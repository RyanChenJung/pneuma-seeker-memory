import os
from logging import Logger

import pandas as pd

from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.prompt_factory import ConductorPromptFactory
from pneuma_seeker.core.conductor.state import InformationNeedState
from pneuma_seeker.core.shared.toolkit.main import Toolkit
from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.core.materializer.main import Materializer
from pneuma_seeker.model.interface.model_factory import get_embed_model, get_llm
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.utils.config import Config
from pneuma_seeker.utils.logger import formatted_log
from pneuma_seeker.utils.parser import parse_json
from pneuma_seeker.utils.table_reader import TableReader


class Conductor:
    def __init__(
        self,
        llm_path: str,
        embed_model_path: str,
        logger: Logger,
        data_sources: list[str],
        config: Config,
        prov_graph: ProvenanceGraph,
    ) -> None:
        self.config = config
        self.logger = logger

        self.llm = get_llm(llm_path, self.config)(llm_path, self.config, self.logger)
        self.embed_model = get_embed_model()(embed_model_path, self.config, self.logger)

        self.data_sources = data_sources
        self.iteration_limit = config.CONDUCTOR_ITERATION_LIMIT

        self.prov_graph = prov_graph
        self.prompt_factory = ConductorPromptFactory(self.config)

        self.toolkit = Toolkit(
            self.llm,
            self.embed_model,
            self.logger,
            self.data_sources,
            self.prov_graph,
            self.config,
        )
        self.materializer = Materializer(
            self.llm,
            self.embed_model,
            self.logger,
            self.data_sources,
            self.prov_graph,
            self.toolkit,
            self.config,
        )
        self.table_reader = TableReader(
            self.config.OPENWEBUI_BASE_URL, self.config.OPENWEBUI_API_KEY
        )

        self.info_need_state = InformationNeedState()
        self.retrieved_tables: list[AbstractDocument] = []
        self.external_tables: list[AbstractDocument] = []
        self.enumerated_table_ids: list[str] = []
        self.web_search_result: AbstractDocument | None = None
        self.web_crawl_result: AbstractDocument | None = None

        self.target_tables_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "..",
            "..",
            "data_src",
            "target_tables",
        )

    def process_input(
        self,
        user_input: str,
        user_id: str,
        chat_id: str,
        interaction_history: list[HumanConductorInteraction],
        external_table_paths: list[str],
    ):
        """Processes user input and yields responses."""
        self.__log(f"Processing human input: {user_input}")
        self.external_tables = self.table_reader.process_external_tables(
            external_table_paths
        )
        if len(self.external_tables) > 0:
            self.__log("Utilizing external table data...")
            for index, doc in enumerate(self.external_tables):
                last_id = getattr(doc, "last_node_id", None)
                if (
                    last_id is not None
                    and self.prov_graph.get_node_by_id(last_id) is not None
                ):
                    continue

                new_node = ProvenanceNode(
                    source_retriever=RetrieverType.USER,
                    python_code=self.toolkit.generate_read_external_tables_code(
                        index + 1, doc
                    ),
                    description="Reads a user-uploaded table.",
                )
                self.prov_graph.add_node(new_node, True)
                doc.last_node_id = new_node.id

        num_actions_taken = 0
        user_facing_response = ""
        is_user_facing_response = False
        actions_taken: list[str] = []
        llm_messages = [
            LLMMessage(
                role=Role.SYSTEM.value,
                content=self.prompt_factory.get_sys_prompt(self.iteration_limit),
            )
        ]

        while not is_user_facing_response and num_actions_taken < self.iteration_limit:
            num_actions_taken += 1
            llm_messages.append(
                LLMMessage(
                    role=Role.USER.value,
                    content=self.prompt_factory.get_env_state_prompt(
                        num_actions_taken,
                        self.iteration_limit,
                        self.info_need_state,
                        interaction_history,
                        actions_taken,
                        self.retrieved_tables,
                        user_input,
                        self.enumerated_table_ids,
                        self.external_tables,
                        self.web_search_result,
                        self.web_crawl_result,
                    ),
                )
            )

            full_response = "".join(
                self.llm.chat(llm_messages, LLMOption(json_mode=True, stream=True))
            )
            llm_messages.append(
                LLMMessage(role=Role.ASSISTANT.value, content=full_response)
            )

            try:
                action_plan = parse_json(full_response)
            except ValueError as exc:
                self.__log(f"Failed to parse LLM response as JSON: {exc}")
                num_actions_taken -= 1
                llm_messages.append(
                    LLMMessage(
                        role=Role.USER.value,
                        content="The response is not valid JSON. Please follow the specified format and try again.",
                    )
                )
                continue

            action: str = action_plan.get("action", "")
            actions_taken.append(action)
            action_message: None | str = action_plan.get("message")
            tool: None | str = action_plan.get("tool")
            args: None | dict = action_plan.get("args")

            if action == "communicate_with_user" and isinstance(action_message, str):
                user_facing_response = action_message
                is_user_facing_response = True
            elif action == "internal_reasoning" and isinstance(action_message, str):
                self.logger.debug(f"num_actions_taken: {num_actions_taken}")
                self.logger.debug(f"actions_taken[-1]: {actions_taken[-1]}")
                yield "LOG: Reasoning internally..."
                if num_actions_taken > 1 and actions_taken[-1] == "internal_reasoning":
                    llm_messages.append(
                        LLMMessage(
                            role=Role.USER.value,
                            content="You cannot select `internal_reasoning` consecutively. Please select a different action!",
                        )
                    )
                else:
                    llm_messages.append(
                        LLMMessage(
                            role=Role.USER.value,
                            content=f"You did some internal reasoning: {action_message}",
                        )
                    )
            elif args is not None:
                if tool is None:
                    tool = action
                yield f"LOG: Calling tool: {tool}..."
                tool_outcome = self.__execute_tool(tool, args, user_id, chat_id)
                llm_messages.append(
                    LLMMessage(role=Role.USER.value, content=tool_outcome)
                )

        if not is_user_facing_response:
            self.__log("Force produce user-facing response")
            llm_messages.append(
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content=self.prompt_factory.get_direct_response_anyway_prompt(),
                )
            )
            user_facing_response = "".join(
                self.llm.chat(llm_messages, LLMOption(stream=True))
            )

        yield user_facing_response

    def __execute_tool(
        self, tool: str, args: str | dict, user_id: str, chat_id: str
    ) -> str:
        """Executes a specified tool with given arguments."""
        if tool == "pneuma_retriever":
            self.__log(f"Pneuma-Retriever request with params: {args}")

            if not isinstance(args, dict):
                error_message = "=> `args` must be an object with a `prompt` property"
                self.__log(f"=> {error_message}")
                return error_message
            if "prompt" not in args:
                error_message = "=> `args` must have a `prompt` property"
                self.__log(f"=> {error_message}")
                return error_message

            self.retrieved_tables = self.toolkit.retrieve_documents(
                args["prompt"], RetrieverType.PNEUMA_RETRIEVER
            )
            return "Successfully retrieved tables from Pneuma-Retriever. Notice that the `RETRIEVED TABLES` has been updated."
        if tool == "web_search" and self.config.ENABLE_WEB_SEARCH:
            self.__log(f"Web Search request with params: {args}")
            if not isinstance(args, dict):
                error_message = "=> `args` must be an object with a `prompt` property"
                self.__log(f"=> {error_message}")
                return error_message
            if "prompt" not in args:
                error_message = "=> `args` must have a `prompt` property"
                self.__log(f"=> {error_message}")
                return error_message

            retrieved_docs = self.toolkit.retrieve_documents(
                args["prompt"], RetrieverType.WEB_SEARCH
            )
            self.web_search_result = (
                retrieved_docs[0] if len(retrieved_docs) > 0 else None
            )
            if self.web_search_result is None:
                return "No relevant information was found from Web Search."
            return "Successfully retrieved information from Web Search. Notice that the `WEB SEARCH RESULT` has been updated."
        if tool == "web_crawl" and self.config.ENABLE_WEB_CRAWL:
            self.__log(f"Web Crawl request with params: {args}")
            if not isinstance(args, dict):
                error_message = "=> `args` must be an object with a `url` property"
                self.__log(f"=> {error_message}")
                return error_message
            if "url" not in args:
                error_message = "=> `args` must have a `url` property"
                self.__log(f"=> {error_message}")
                return error_message

            retrieved_docs = self.toolkit.retrieve_documents(
                args["url"], RetrieverType.WEB_CRAWL
            )
            self.web_crawl_result = (
                retrieved_docs[0] if len(retrieved_docs) > 0 else None
            )
            if self.web_crawl_result is None:
                return "No relevant information was found from Web Crawl."
            return "Successfully retrieved information from Web Crawl. Notice that the `WEB CRAWL RESULT` has been updated."
        if tool == "table_enumerator":
            self.__log(f"Table Enumerator request with params: {args}")

            if not isinstance(args, dict):
                error_message = "`args` must be an object with a `pattern` property"
                self.__log(f"=> {error_message}")
                return error_message
            if "pattern" not in args:
                error_message = "`args` must have a `pattern` property"
                self.__log(f"=> {error_message}")
                return error_message

            enumerated_tables = self.toolkit.retrieve_documents(
                args["pattern"], RetrieverType.ENUMERATOR
            )
            self.enumerated_table_ids = [i.doc_id for i in enumerated_tables]
            return f"Enumerated table IDs based on this pattern: {args["pattern"]}. If there are any matches, the IDs will be reflected in `OTHER TABLE IDS WITH SIMILAR NAMING PATTERNS`."
        if tool == "state_manipulation":
            self.__log(f"State Manipulation request with params: {args}")

            if not isinstance(args, dict):
                error_message = "`args` must be an object"
                self.__log(f"=> {error_message}")
                return error_message

            T: dict[str, list[str]] | None = args.get("T")
            column_descriptions: dict[str, dict[str, str]] | None = args.get(
                "column_descriptions"
            )
            S: str | None = args.get("S")

            is_T_modified = False
            if T is not None and column_descriptions is not None:
                if column_descriptions is not None:
                    T_docs: dict[str, AbstractDocument] = dict()
                    for schema_id in T:
                        target_schema_df = pd.DataFrame(columns=T[schema_id])

                        target_schema_path = os.path.join(
                            self.target_tables_path,
                            user_id,
                            chat_id,
                            f"{schema_id}.csv",
                        )
                        os.makedirs(os.path.dirname(target_schema_path), exist_ok=True)

                        target_schema_df.to_csv(target_schema_path, index=False)
                        T_docs[schema_id] = Table(
                            doc_id=schema_id,
                            retriever_type=RetrieverType.CONDUCTOR,
                            content=target_schema_df,
                            metadata={},
                            path=target_schema_path,
                        )

                    self.info_need_state.T = T_docs
                    self.info_need_state.column_descriptions = column_descriptions
                    self.info_need_state.is_T_materialized = False
                    is_T_modified = True
                else:
                    return "If you want to change T, make sure to also define column_descriptions."

            is_S_modified = False
            if S is not None:
                self.info_need_state.S = S
                self.info_need_state.is_S_executed = False
                is_S_modified = True

            if is_T_modified and is_S_modified:
                return "Successfully modified both T and S."
            if is_T_modified:
                return "Successfully modified T."
            if is_S_modified:
                return "Successfully modified S."
            return "No modification is done."
        if tool == "materializer":
            if len(self.info_need_state.T.keys()) == 0:
                error_message = (
                    "T has to already be defined before calling Materializer"
                )
                self.__log(f"=> {error_message}")
                return error_message

            note = ""
            if isinstance(args, dict) and "note" in args:
                note = args["note"]

            self.__log(f"Materializer called (note: {note})")

            self.info_need_state.T = self.__materialize_T_driver(
                self.info_need_state.T,
                self.info_need_state.column_descriptions,
                self.info_need_state.S,
                note,
                self.external_tables,
            )
            self.info_need_state.is_T_materialized = True

            for _, T_doc in self.info_need_state.T.items():
                updated_content: pd.DataFrame = T_doc.content
                updated_content.to_csv(T_doc.path, index=False)

            return "Successfully materialized T."
        if tool == "executor":
            self.__log("Executor called")
            execution_result: str = ""
            if not self.info_need_state.is_T_materialized:
                error_message = "T has not been materialized, so running Executor will produce useful results. Call Materializer first, then you can call Executor."
                self.__log(f"=> {error_message}")
                return error_message
            if len(self.info_need_state.S) == 0:
                error_message = "S is still empty, which means there is nothing to execute. Please define S first, then ensure T has been materialized using Materializer, and finally, you can call Executor again."
                self.__log(f"=> {error_message}")
                return error_message

            T_df: dict[str, pd.DataFrame] = {}
            for t_id, i in self.info_need_state.T.items():
                T_df[t_id] = i.content

            execution_result = self.toolkit.python_executor.execute_code(
                T_df, self.info_need_state.S
            )["exec_res"]
            self.__log(f"Script (S) execution result: {execution_result}")

            self.info_need_state.is_S_executed = True
            return f"Executed S, which resulted in this output: {execution_result}"
        if tool == "categorical_column_info":
            if isinstance(args, dict):
                self.__log(f"categorical_column_info request with params: {args}")
                table_id: str | None = args.get("id")
                table_columns: list[str] | None = args.get("columns")
                if table_id is None:
                    error_message = "The `id` field most not be empty."
                    self.__log(f"=> {error_message}")
                    return error_message
                if table_columns is None:
                    error_message = "The `columns` field most not be empty."
                    self.__log(f"=> {error_message}")
                    return error_message
                if not isinstance(table_columns, list) or len(table_columns) == 0:
                    error_message = "The `columns` field must be a non-empty list of strings (column names in the table)"
                    self.__log(f"=> {error_message}")
                    return error_message

                for document in self.retrieved_tables:
                    if document.doc_id == table_id:
                        cat_col_info = ""
                        table: pd.DataFrame = document.content
                        for column in table_columns:
                            if column not in table.columns:
                                cat_col_info += (
                                    f"Column `{column}` does not exist in the table.\n"
                                )
                                continue

                            counts = table[column].value_counts()
                            top_values = counts.index[:10].tolist()

                            # Append "truncated" if there are more than 10 unique values
                            if len(counts) > 10:
                                top_values.append("truncated")

                            # Convert list to string for cleaner display
                            top_values_str = ", ".join(str(v) for v in top_values)
                            column_info = f"{column}: {top_values_str}\n"
                            cat_col_info += column_info
                        return cat_col_info

                return f"ID {table_id} does not exist; ensure it exists in the current retrieval results."
            else:
                return "Argument must be a specified key-value pairs with keys `id` and `columns`."

        return f"Tool calling failed; {tool} is unknown"

    def __materialize_T_driver(
        self,
        T: dict[str, AbstractDocument],
        col_descriptions: dict[str, dict[str, str]],
        S: str,
        user_side_note: str,
        external_tables: list[AbstractDocument],
    ):
        T_dfs: dict[str, pd.DataFrame] = {}
        for T_id, T_doc in T.items():
            T_dfs[T_id] = T_doc.content

        materialized_T_dfs = self.materializer.materialize_T(
            T_dfs,
            col_descriptions,
            S,
            user_side_note,
            external_tables,
            self.retrieved_tables,
        )

        materialized_T: dict[str, AbstractDocument] = {}
        for T_id, T_df in materialized_T_dfs.items():
            materialized_T[T_id] = T[T_id]
            materialized_T[T_id].content = T_df
        return materialized_T

    def __log(self, text):
        formatted_log(self.logger, "CONDUCTOR", text)
