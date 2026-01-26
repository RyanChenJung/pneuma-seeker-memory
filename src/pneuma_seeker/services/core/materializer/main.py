# src/pneuma_seeker/core/materializer/main.py
import glob
import os
from logging import Logger
from typing import Any

from pandas import DataFrame

from pneuma_seeker.services.core.api.db import DBAPI
from pneuma_seeker.services.core.api.language_model import LanguageModelAPI
from pneuma_seeker.shared.schemas.core.ir_system import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.services.core.materializer.prompt_factory import MaterializerPromptFactory
from pneuma_seeker.services.core.materializer.state import MaterializerState
from pneuma_seeker.services.core.toolkit.main import Toolkit
from pneuma_seeker.services.core.toolkit.tool.semantic_operator import SyntacticSimMetric
from pneuma_seeker.services.language_model.abstract_model import AbstractModel
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.role import Role
from pneuma_seeker.shared.schemas.language_model.option import LLMOption
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.logger import formatted_log
from pneuma_seeker.shared.parser import parse_code, parse_json


class Materializer:
    """
    Materializer class that orchestrates the materialization
    process using LLMs and various operations.
    """

    def __init__(
        self,
        user_id: str,
        chat_id: str,
        config: Config,
        logger: Logger,
        prov_graph: ProvenanceGraph,
        toolkit: Toolkit,
        db_api: DBAPI,
        language_model_api: LanguageModelAPI,
    ):
        self.user_id = user_id
        self.chat_id = chat_id
        self.config = config
        self.logger = logger
        self.prov_graph = prov_graph
        self.toolkit = toolkit
        self.db_api = db_api
        self.language_model_api = language_model_api

        self.__log(f"Initializing Materializer for user_id: {self.user_id}, chat_id: {self.chat_id}")

        self.prompt_factory = MaterializerPromptFactory(self.config)
        self.state = MaterializerState()

        self.actions: list[str] = []
        self.module_dir = os.path.dirname(os.path.abspath(__file__))

    def materialize_T(
        self,
        T: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        S: str,
        user_side_note="",
        external_tables: list[AbstractDocument] = [],
        prefetched_tables: list[AbstractDocument] = [],
        prefetched_web_search_result: AbstractDocument | None = None,
        prefetched_web_crawl_result: AbstractDocument | None = None,
    ) -> dict[str, DataFrame]:
        """Materialize target tables T based on the provided script S and external tables."""
        self.__log(f"Materializing {len(T)} target tables...")
        self.__cleanup_system()

        if len(prefetched_tables) > 0:
            self.state.retrieved_tables = prefetched_tables

        if prefetched_web_search_result is not None:
            self.state.web_search_result = prefetched_web_search_result
        if prefetched_web_crawl_result is not None:
            self.state.web_crawl_result = prefetched_web_crawl_result

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
            self.__log("=> Planning next materialization action...")
            curr_iteration += 1

            # Prevent forever loop in the worst-case scenario
            if curr_iteration == self.config.MATERIALIZER_HARD_ITERATION_LIMIT:
                break

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
                        self.state.web_crawl_result,
                    ),
                )
            )

            response = "".join(self.language_model_api.chat(llm_messages, LLMOption(json_mode=True)))
            self.__log(f"=> Materialization action selected: {response}")

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
                self.__log("==> Parsing the response...")
                plan: dict[str, Any] = parse_json(response)
            except ValueError as exc:
                error_msg = f"Error parsing the response: {exc}. Please ensure the response is a valid JSON object."
                self.__log(f"==> {error_msg}")
                self.actions.append(error_msg)
                llm_messages.append(
                    LLMMessage(
                        role=Role.SYSTEM.value,
                        content=error_msg,
                    )
                )
                continue

            action_type: str = plan.get("action_type", "")
            if len(action_type) == 0:
                error_msg = "The action_type is not defined. Please define it properly."
                self.__log(f"==> {error_msg}")
                self.actions.append(error_msg)
                llm_messages.append(
                    LLMMessage(
                        role=Role.SYSTEM.value,
                        content=error_msg,
                    )
                )
                continue

            self.__process_action(action_type, plan, external_tables, T)

        self.__log("Materialization completed successfully.")
        final_result: dict[str, DataFrame] = {}
        for intermediate_table_doc in self.state.intermediate_tables:
            if intermediate_table_doc.doc_id in T.keys():
                final_result[intermediate_table_doc.doc_id] = (
                    intermediate_table_doc.content
                )
        return final_result

    def __process_action(
        self,
        action_type: str,
        plan: dict[str, Any],
        external_data: list[AbstractDocument],
        T: dict[str, DataFrame],
    ):
        """Handles a single action in the materialization process."""
        self.__log(f"=> Handling action of type: {action_type}")
        if action_type == "internal_reasoning":
            message: str = plan["message"]
            self.actions.append(f"Reasoned internally: {message}")
        elif action_type == "operation":
            op_name, op_args, assign_to = (
                plan.get("name", ""),
                plan.get("args", {}),
                plan.get("assign_to", ""),
            )

            if len(op_name) == 0:
                error_msg = "The op_name is not defined. Please define it properly."
                self.__log(f"==> {error_msg}")
                self.actions.append(error_msg)
                return

            self.__handle_operation(T, external_data, op_name, op_args, assign_to)
        else:
            error_msg = f"{action_type} is not a valid action."
            self.__log(f"==> {error_msg}")
            self.actions.append(error_msg)

    def __handle_operation(
        self,
        T: dict[str, DataFrame],
        external_data: list[AbstractDocument],
        op_name: str,
        op_args: dict[str, Any],
        assign_to: str,
    ):
        all_tables = self.__gather_all_tables(external_data)
        self.__log(f"==> Executing operation {op_name}...")

        def _create_or_get_read_node(
            doc: AbstractDocument,
            source: RetrieverType,
            python_code: str,
            description: str,
        ) -> str | None:
            try:
                last_id = getattr(doc, "last_node_id", None)
                if last_id is not None:
                    existing = self.prov_graph.get_node_by_id(last_id)
                    if existing is not None:
                        return last_id

                read_node = ProvenanceNode(
                    source_retriever=source,
                    python_code=python_code,
                    description=description,
                )
                self.prov_graph.add_node(read_node, True)
                return read_node.id
            except Exception:
                # On any error, do not crash materializer; return None so caller can handle
                return None

        match op_name:
            case "pneuma_retriever":
                prompt = op_args.get("prompt", "")
                self.state.retrieved_tables = self.toolkit.retrieve_documents(
                    prompt, RetrieverType.PNEUMA_RETRIEVER, 10, True, 5
                )
                if len(self.state.retrieved_tables) == 0:
                    error_msg = (
                        f"No tables were retrieved using this prompt: ```{prompt}```."
                    )
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                else:
                    success_msg = f'Successfully retrieved tables using this prompt: ```{prompt}```. Notice that the "retrieved internal tables" have been filled.'
                    self.__log(f"==> {success_msg}")
                    self.actions.append(success_msg)
                for doc in self.state.retrieved_tables:
                    if doc.path is not None:
                        node_id = _create_or_get_read_node(
                            doc,
                            RetrieverType.PNEUMA_RETRIEVER,
                            self.toolkit.generate_pandas_read_csv_code(doc),
                            "Retrieves an internal table from Pneuma-Retriever.",
                        )
                        if node_id is not None:
                            doc.last_node_id = node_id
            case "web_search":
                if not self.config.ENABLE_WEB_SEARCH:
                    error_msg = "Web search is not enabled in the configuration."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                prompt = op_args.get("prompt", "")
                web_search_results = self.toolkit.retrieve_documents(
                    prompt, RetrieverType.WEB_SEARCH
                )
                if len(web_search_results) == 0:
                    error_msg = "No relevant information was found from web search."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                self.state.web_search_result = web_search_results[0]
                success_msg = f'Successfully retrieved information from Web Search using this prompt: ```{prompt}```. Notice that the "Web search result" have been filled.'
                self.__log(f"==> {success_msg}")
                self.actions.append(success_msg)

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.WEB_SEARCH,
                    python_code=self.toolkit.generate_view_textual_document_code(
                        self.state.web_search_result
                    ),
                    description=f"Searches the web using this query: {prompt}.",
                )
                self.prov_graph.add_node(new_node, True)
                self.state.web_search_result.last_node_id = new_node.id
            case "web_crawl":
                if not self.config.ENABLE_WEB_CRAWL:
                    error_msg = "Web crawl is not enabled in the configuration."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                prompt = op_args.get("url", "")
                web_crawl_results = self.toolkit.retrieve_documents(
                    prompt, RetrieverType.WEB_CRAWL
                )
                if len(web_crawl_results) == 0:
                    error_msg = "No relevant information was found from web crawl."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                self.state.web_crawl_result = web_crawl_results[0]
                success_msg = f'Successfully retrieved information from Web Crawl using this URL: ```{prompt}```. Notice that the "Web crawl result" have been filled.'
                self.__log(f"==> {success_msg}")
                self.actions.append(success_msg)

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.WEB_CRAWL,
                    python_code=self.toolkit.generate_view_textual_document_code(
                        self.state.web_crawl_result
                    ),
                    description=f"Crawls the web page with this URL: {prompt}.",
                )
                self.prov_graph.add_node(new_node, True)
                self.state.web_crawl_result.last_node_id = new_node.id
            case "table_enumerator":
                pattern = op_args.get("pattern", "")
                extra_tables: list[AbstractDocument] = self.toolkit.retrieve_documents(
                    pattern, RetrieverType.ENUMERATOR, 10, True, 5
                )

                if len(extra_tables) > 0:
                    success_msg = f'Successfully retrieved all tables that match the pattern {pattern}. You can use them to materialize T, even if you have not called pneuma_retriever before, as these tables have been included to "retrieved internal tables".'
                    self.__log(f"==> {success_msg}")
                    self.actions.append(success_msg)

                    read_code = self.toolkit.generate_pandas_read_multi_doc_code(
                        extra_tables
                    )
                    new_node = ProvenanceNode(
                        source_retriever=RetrieverType.ENUMERATOR,
                        python_code=read_code,
                        description=f"Enumerates all tables whose names match this regular expression (RegEx) pattern: {pattern}.",
                    )
                    self.prov_graph.add_node(new_node, True)

                    for extra_table in extra_tables:
                        # If extra_table already has a last_node_id that exists in graph,
                        # prefer reusing it; otherwise set to this multi-read node.
                        last_id = getattr(extra_table, "last_node_id", None)
                        if last_id is not None:
                            existing_node = self.prov_graph.get_node_by_id(last_id)
                            if existing_node is not None:
                                continue
                        extra_table.last_node_id = new_node.id

                    existing_tables = self.state.retrieved_tables
                    self.state.retrieved_tables = list(
                        set(existing_tables).union(set(extra_tables))
                    )
                else:
                    error_msg = "There are no tables that match the pattern."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
            case "table_select":
                for target_table_id, retrieved_table_info in op_args.items():
                    if isinstance(retrieved_table_info, list):
                        if len(retrieved_table_info) == 0:
                            msg = f"Skipping {target_table_id!r}: empty list provided as value."
                            self.__log(f"==> {msg}")
                            self.actions.append(msg)
                            continue
                        retrieved_table_info = retrieved_table_info[0]

                    if not isinstance(retrieved_table_info, dict):
                        msg = f"Invalid argument for target {target_table_id!r}: expected a dict."
                        self.__log(f"==> {msg}")
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
                            "Invalid table ID to select. Ensure the table exists."
                        )
                        self.__log(f"==> {error_msg}")
                        self.actions.append(error_msg)
                        return

                    if target_table_id in T:
                        matches = [
                            i for i in all_tables if i.doc_id == table_id_to_select
                        ]
                        if not matches:
                            error_msg = f"Table {table_id_to_select!r} not found in the available tables."
                            self.__log(f"==> {error_msg}")
                            self.actions.append(error_msg)
                            return

                        table_to_select_doc = matches[0]
                        self.__log(
                            f"==> target_table_id: {target_table_id}; table_id_to_select: {table_id_to_select}"
                        )

                        try:
                            table_to_select: DataFrame = table_to_select_doc.content[
                                relevant_columns
                            ]
                        except Exception as e:
                            error_msg = f"Failed selecting columns {relevant_columns!r} from table {table_id_to_select!r}: {e}"
                            self.__log(f"==> {error_msg}")
                            self.actions.append(error_msg)
                            return

                        # Always create a materializer node representing the select operation
                        select_code = self.toolkit.generate_table_select_code(
                            target_table_id,
                            table_to_select_doc.doc_id,
                            relevant_columns,
                        )

                        # Try to create/get a read node for the source doc to connect from
                        parent_node_id = _create_or_get_read_node(
                            table_to_select_doc,
                            table_to_select_doc.retriever_type,
                            self.toolkit.generate_pandas_read_csv_code(
                                table_to_select_doc
                            ),
                            "",
                        )

                        child_node_desc = f"Directly selects a table (ID: `{table_id_to_select}`; columns: {relevant_columns}) to form a target table: `{target_table_id}`"
                        if set(relevant_columns) != set(T[target_table_id].columns):
                            child_node_desc += " (partially)."
                        else:
                            child_node_desc += "."

                        child_node = ProvenanceNode(
                            source_retriever=RetrieverType.MATERIALIZER,
                            python_code=select_code,
                            description=child_node_desc,
                        )

                        self.prov_graph.add_node(child_node, True)
                        new_node_id = child_node.id
                        if parent_node_id is not None:
                            parent_node = self.prov_graph.get_node_by_id(parent_node_id)
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
                        success_msg = "Successfully selected retrieved tables in the mapping as target tables. Notice the state's intermediate tables have changed, but please CHECK if the schemas in the selected tables match, either fully or partially, with the ones in target tables."
                        self.__log(f"==> {success_msg}")
                        self.actions.append(success_msg)
                    else:
                        error_msg = f"Error: The ID {target_table_id} does not exist in T. Please fix it."
                        self.__log(f"==> {error_msg}")
                        self.actions.append(error_msg)
            case "semantic_column_generator":
                table_id: str | None = op_args.get("table_id")
                new_column_name: str | None = op_args.get("new_column_name")
                table_relevant_columns: list[str] | None = op_args.get(
                    "relevant_columns"
                )
                instruction: str | None = op_args.get("instruction")

                if table_id is None or table_id not in [i.doc_id for i in all_tables]:
                    error_msg = "table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if new_column_name is None:
                    error_msg = "new_column_name is not provided."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if table_relevant_columns is None:
                    error_msg = "relevant_columns is not provided."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return

                conditioned_table_doc = [i for i in all_tables if i.doc_id == table_id][
                    0
                ]
                conditioned_table: DataFrame = conditioned_table_doc.content

                if not set(table_relevant_columns) <= set(
                    list(conditioned_table.columns)
                ):
                    error_msg = f"relevant_columns must be a subset of the columns of table {table_id}."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if instruction is None:
                    error_msg = "instruction is not provided."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return

                new_column_values = self.toolkit.generate_semantic_column(
                    conditioned_table[table_relevant_columns],
                    new_column_name,
                    instruction,
                )
                conditioned_table[new_column_name] = new_column_values
                success_msg = f"Successfully added a new column named {new_column_name} to table with ID {table_id}."
                self.__log(f"==> {success_msg}")
                self.actions.append(success_msg)

                sem_col_code = self.toolkit.generate_semantic_col_generator_code(
                    table_relevant_columns,
                    conditioned_table_doc,
                    new_column_name,
                    new_column_values,
                    os.path.join(
                        self._get_intermediate_table_dir_path(),
                        f"{conditioned_table_doc.doc_id}.csv",
                    ),
                )
                # Ensure we have a parent node for the conditioned table (read node)
                parent_node_id = _create_or_get_read_node(
                    conditioned_table_doc,
                    conditioned_table_doc.retriever_type,
                    self.toolkit.generate_pandas_read_csv_code(conditioned_table_doc),
                    "",
                )

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.MATERIALIZER,
                    python_code=sem_col_code,
                    description=f"Semantically generates a column named `{new_column_name}` in the table `{table_id}`, conditioned on the following columns: `{table_relevant_columns}`.",
                )
                self.prov_graph.add_node(new_node, True)
                if parent_node_id is not None:
                    parent_node = self.prov_graph.get_node_by_id(parent_node_id)
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
                    error_msg = "left_table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if right_table_id is None or right_table_id not in all_table_ids:
                    error_msg = "right_table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
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
                    error_msg = (
                        f"left_table with ID {left_table_id} is not a DataFrame."
                    )
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if not isinstance(right_table, DataFrame):
                    error_msg = (
                        f"right_table with ID {right_table_id} is not a DataFrame."
                    )
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return

                if not isinstance(left_table_doc, AbstractDocument):
                    error_msg = f"ID {left_table_id} does not correspond to a document."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if not isinstance(right_table_doc, AbstractDocument):
                    error_msg = (
                        f"ID {right_table_id} does not correspond to a document."
                    )
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return

                if relevant_left_cols is None:
                    error_msg = "relevant_left_cols is not provided."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if relevant_right_cols is None:
                    error_msg = "relevant_right_cols is not provided."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if not set(relevant_left_cols) <= set(list(left_table.columns)):
                    error_msg = (
                        "relevant_left_cols is not a subset of left_table's columns."
                    )
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if not set(relevant_right_cols) <= set(list(right_table.columns)):
                    error_msg = (
                        "relevant_right_cols is not a subset of right_table's columns."
                    )
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return
                if not joined_table_id:
                    error_msg = "joined_table_id is not provided."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
                    return

                joined_table = self.toolkit.semantic_join(
                    left_table,
                    right_table,
                    relevant_left_cols,
                    relevant_right_cols,
                    syntactic_sim_metric=SyntacticSimMetric.JACCARD_QGRAM,
                    top_k=self.config.SEMANTIC_JOIN_TOP_K,
                )

                join_code = self.toolkit.generate_semantic_join_generator_code(
                    left_table_doc,
                    right_table_doc,
                    relevant_left_cols,
                    relevant_right_cols,
                    self.config.SEMANTIC_JOIN_TOP_K,
                    os.path.join(
                        self._get_intermediate_table_dir_path(),
                        f"{joined_table_id}.csv",
                    ),
                )
                parent_node_1_id = _create_or_get_read_node(
                    left_table_doc,
                    left_table_doc.retriever_type,
                    self.toolkit.generate_pandas_read_csv_code(left_table_doc),
                    "",
                )
                parent_node_2_id = _create_or_get_read_node(
                    right_table_doc,
                    right_table_doc.retriever_type,
                    self.toolkit.generate_pandas_read_csv_code(right_table_doc),
                    "",
                )

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.MATERIALIZER,
                    python_code=join_code,
                    description=f"Semantically joins tables `{left_table_id}` and `{right_table_id}` with `top-k = {self.config.SEMANTIC_JOIN_TOP_K}`.",
                )
                self.prov_graph.add_node(new_node, True)
                if parent_node_1_id is not None:
                    parent_node_1 = self.prov_graph.get_node_by_id(parent_node_1_id)
                    if parent_node_1 is not None:
                        self.prov_graph.connect(parent_node_1, new_node)
                if parent_node_2_id is not None:
                    parent_node_2 = self.prov_graph.get_node_by_id(parent_node_2_id)
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
                success_msg = "Successfully joined the left and right tables semantically. Notice the state's intermediate tables have changed."
                self.__log(f"==> {success_msg}")
                self.actions.append(success_msg)
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
                                self._get_intermediate_table_dir_path(),
                                f"{assign_to}.csv",
                            )}",
                        ),
                        description="Executes Python code.",
                    )
                    self.prov_graph.add_node(new_node, True)
                    for parent_node in parent_nodes:
                        # parent_node is already a ProvenanceNode instance
                        if parent_node is None:
                            continue
                        try:
                            self.prov_graph.connect(parent_node, new_node)
                        except Exception:
                            # best-effort: try to resolve by id and connect if present
                            fallback = self.prov_graph.get_node_by_id(parent_node.id)
                            if fallback is not None:
                                try:
                                    self.prov_graph.connect(fallback, new_node)
                                except Exception:
                                    continue

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
                    success_msg = f"Successfully executed the Python code, resulting in a table named {assign_to}"
                    self.__log(f"==> {success_msg}")
                    self.actions.append(success_msg)
                elif isinstance(exec_res, Exception):
                    self.__log(
                        f"==> Exception occured during Python code execution: {exec_res}"
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
                        error_msg = "The `result` variable is empty, which means the Python code did not assign the outcome (e.g., table) to the variable `result`."
                        self.__log(f"==> {error_msg}")
                        self.actions.append(error_msg)
                    else:
                        success_msg = f"Successfully executed the Python code, resulting in this: {exec_res}"
                        self.__log(f"==> {success_msg}")
                        self.actions.append(success_msg)
                        new_node = ProvenanceNode(
                            source_retriever=RetrieverType.MATERIALIZER,
                            python_code=self.toolkit.append_comment_to_existing_code(
                                python_code,
                                "The execution did not result in a DataFrame, but something else.",
                            ),
                            description="Executes Python code.",
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
                        doc = id_docs[used_table_id]
                        source_retrievers.append(doc.retriever_type)
                        last_id = getattr(doc, "last_node_id", None)
                        if last_id is not None:
                            parent_node = self.prov_graph.get_node_by_id(last_id)
                            if parent_node is not None:
                                parent_nodes.append(parent_node)

                    new_node = ProvenanceNode(
                        source_retriever=RetrieverType.MATERIALIZER,
                        python_code=self.toolkit.generate_sql_executor_code(
                            sql_query,
                            id_dfs,
                            os.path.join(
                                self._get_intermediate_table_dir_path(),
                                f"{assign_to}.csv",
                            ),
                        ),
                        description="Executes a SQL query.",
                    )
                    self.prov_graph.add_node(new_node, True)
                    for parent_node in parent_nodes:
                        if parent_node is None:
                            continue
                        try:
                            self.prov_graph.connect(parent_node, new_node)
                        except Exception:
                            fallback = self.prov_graph.get_node_by_id(parent_node.id)
                            if fallback is not None:
                                try:
                                    self.prov_graph.connect(fallback, new_node)
                                except Exception:
                                    continue

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

                    success_msg = f"Successfully executed the SQL query, resulting in a table named {assign_to}"
                    self.__log(f"==> {success_msg}")
                    self.actions.append(success_msg)

                except Exception as e:
                    error_msg = f"Error when executing the SQL query: {e}. Please fix it (you may want to quote identifiers with, for instance, `-` symbol)."
                    self.__log(f"==> {error_msg}")
                    self.actions.append(error_msg)
            case _:
                error_msg = f"{op_name} is not a valid operation."
                self.__log(f"==> {error_msg}")
                self.actions.append(error_msg)

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
                    f"=> Warning: doc {doc.doc_id} has invalid content type {type(doc.content)}"
                )

        self.__log(f"=> all_T_ids: {all_T_ids}")
        self.__log(f"=> materialized_table_ids: {materialized_table_ids}")
        ids_complete = all_T_ids <= materialized_table_ids
        is_complete = ids_complete

        if not ids_complete:
            warning_msg = f"You have not materialized these tables: {all_T_ids - materialized_table_ids}"
            self.__log(f"=> {warning_msg}")
            self.actions.append(warning_msg)

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
        self.__log("Materializer cleanup complete.")

    def __clear_csv_files(self):
        """Delete all .csv files in the module directory."""
        pattern = os.path.join(self._get_intermediate_table_dir_path(), "*.csv")
        for csv_file in glob.glob(pattern):
            try:
                os.remove(csv_file)
            except Exception:
                continue

    def __log(self, text: str):
        formatted_log(self.logger, "MATERIALIZER", text)

    def __save_new_or_updated_intermediate_table(self, table_id: str):
        """Save a new or updated intermediate table to a CSV file."""
        intermediate_table_dir_path = self._get_intermediate_table_dir_path()
        os.makedirs(intermediate_table_dir_path, exist_ok=True)
        csv_path = os.path.join(intermediate_table_dir_path, f"{table_id}.csv")
        intermediate_table: DataFrame | None = None
        for table_doc in self.state.intermediate_tables:
            if table_doc.doc_id == table_id:
                intermediate_table = table_doc.content
                break

        if isinstance(intermediate_table, DataFrame):
            intermediate_table.to_csv(csv_path, index=False)

    def _get_intermediate_table_dir_path(self):
        """Get the directory path for storing intermediate table CSV files."""
        return os.path.join(self.module_dir, "intermediate_data")
