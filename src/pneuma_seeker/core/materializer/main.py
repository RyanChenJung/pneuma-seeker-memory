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
from pneuma_seeker.core.ir_system.main import IRSystem
from pneuma_seeker.core.materializer.operation.operation_description import (
    get_operation_description,
)
from pneuma_seeker.core.materializer.operation.python_executor import PythonExecutor
from pneuma_seeker.core.materializer.operation.semantic_column_generator import (
    SemanticColumnGenerator,
)
from pneuma_seeker.core.materializer.operation.semantic_joiner import (
    SemanticJoiner,
    SyntacticSimMetric,
)
from pneuma_seeker.core.materializer.operation.sql_executor import SQLExecutor
from pneuma_seeker.core.materializer.prompt_factory import MaterializerPromptFactory
from pneuma_seeker.core.materializer.state import MaterializerState
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
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
    ):
        self.__log("Initializing Materializer")

        self.llm = llm
        self.embed_model = embed_model
        self.logger = logger

        self.prompt_factory = MaterializerPromptFactory()
        self.state = MaterializerState()

        self.actions: list[str] = []
        self.data_sources = data_sources
        self.prov_graph = prov_graph

        self.ir_system = IRSystem(self.llm, self.embed_model, self.logger)
        self.python_executor = PythonExecutor(self.logger, self.prov_graph)
        self.sql_executor = SQLExecutor(self.llm, self.logger)
        self.semantic_joiner = SemanticJoiner(self.llm, self.embed_model)
        self.semantic_col_generator = SemanticColumnGenerator(self.llm, 20)

        self.is_sql_alignment_checked = False
        self.module_dir = os.path.dirname(os.path.abspath(__file__))

    def materialize_T(
        self,
        T: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        Q: list[str],
        user_side_note="",
        external_data: list[AbstractDocument] = [],
        prefetched_ir_docs: dict[RetrieverType, list[AbstractDocument]] = {},
    ) -> dict[str, DataFrame]:
        """Materialize target schemas T based on the provided queries Q and external data."""
        self.__log(f"Materializing {len(T)} target tables")
        self.__cleanup_system()

        if len(prefetched_ir_docs) > 0:
            for retriever_type in prefetched_ir_docs:
                prefetched_docs = prefetched_ir_docs[retriever_type]
                if len(prefetched_docs) > 0:
                    self.state.current_retrieved_documents[retriever_type] = (
                        prefetched_docs
                    )

        # Future-TODO: Use more fundamental safeguard; currently, we
        # prevent repetitive iteration that can happen, usually if
        # the model is confident it has produced all tables specified
        # in T, even though it is not (fundamentally) enough.
        prev_response = ""
        repetitive_response_count = 0

        curr_iteration = 0
        llm_messages = [
            LLMMessage(
                role=Role.SYSTEM.value,
                content=self.prompt_factory.get_planning_prompt(
                    T=T,
                    column_descriptions=column_descriptions,
                    Q=Q,
                    operation_description=get_operation_description(),
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
                        self.state.current_retrieved_documents,
                        list(self.state.intermediate_tables),
                        self.actions,
                        curr_iteration,
                        user_side_note,
                        external_data,
                    ),
                )
            )

            response = "".join(self.llm.chat(llm_messages, LLMOption(json_mode=True)))
            if response == prev_response:
                repetitive_response_count += 1
            else:
                prev_response = response
                repetitive_response_count = 0
            if repetitive_response_count == 5:
                break

            self.__log(f"LLM response: {response}")
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
                    "Error parsing the response from the model. Please ensure the response is in valid JSON format."
                )
                continue

            step_type: str = plan.get("step_type", "")
            self.__handle_step(
                step_type, plan, self.__gather_all_tables(external_data), T
            )

        self.__log("Materialization completed successfully")
        final_result: dict[str, DataFrame] = {}
        for intermediate_table_doc in self.state.intermediate_tables:
            if intermediate_table_doc.doc_id in T.keys():
                final_result[intermediate_table_doc.doc_id] = (
                    intermediate_table_doc.content
                )
        return final_result

    def __gather_all_tables(self, external_data: list[AbstractDocument]):
        """Gather all tables from retrieved documents, external data, and intermediate tables."""
        pneuma_retrieval_results: list[AbstractDocument] = (
            self.state.current_retrieved_documents.get(RetrieverType.PNEUMA, [])
        )
        external_data_tables_only: list[AbstractDocument] = [
            i for i in external_data if isinstance(i, Table)
        ]
        return (
            pneuma_retrieval_results
            + external_data_tables_only
            + list(self.state.intermediate_tables)
        )

    def __handle_step(
        self,
        step_type: str,
        plan: dict[str, Any],
        all_tables: list[AbstractDocument],
        T: dict[str, DataFrame],
    ):
        """Handles a single step in the materialization process."""
        if step_type == "internal_reasoning":
            message: str = plan["message"]
            self.actions.append(f"Reasoned internally: {message}")
        elif step_type == "operation":
            op_name: str = plan.get("name", "")
            op_args: dict[str, Any] = plan.get("args", {})
            assign_to: str = plan.get("assign_to", "")

            if op_name == "Document Retriever":
                self.__log("Executing Document Retriever")
                prompt: str = op_args.get("prompt", "")
                self.state.current_retrieved_documents = (
                    self.ir_system.retrieve_multisource_documents(
                        prompt,
                        self.data_sources,
                        10,
                    )
                )
                self.actions.append(
                    f'Successfully retrieved documents using this prompt: ```{prompt}```. Notice that the "Previously retrieved documents" have been filled.'
                )

                for doc in self.state.current_retrieved_documents.get(
                    RetrieverType.PNEUMA, []
                ):
                    if doc.path is not None:
                        new_node = ProvenanceNode(
                            output_data_id=doc.doc_id,
                            output_data_ref={"doc_path": doc.path},
                            source_retriever=RetrieverType.PNEUMA,
                            op_description="Data retrieved from Pneuma",
                        )
                        self.prov_graph.add_node(new_node, True)
                        doc.last_node_id = new_node.id

                for doc in self.state.current_retrieved_documents[
                    RetrieverType.DOCUMENT_DB
                ]:
                    new_node = ProvenanceNode(
                        output_data_id=doc.doc_id,
                        output_data_ref={"doc_content": doc.content},
                        source_retriever=RetrieverType.DOCUMENT_DB,
                        op_description="Data retrieved from Document DB",
                    )
                    self.prov_graph.add_node(new_node, True)
                    doc.last_node_id = new_node.id
            elif op_name == "Table Enumerator":
                self.__log("Executing Table Enumerator")
                pattern: str = op_args.get("pattern", "")
                extra_tables: list[AbstractDocument] = (
                    self.ir_system.retrieve_documents(
                        RetrieverType.ENUMERATOR,
                        pattern,
                        self.data_sources,
                    )
                )

                for extra_table in extra_tables:
                    if extra_table.path is not None:
                        new_node = ProvenanceNode(
                            output_data_id=extra_table.doc_id,
                            output_data_ref={"extra_table_path": extra_table.path},
                            source_retriever=RetrieverType.ENUMERATOR,
                            op_description=f"Enumerate tables using this pattern: {pattern}",
                        )
                        self.prov_graph.add_node(new_node, True)
                        extra_table.last_node_id = new_node.id

                if len(self.state.current_retrieved_documents.keys()) == 0:
                    if len(extra_tables) > 0:
                        self.state.current_retrieved_documents = {
                            RetrieverType.PNEUMA: extra_tables
                        }
                else:
                    self.state.current_retrieved_documents[RetrieverType.PNEUMA] = list(
                        set(
                            self.state.current_retrieved_documents.get(
                                RetrieverType.PNEUMA, []
                            )
                        ).union(set(extra_tables))
                    )
                if len(extra_tables) > 0:
                    self.actions.append(
                        f'Successfully retrieved all tables that match the pattern {pattern}. You can use them to materialize target schemas, even if you have not called Document Retriever before, as these tables have been included to "Previously retrieved documents".'
                    )
                else:
                    self.actions.append("There are no tables that match the pattern.")
            elif op_name == "Table Select":
                self.__log("Executing Table Select:")
                for target_schema_id, retrieved_table_info in op_args.items():
                    if isinstance(retrieved_table_info, list):
                        retrieved_table_info = retrieved_table_info[0]
                    table_id_to_select: str = retrieved_table_info.get("id", "")
                    relevant_columns: list[str] = retrieved_table_info.get(
                        "columns", []
                    )

                    if table_id_to_select.startswith("Table "):
                        table_id_to_select = table_id_to_select[6:]
                    table_id_to_select = table_id_to_select.strip()
                    target_schema_id = target_schema_id.strip()

                    self.__log(
                        f"=> target_schema_id: {target_schema_id}; table_id_to_select: {table_id_to_select}"
                    )

                    all_table_doc_ids = [i.doc_id for i in all_tables]
                    if (
                        target_schema_id in T
                        and table_id_to_select in all_table_doc_ids
                    ):
                        table_to_select_doc = [
                            i for i in all_tables if i.doc_id == table_id_to_select
                        ][0]
                        table_to_select: DataFrame = table_to_select_doc.content[
                            relevant_columns
                        ]

                        new_node_id = None
                        if (
                            table_to_select_doc.path is not None
                            and table_to_select_doc.last_node_id is not None
                        ):
                            child_node = ProvenanceNode(
                                output_data_id=target_schema_id,
                                output_data_ref={
                                    "selected_table_path": table_to_select_doc.path,
                                    "relevant_columns": str(relevant_columns),
                                },
                                source_retriever=RetrieverType.MATERIALIZER,
                                op_description="Directly select a relevant retrieved table",
                            )
                            parent_node = self.prov_graph.get_node_by_id(
                                table_to_select_doc.last_node_id
                            )

                            new_node_id = child_node.id
                            self.prov_graph.add_node(child_node, True)
                            if parent_node is not None:
                                self.prov_graph.connect(parent_node, child_node)

                        self.state.add_intermediate_table(
                            Table(
                                doc_id=target_schema_id,
                                retriever_type=RetrieverType.MATERIALIZER,
                                content=table_to_select,
                                metadata={},
                                last_node_id=new_node_id,
                            )
                        )
                        self.__save_new_or_updated_intermediate_table(target_schema_id)
                        self.actions.append(
                            "Successfully selecting retrieved tables in the mapping as target schema tables. Notice the state's intermediate tables have changed, but please CHECK if the schemas in the selected tables match, either fully or partially, with the ones in target schemas."
                        )

                    elif target_schema_id not in T:
                        self.actions.append(
                            f"Error: The ID {target_schema_id} does not exist in the target schemas. Please fix it."
                        )
                    else:
                        self.actions.append(
                            f"Error: The ID {table_id_to_select} does not exist in either the retrieved tables OR the intermediate tables so far. Please fix it."
                        )
            elif op_name == "Semantic Column Generator":
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

                new_column_values = (
                    self.semantic_col_generator.generate_semantic_column(
                        conditioned_table[table_relevant_columns],
                        new_column_name,
                        instruction,
                    )
                )
                conditioned_table[new_column_name] = new_column_values
                self.actions.append(
                    f"Successfully added a new column named {new_column_name} to table with ID {table_id}."
                )

                new_node = ProvenanceNode(
                    output_data_id=conditioned_table_doc.doc_id,
                    output_data_ref={
                        "semantically_appended_table_path": os.path.join(
                            self.__get_intermediate_table_dir_path(),
                            f"{conditioned_table_doc.doc_id}.csv",
                        )
                    },
                    source_retriever=RetrieverType.MATERIALIZER,
                    op_description="Generates column semantically",
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
            elif op_name == "Semantic Join":
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

                joined_table = self.semantic_joiner.semantic_join(
                    left_table,
                    right_table,
                    relevant_left_cols,
                    relevant_right_cols,
                    syntactic_sim_metric=SyntacticSimMetric.JACCARD_QGRAM,
                    top_k=2,
                )

                new_node = ProvenanceNode(
                    output_data_id=joined_table_id,
                    output_data_ref={
                        "joined_table_path": os.path.join(
                            self.__get_intermediate_table_dir_path(),
                            f"{joined_table_id}.csv",
                        )
                    },
                    source_retriever=RetrieverType.MATERIALIZER,
                    op_description="Joins tables semantically",
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
            elif op_name == "Python Executor":
                id_dfs: dict[str, DataFrame] = {}
                id_docs: dict[str, AbstractDocument] = {}
                for table_doc in all_tables:
                    id_dfs[table_doc.doc_id] = table_doc.content
                    id_docs[table_doc.doc_id] = table_doc

                python_code: str = parse_code(op_args.get("code", ""))
                python_executor_output = self.python_executor.execute_code(
                    id_dfs, python_code
                )

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
                        output_data_id=assign_to,
                        output_data_ref={
                            "exec_res_path": os.path.join(
                                self.__get_intermediate_table_dir_path(),
                                f"{assign_to}.csv",
                            )
                        },
                        source_retriever=RetrieverType.MATERIALIZER,
                        op_description=f"Executes this Python code: {python_code}",
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
                            output_data_id="",
                            output_data_ref={"exec_res": exec_res},
                            source_retriever=RetrieverType.MATERIALIZER,
                            op_description=f"Executes this Python code: {python_code}",
                        )
                        self.prov_graph.add_node(new_node, True)
                        for parent_node in parent_nodes:
                            self.prov_graph.connect(parent_node, new_node)
            elif op_name == "SQL Executor":
                try:
                    sql_query: str = op_args["sql_query"]
                    id_dfs: dict[str, DataFrame] = {}
                    id_docs: dict[str, AbstractDocument] = {}
                    for doc in all_tables:
                        id_dfs[doc.doc_id] = doc.content
                        id_docs[doc.doc_id] = doc
                    sql_executor_output = self.sql_executor.execute_sql(
                        sql_query, id_dfs
                    )

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
                        output_data_id=assign_to,
                        output_data_ref={
                            "exec_res_path": os.path.join(
                                self.__get_intermediate_table_dir_path(),
                                f"{assign_to}.csv",
                            )
                        },
                        source_retriever=RetrieverType.MATERIALIZER,
                        op_description=f"Executes this SQL query: {sql_query}",
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
            else:
                self.actions.append(
                    f"Trying to perform/execute {op_name}, but it is not a valid operation."
                )
        else:
            self.actions.append(f"The step {step_type} is not a valid action.")

    def __check_completion(self, T: dict[str, DataFrame]) -> bool:
        """Check if all target schemas in T have been materialized correctly."""
        self.__log("Check completion")
        all_schema_ids = set(T.keys())
        id_dfs: dict[str, DataFrame] = {}
        materialized_schema_ids: set[str] = set()
        for doc in self.state.intermediate_tables:
            id_dfs[doc.doc_id] = doc.content
            materialized_schema_ids.add(doc.doc_id)

        self.__log(f"=> all_schema_ids: {all_schema_ids}")
        self.__log(f"=> materialized_schema_ids: {materialized_schema_ids}")
        is_complete = all_schema_ids <= materialized_schema_ids

        if not is_complete:
            self.actions.append(
                f"==> You have not materialized these tables: {all_schema_ids - materialized_schema_ids}"
            )

        already_complete = is_complete
        column_issues: list[str] = []

        if is_complete:
            for target_schema_id in all_schema_ids:
                if target_schema_id in materialized_schema_ids:
                    self.__log(f"=> Checking the target schema {target_schema_id}.")

                    target_cols = set(T[target_schema_id].columns)
                    materialized_cols = set(id_dfs[target_schema_id].columns)

                    self.__log(f"==> target_cols {target_cols}")
                    self.__log(f"==> materialized_cols {materialized_cols}")

                    missing_cols = target_cols - materialized_cols
                    extra_cols = materialized_cols - target_cols

                    if missing_cols or extra_cols:
                        is_complete = False
                        issue_msg = f"For table `{target_schema_id}`: "

                        if missing_cols:
                            issue_msg += f"missing columns {sorted(missing_cols)}. "
                        if extra_cols:
                            issue_msg += f"unexpected columns {sorted(extra_cols)}. "

                        column_issues.append(issue_msg.strip())

        if already_complete and not is_complete:
            for issue in column_issues:
                self.actions.append(issue)
            self.actions.append(
                "Fix the above column issues. If some columns have different names (e.g., `Doc ID` vs `doc_id`), rename them using Python."
            )

        self.__log(f"==> is_complete: {is_complete}")
        self.__log(
            f"Completion check: {is_complete} ({len(materialized_schema_ids)}/{len(all_schema_ids)} schemas materialized)"
        )
        return is_complete

    def __cleanup_system(self):
        """Reset the state and clear intermediate files."""
        self.__log("Cleaning up Materializer...")
        self.state.reset()
        self.prov_graph.reset_for_materialization()
        self.__clear_csv_files()
        self.is_sql_alignment_checked = False
        self.actions = []

    def __clear_csv_files(self):
        """Delete all .csv files in the module directory."""
        pattern = os.path.join(self.__get_intermediate_table_dir_path(), "*.csv")
        for csv_file in glob.glob(pattern):
            try:
                os.remove(csv_file)
            except Exception:
                continue

    def __log(self, text):
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
