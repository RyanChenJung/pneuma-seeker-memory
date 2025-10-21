import glob
import os
from logging import Logger
from typing import Any

from pandas import DataFrame

from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.core.materializer.prompt_factory import MaterializerPromptFactory
from pneuma_seeker.core.materializer.state import MaterializerState
from pneuma_seeker.core.shared.toolkit.main import Toolkit
from pneuma_seeker.core.shared.toolkit.tool.semantic_operator import SyntacticSimMetric
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.utils.config import Config
from pneuma_seeker.utils.logger import formatted_log
from pneuma_seeker.utils.parser import parse_code, parse_json


class Materializer:
    """
    Materializer class that orchestrates the materialization
    process using LLMs and various operations.
    """

    def __init__(
        self,
        llm: AbstractModel,
        embed_model: AbstractModel,
        logger: Logger,
        data_sources: list[str],
        prov_graph: ProvenanceGraph,
        toolkit: Toolkit,
        config: Config,
    ):
        self.llm = llm
        self.embed_model = embed_model
        self.logger = logger
        self.config = config

        self.__log("Initializing Materializer")

        self.prompt_factory = MaterializerPromptFactory(self.config)
        self.state = MaterializerState()

        self.actions: list[str] = []
        self.data_sources = data_sources
        self.prov_graph = prov_graph
        self.toolkit = toolkit

        self.module_dir = os.path.dirname(os.path.abspath(__file__))

    def materialize_T(
        self,
        T: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        S: str,
        user_side_note="",
        external_tables: list[AbstractDocument] = [],
        prefetched_tables: list[AbstractDocument] = [],
    ) -> dict[str, DataFrame]:
        """Materialize target tables T based on the provided script S and external tables."""
        self.__log(f"Materializing {len(T)} target tables")
        self.__cleanup_system()

        if len(prefetched_tables) > 0:
            self.state.retrieved_tables = prefetched_tables

        prev_response = ""
        repetitive_response_count = 0

        curr_iteration = 0
        llm_messages = [
            LLMMessage(
                role=Role.SYSTEM.value,
                content=self.prompt_factory.get_planning_prompt(
                    T=T,
                    column_descriptions=column_descriptions,
                    S=S,
                ),
            )
        ]
        while not self.__check_completion(T):
            self.__log("Planning next materialization step")
            curr_iteration += 1
            llm_messages.append(
                LLMMessage(
                    role=Role.USER.value,
                    content=self.prompt_factory.get_context_prompt(
                        self.state.retrieved_tables,
                        list(self.state.intermediate_tables),
                        self.actions,
                        curr_iteration,
                        user_side_note,
                        external_tables,
                        self.state.web_search_result,
                    ),
                )
            )

            response = "".join(self.llm.chat(llm_messages, LLMOption(json_mode=True)))
            self.__log(f"LLM response: {response}")

            if response == prev_response:
                repetitive_response_count += 1
            else:
                prev_response = response
                repetitive_response_count = 0
            if repetitive_response_count == 5:
                break

            llm_messages.append(
                LLMMessage(
                    role=Role.ASSISTANT.value,
                    content=response,
                )
            )

            try:
                plan: dict[str, Any] = parse_json(response)
            except ValueError as exc:
                self.__log(f"Error parsing JSON: {exc}")
                self.actions.append(
                    "Error parsing the response. Please ensure the response is a valid JSON object."
                )
                continue

            step_type: str = plan.get("step_type", "")
            if len(step_type) == 0:
                error_msg = "The step_type is not defined. Please define it properly."
                self.__log(error_msg)
                self.actions.append(error_msg)
                continue

            self.__handle_step(step_type, plan, external_tables, T)

        self.__log("Materialization completed successfully")
        final_result: dict[str, DataFrame] = {}
        for intermediate_table_doc in self.state.intermediate_tables:
            if intermediate_table_doc.doc_id in T.keys():
                final_result[intermediate_table_doc.doc_id] = (
                    intermediate_table_doc.content
                )
        return final_result

    def __handle_step(
        self,
        step_type: str,
        plan: dict[str, Any],
        external_data: list[AbstractDocument],
        T: dict[str, DataFrame],
    ):
        """Handles a single step in the materialization process."""
        if step_type == "internal_reasoning":
            message: str = plan["message"]
            self.actions.append(f"Reasoned internally: {message}")
        elif step_type == "operation":
            op_name, op_args, assign_to = (
                plan.get("name", ""),
                plan.get("args", {}),
                plan.get("assign_to", ""),
            )

            if len(op_name) == 0:
                error_msg = "The op_name is not defined. Please define it properly."
                self.__log(error_msg)
                self.actions.append(error_msg)
                return

            self.__handle_operation(T, external_data, op_name, op_args, assign_to)
        else:
            self.actions.append(f"The step {step_type} is not a valid action.")

    def __handle_operation(
        self,
        T: dict[str, DataFrame],
        external_data: list[AbstractDocument],
        op_name: str,
        op_args: dict[str, Any],
        assign_to: str,
    ):
        all_tables = self.__gather_all_tables(external_data)
        self.__log(f"Executing {op_name}...")
        match op_name:
            case "pneuma_retriever":
                prompt = op_args.get("prompt", "")
                self.state.retrieved_tables = self.toolkit.retrieve_documents(
                    prompt, RetrieverType.PNEUMA, 10
                )
                self.actions.append(
                    f'Successfully retrieved tables using this prompt: ```{prompt}```. Notice that the "Retrieved internal tables" have been filled.'
                )

                for doc in self.state.retrieved_tables:
                    if doc.path is not None:
                        new_node = ProvenanceNode(
                            source_retriever=RetrieverType.PNEUMA,
                            python_code=self.toolkit.generate_pandas_read_code(doc),
                        )
                        self.prov_graph.add_node(new_node, True)
                        doc.last_node_id = new_node.id
            case "web_search":
                if not self.config.ENABLE_WEB_SEARCH:
                    self.actions.append(
                        "Web search is not enabled in the configuration."
                    )
                    return
                prompt = op_args.get("prompt", "")
                web_search_results = self.toolkit.retrieve_documents(
                    prompt, RetrieverType.WEB_SEARCH
                )
                if len(web_search_results) == 0:
                    self.actions.append(
                        "No relevant information was found from web search."
                    )
                    return
                self.state.web_search_result = web_search_results[0]
                self.actions.append(
                    f'Successfully retrieved information from Web Search using this prompt: ```{prompt}```. Notice that the "Retrieved internal tables" have been filled.'
                )

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.WEB_SEARCH,
                    python_code=f'result = "{self.state.web_search_result.content}"',
                )
                self.prov_graph.add_node(new_node, True)
                self.state.web_search_result.last_node_id = new_node.id
            case "table_enumerator":
                pattern = op_args.get("pattern", "")
                extra_tables: list[AbstractDocument] = self.toolkit.retrieve_documents(
                    pattern, RetrieverType.ENUMERATOR
                )

                if len(extra_tables) > 0:
                    self.actions.append(
                        f'Successfully retrieved all tables that match the pattern {pattern}. You can use them to materialize T, even if you have not called pneuma_retriever before, as these tables have been included to "Previously retrieved documents".'
                    )

                    new_node = ProvenanceNode(
                        source_retriever=RetrieverType.ENUMERATOR,
                        python_code=self.toolkit.generate_pandas_read_multi_doc_code(
                            extra_tables
                        ),
                    )
                    self.prov_graph.add_node(new_node, True)

                    for extra_table in extra_tables:
                        extra_table.last_node_id = new_node.id

                    existing_tables = self.state.retrieved_tables
                    self.state.retrieved_tables = list(
                        set(existing_tables).union(set(extra_tables))
                    )
                else:
                    self.actions.append("There are no tables that match the pattern.")
            case "table_select":
                for target_table_id, retrieved_table_info in op_args.items():
                    if isinstance(retrieved_table_info, list):
                        if len(retrieved_table_info) == 0:
                            msg = f"Skipping {target_table_id!r}: empty list provided as value."
                            self.__log(msg)
                            self.actions.append(msg)
                            continue
                        retrieved_table_info = retrieved_table_info[0]

                    if not isinstance(retrieved_table_info, dict):
                        msg = f"Invalid argument for target {target_table_id!r}: expected a dict."
                        self.__log(msg)
                        self.actions.append(msg)
                        continue

                    table_id_to_select = str(retrieved_table_info.get("id", "")).strip()
                    if table_id_to_select.startswith("Table "):
                        table_id_to_select = table_id_to_select[6:].strip()
                    relevant_columns = retrieved_table_info.get("columns", [])
                    target_table_id = target_table_id.strip()

                    all_table_doc_ids = [i.doc_id for i in all_tables]
                    if table_id_to_select not in all_table_doc_ids:
                        error_msg = (
                            f"Invalid table ID to select. Ensure the table exists."
                        )
                        self.__log(error_msg)
                        self.actions.append(error_msg)
                        return

                    if target_table_id in T:
                        matches = [
                            i for i in all_tables if i.doc_id == table_id_to_select
                        ]
                        if not matches:
                            error_msg = f"Table {table_id_to_select!r} not found in the available tables."
                            self.__log(error_msg)
                            self.actions.append(error_msg)
                            return

                        table_to_select_doc = matches[0]
                        self.__log(
                            f"=> target_table_id: {target_table_id}; table_id_to_select: {table_id_to_select}"
                        )

                        try:
                            table_to_select: DataFrame = table_to_select_doc.content[
                                relevant_columns
                            ]
                        except Exception as e:
                            error_msg = f"Failed selecting columns {relevant_columns!r} from table {table_id_to_select!r}: {e}"
                            self.__log(error_msg)
                            self.actions.append(error_msg)
                            return

                        new_node_id: str | None = None
                        if table_to_select_doc.path is not None:
                            child_node = ProvenanceNode(
                                source_retriever=RetrieverType.MATERIALIZER,
                                python_code=self.toolkit.generate_table_select_code(
                                    target_table_id,
                                    table_to_select_doc.doc_id,
                                    relevant_columns,
                                ),
                            )
                            parent_node = self.prov_graph.get_node_by_id(
                                table_to_select_doc.last_node_id or ""
                            )

                            new_node_id = child_node.id
                            self.prov_graph.add_node(child_node, True)
                            if parent_node is not None:
                                self.prov_graph.connect(parent_node, child_node)

                        self.state.add_intermediate_table(
                            Table(
                                doc_id=target_table_id,
                                retriever_type=RetrieverType.MATERIALIZER,
                                content=table_to_select,
                                metadata={},
                                last_node_id=new_node_id,
                            )
                        )
                        self.__save_new_or_updated_intermediate_table(target_table_id)
                        self.actions.append(
                            "Successfully selecting retrieved tables in the mapping as target tables. Notice the state's intermediate tables have changed, but please CHECK if the schemas in the selected tables match, either fully or partially, with the ones in target tables."
                        )
                    else:
                        self.actions.append(
                            f"Error: The ID {target_table_id} does not exist in T. Please fix it."
                        )
            case "semantic_column_generator":
                table_id: str | None = op_args.get("table_id")
                new_column_name: str | None = op_args.get("new_column_name")
                table_relevant_columns: list[str] | None = op_args.get(
                    "relevant_columns"
                )
                instruction: str | None = op_args.get("instruction")

                if table_id is None or table_id not in [i.doc_id for i in all_tables]:
                    self.actions.append(
                        "table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                    )
                    return
                if new_column_name is None:
                    self.actions.append("new_column_name is not provided.")
                    return
                if table_relevant_columns is None:
                    self.actions.append("relevant_columns is not provided.")
                    return

                conditioned_table_doc = [i for i in all_tables if i.doc_id == table_id][
                    0
                ]
                conditioned_table: DataFrame = conditioned_table_doc.content

                if not set(table_relevant_columns) <= set(
                    list(conditioned_table.columns)
                ):
                    self.actions.append(
                        f"relevant_columns must be a subset of the columns of table {table_id}."
                    )
                    return
                if instruction is None:
                    self.actions.append("instruction is not provided.")
                    return

                new_column_values = self.toolkit.generate_semantic_column(
                    conditioned_table[table_relevant_columns],
                    new_column_name,
                    instruction,
                )
                conditioned_table[new_column_name] = new_column_values
                self.actions.append(
                    f"Successfully added a new column named {new_column_name} to table with ID {table_id}."
                )

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.MATERIALIZER,
                    python_code=self.toolkit.generate_semantic_col_generator_code(
                        table_relevant_columns,
                        conditioned_table_doc,
                        new_column_name,
                        os.path.join(
                            self.__get_intermediate_table_dir_path(),
                            f"{conditioned_table_doc.doc_id}.csv",
                        ),
                    ),
                )
                self.prov_graph.add_node(new_node, True)
                parent_node = self.prov_graph.get_node_by_id(
                    conditioned_table_doc.last_node_id or ""
                )
                if parent_node is not None:
                    self.prov_graph.connect(parent_node, new_node)

                conditioned_table_doc.last_node_id = new_node.id
                self.__save_new_or_updated_intermediate_table(
                    conditioned_table_doc.doc_id
                )
            case "semantic_join":
                left_table_id: str | None = op_args.get("left_table_id")
                right_table_id: str | None = op_args.get("right_table_id")
                relevant_left_cols: list[str] | None = op_args.get("relevant_left_cols")
                relevant_right_cols: list[str] | None = op_args.get(
                    "relevant_right_cols"
                )
                joined_table_id: str | None = op_args.get("joined_table_id")

                all_table_ids = [i.doc_id for i in all_tables]
                if left_table_id is None or left_table_id not in all_table_ids:
                    self.actions.append(
                        "left_table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                    )
                    return
                if right_table_id is None or right_table_id not in all_table_ids:
                    self.actions.append(
                        "right_table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                    )
                    return

                left_table: DataFrame | None = None
                left_table_doc: AbstractDocument | None = None
                right_table: DataFrame | None = None
                right_table_doc: AbstractDocument | None = None

                for doc in all_tables:
                    if doc.doc_id == left_table_id:
                        left_table = doc.content
                        left_table_doc = doc
                    if doc.doc_id == right_table_id:
                        right_table = doc.content
                        right_table_doc = doc

                if not isinstance(left_table, DataFrame):
                    self.actions.append(
                        f"left_table with ID {left_table_id} is not a DataFrame."
                    )
                    return
                if not isinstance(right_table, DataFrame):
                    self.actions.append(
                        f"right_table with ID {right_table_id} is not a DataFrame."
                    )
                    return

                if not isinstance(left_table_doc, AbstractDocument):
                    self.actions.append(
                        f"ID {left_table_id} does not correspond to a document."
                    )
                    return
                if not isinstance(right_table_doc, AbstractDocument):
                    self.actions.append(
                        f"ID {right_table_id} does not correspond to a document."
                    )
                    return

                if relevant_left_cols is None:
                    self.actions.append("relevant_left_cols is not provided.")
                    return
                if relevant_right_cols is None:
                    self.actions.append("relevant_right_cols is not provided.")
                    return
                if not set(relevant_left_cols) <= set(list(left_table.columns)):
                    self.actions.append(
                        "relevant_left_cols is not a subseet of left_table's columns."
                    )
                    return
                if not set(relevant_right_cols) <= set(list(right_table.columns)):
                    self.actions.append(
                        "relevant_right_cols is not a subseet of right_table's columns."
                    )
                    return
                if not joined_table_id:
                    self.actions.append("joined_table_id is not provided.")
                    return

                joined_table = self.toolkit.semantic_join(
                    left_table,
                    right_table,
                    relevant_left_cols,
                    relevant_right_cols,
                    syntactic_sim_metric=SyntacticSimMetric.JACCARD_QGRAM,
                    top_k=self.config.SEMANTIC_JOIN_TOP_K,
                )

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.MATERIALIZER,
                    python_code=self.toolkit.generate_semantic_join_generator_code(
                        left_table_doc,
                        right_table_doc,
                        relevant_left_cols,
                        relevant_right_cols,
                        self.config.SEMANTIC_JOIN_TOP_K,
                        os.path.join(
                            self.__get_intermediate_table_dir_path(),
                            f"{joined_table_id}.csv",
                        ),
                    ),
                )
                parent_node_1 = self.prov_graph.get_node_by_id(
                    left_table_doc.last_node_id or ""
                )
                parent_node_2 = self.prov_graph.get_node_by_id(
                    right_table_doc.last_node_id or ""
                )

                self.prov_graph.add_node(new_node, True)
                if parent_node_1 is not None:
                    self.prov_graph.connect(parent_node_1, new_node)
                if parent_node_2 is not None:
                    self.prov_graph.connect(parent_node_2, new_node)

                self.state.add_intermediate_table(
                    Table(
                        doc_id=joined_table_id,
                        retriever_type=RetrieverType.MATERIALIZER,
                        content=joined_table,
                        metadata={},
                        last_node_id=new_node.id,
                    )
                )
                self.__save_new_or_updated_intermediate_table(joined_table_id)

                self.actions.append(
                    "Successfully joined the left and right tables semantically. Notice the state's intermediate tables have changed."
                )
            case "python_executor":
                id_dfs: dict[str, DataFrame] = {}
                id_docs: dict[str, AbstractDocument] = {}
                for table_doc in all_tables:
                    id_dfs[table_doc.doc_id] = table_doc.content
                    id_docs[table_doc.doc_id] = table_doc

                python_code: str = parse_code(op_args.get("code", ""))
                python_executor_output = self.toolkit.execute_code(id_dfs, python_code)

                exec_res = python_executor_output["exec_res"]
                used_table_ids = python_executor_output["used_table_ids"]

                used_table_retrievers: list[RetrieverType] = []
                parent_nodes: list[ProvenanceNode] = []
                for used_table_id in used_table_ids:
                    used_table_retrievers.append(id_docs[used_table_id].retriever_type)

                    used_table_doc = id_docs[used_table_id]
                    parent_node = self.prov_graph.get_node_by_id(
                        used_table_doc.last_node_id or ""
                    )
                    if parent_node is not None:
                        parent_nodes.append(parent_node)

                if isinstance(exec_res, DataFrame):
                    new_node = ProvenanceNode(
                        source_retriever=RetrieverType.MATERIALIZER,
                        python_code=self.toolkit.append_comment_to_existing_code(
                            python_code,
                            f"Result path: {os.path.join(
                                self.__get_intermediate_table_dir_path(),
                                f"{assign_to}.csv",
                            )}",
                        ),
                    )
                    self.prov_graph.add_node(new_node, True)
                    for parent_node in parent_nodes:
                        self.prov_graph.connect(parent_node, new_node)

                    self.state.add_intermediate_table(
                        Table(
                            doc_id=assign_to,
                            retriever_type=RetrieverType.MATERIALIZER,
                            content=exec_res,
                            metadata={},
                            last_node_id=new_node.id,
                        )
                    )
                    self.__save_new_or_updated_intermediate_table(assign_to)

                    self.actions.append(
                        f"Successfully executed the Python code, resulting in a table named {assign_to}"
                    )
                elif isinstance(exec_res, Exception):
                    self.__log(
                        f"Exception during execution of the Python code: {exec_res}"
                    )
                    diagnose_messages = [
                        LLMMessage(
                            role=Role.SYSTEM.value,
                            content=self.prompt_factory.get_fix_python_prompt(
                                python_code, id_dfs, exec_res
                            ),
                        )
                    ]
                    feedback = self.llm.chat(diagnose_messages)
                    feedback = "".join(feedback)
                    self.actions.append(feedback)
                else:
                    if exec_res is None:
                        self.actions.append(
                            "The `result` variable is empty, which means the Python code did not assign the outcome (e.g., table) to the variable `result`."
                        )
                    else:
                        self.actions.append(
                            f"Successfully executed the Python code, resulting in this: {exec_res}"
                        )
                        new_node = ProvenanceNode(
                            source_retriever=RetrieverType.MATERIALIZER,
                            python_code=self.toolkit.append_comment_to_existing_code(
                                python_code,
                                "The execution did not result in a DataFrame, but something else.",
                            ),
                        )
                        self.prov_graph.add_node(new_node, True)
                        for parent_node in parent_nodes:
                            self.prov_graph.connect(parent_node, new_node)
            case "sql_executor":
                try:
                    sql_query: str = op_args["sql_query"]
                    self.logger.info(f"Executing this SQL query: {sql_query}")

                    id_dfs: dict[str, DataFrame] = {}
                    id_docs: dict[str, AbstractDocument] = {}
                    for doc in all_tables:
                        id_dfs[doc.doc_id] = doc.content
                        id_docs[doc.doc_id] = doc
                    sql_executor_output = self.toolkit.execute_sql_df(sql_query, id_dfs)

                    exec_res: DataFrame = sql_executor_output["exec_res"]
                    used_table_ids = sql_executor_output["used_table_ids"]

                    source_retrievers: list[RetrieverType] = []
                    parent_nodes: list[ProvenanceNode] = []
                    for used_table_id in used_table_ids:
                        source_retrievers.append(id_docs[used_table_id].retriever_type)
                        parent_node = self.prov_graph.get_node_by_id(used_table_id)
                        if parent_node is not None:
                            parent_nodes.append(parent_node)

                    new_node = ProvenanceNode(
                        source_retriever=RetrieverType.MATERIALIZER,
                        python_code=self.toolkit.generate_sql_executor_code(
                            sql_query,
                            id_dfs,
                            os.path.join(
                                self.__get_intermediate_table_dir_path(),
                                f"{assign_to}.csv",
                            ),
                        ),
                    )
                    self.prov_graph.add_node(new_node, True)
                    for parent_node in parent_nodes:
                        self.prov_graph.connect(parent_node, new_node)

                    self.state.add_intermediate_table(
                        Table(
                            doc_id=assign_to,
                            retriever_type=RetrieverType.MATERIALIZER,
                            content=exec_res,
                            metadata={},
                            last_node_id=new_node.id,
                        )
                    )
                    self.__save_new_or_updated_intermediate_table(assign_to)

                    self.actions.append(
                        f"Successfully executed the SQL query, resulting in a table named {assign_to}"
                    )

                except Exception as e:
                    self.actions.append(
                        f"Error when executing the SQL query: {e}. Please fix it (you may want to quote identifiers with, for instance, `-` symbol)."
                    )
            case _:
                self.actions.append(
                    f"Trying to perform/execute {op_name}, but it is not a valid operation."
                )

    def __check_completion(self, T: dict[str, DataFrame]) -> bool:
        """Check if all target tables (T) have been materialized correctly."""
        self.__log("Checking completion...")
        all_T_ids = set(T.keys())
        id_dfs: dict[str, DataFrame] = {}

        materialized_table_ids: set[str] = set()
        for doc in self.state.intermediate_tables:
            if isinstance(doc.content, DataFrame):
                id_dfs[doc.doc_id] = doc.content
                materialized_table_ids.add(doc.doc_id)
            else:
                self.__log(
                    f"Warning: doc {doc.doc_id} has invalid content type {type(doc.content)}"
                )

        self.__log(f"=> all_T_ids: {all_T_ids}")
        self.__log(f"=> materialized_table_ids: {materialized_table_ids}")
        ids_complete = all_T_ids <= materialized_table_ids
        is_complete = ids_complete

        if not ids_complete:
            self.actions.append(
                f"==> You have not materialized these tables: {all_T_ids - materialized_table_ids}"
            )

        column_issues: list[str] = ["Fix the following column issues:"]
        if ids_complete:
            for target_table_id in all_T_ids:
                df = id_dfs.get(target_table_id)
                if df is None or not isinstance(df, DataFrame):
                    issue_msg = f"- For table `{target_table_id}`: no valid DataFrame was materialized."
                    self.__log(issue_msg)
                    column_issues.append(issue_msg)
                    is_complete = False
                    continue

                self.__log(f"=> Checking the target schema {target_table_id}.")
                target_cols = set(T[target_table_id].columns)
                materialized_cols = set(df.columns)

                self.__log(f"==> target_cols {target_cols}")
                self.__log(f"==> materialized_cols {materialized_cols}")

                missing_cols = target_cols - materialized_cols
                extra_cols = materialized_cols - target_cols

                if missing_cols or extra_cols:
                    is_complete = False
                    issue_msg = f"- For table `{target_table_id}`: "
                    if missing_cols:
                        issue_msg += f"missing columns {sorted(missing_cols)}. "
                    if extra_cols:
                        issue_msg += f"unexpected columns {sorted(extra_cols)}. "
                    column_issues.append(issue_msg.strip())

        if ids_complete and not is_complete:
            self.actions.append("\n".join(column_issues))

        self.__log(f"==> is_complete: {is_complete}")
        self.__log(
            f"Completion check: {is_complete} ({len(materialized_table_ids)}/{len(all_T_ids)} tables materialized)"
        )
        return is_complete

    def __gather_all_tables(self, external_data: list[AbstractDocument]):
        """Gather all tables from retrieved documents, external data, and intermediate tables."""
        external_data_tables_only: list[AbstractDocument] = [
            i for i in external_data if isinstance(i, Table)
        ]
        return (
            self.state.retrieved_tables
            + external_data_tables_only
            + list(self.state.intermediate_tables)
        )

    def __cleanup_system(self):
        """Reset the state and clear intermediate files."""
        self.__log("Cleaning up Materializer...")
        self.state.reset()
        self.prov_graph.reset_for_materialization()
        self.__clear_csv_files()
        self.actions = []

    def __clear_csv_files(self):
        """Delete all .csv files in the module directory."""
        pattern = os.path.join(self.__get_intermediate_table_dir_path(), "*.csv")
        for csv_file in glob.glob(pattern):
            try:
                os.remove(csv_file)
            except Exception:
                continue

    def __log(self, text: str):
        formatted_log(self.logger, "MATERIALIZER", text)

    def __save_new_or_updated_intermediate_table(self, table_id: str):
        """Save a new or updated intermediate table to a CSV file."""
        csv_path = os.path.join(
            self.__get_intermediate_table_dir_path(), f"{table_id}.csv"
        )
        intermediate_table: DataFrame | None = None
        for table_doc in self.state.intermediate_tables:
            if table_doc.doc_id == table_id:
                intermediate_table = table_doc.content
                break

        if isinstance(intermediate_table, DataFrame):
            intermediate_table.to_csv(csv_path, index=False)

    def __get_intermediate_table_dir_path(self):
        """Get the directory path for storing intermediate table CSV files."""
        return os.path.join(self.module_dir, "intermediate_data")
