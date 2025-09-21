import json
import os
import re
from collections.abc import Generator
from logging import Logger

import pandas as pd
import requests

from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.prompt_factory import ConductorPromptFactory
from pneuma_seeker.core.conductor.state import InformationNeedState
from pneuma_seeker.core.conductor.toolkit import Toolkit
from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.model.interface.model_factory import get_embed_model, get_llm
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.utils.cleaner import clean_column_table_name
from pneuma_seeker.utils.config import Config
from pneuma_seeker.utils.logger import formatted_log
from pneuma_seeker.utils.parser import parse_json


class Conductor:
    def __init__(
        self,
        llm_path: str,
        embed_model_path: str,
        logger: Logger,
        data_sources: list[str],
        config: Config,
        iteration_limit=5,
    ) -> None:
        self.llm = get_llm(llm_path, self.config)(llm_path, self.config, self.logger)
        self.embed_model = get_embed_model()(embed_model_path, self.config, self.logger)
        self.logger = logger
        self.data_sources = data_sources
        self.config = config
        self.iteration_limit = iteration_limit

        self.prov_graph = ProvenanceGraph(self.logger)
        self.prompt_factory = ConductorPromptFactory()
        self.toolkit = Toolkit(
            self.llm,
            self.embed_model,
            self.logger,
            self.data_sources,
            self.prov_graph,
            self.prompt_factory,
        )

        self.info_need_state = InformationNeedState()
        self.current_retrieval_results: dict[RetrieverType, list[AbstractDocument]] = {}
        self.external_documents: list[AbstractDocument] = []
        self.enumerated_table_ids: list[str] = []

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
        external_data_paths: list[str],
    ):
        self.__log(f"Processing human input: {user_input}")
        if len(interaction_history) > 0:
            user_input += " (Note: please check the current state (target schemas & sqls), if already defined, are they still relevant, or do they need any adjustments? For sqls, ensure all queries use ONLY available columns in the target schemas, so we do not run into errors.)"

        self.__process_external_data(external_data_paths)

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
                        self.current_retrieval_results,
                        user_input,
                        self.enumerated_table_ids,
                        self.external_documents,
                    ),
                )
            )

            llm_output_gen = self.llm.chat(
                llm_messages, LLMOption(json_mode=True, stream=True)
            )
            stream_gen, raw_buffer = self.__stream_message_content_from_chunks(
                llm_output_gen
            )
            for char in stream_gen:
                yield char
                is_user_facing_response = True  # we saw at least one streamed char

            full_response = "".join(raw_buffer) if raw_buffer else ""
            if full_response:
                llm_messages.append(
                    LLMMessage(role=Role.ASSISTANT.value, content=full_response)
                )

            try:
                action = parse_json(full_response)
            except Exception:
                action = {}

            intent: str = action.get("action", "")
            actions_taken.append(intent)
            action_message: None | str = action.get("message")
            tool: None | str = action.get("tool")
            args: None | dict = action.get("args")

            if intent == "communicate_with_user" and isinstance(action_message, str):
                user_facing_response = action_message
                is_user_facing_response = True
            elif intent == "internal_reasoning" and isinstance(action_message, str):
                self.logger.debug(f"num_actions_taken: {num_actions_taken}")
                self.logger.debug(f"actions_taken[-1]: {actions_taken[-1]}")
                yield "LOG: Performing internal reasoning..."
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
                    tool = intent
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

    def __process_external_data(self, external_data_paths):
        if len(external_data_paths) > 0:
            self.__log("Utilizing external data...")
            self.external_documents = self.__unpack_external_data(external_data_paths)
            for doc in self.external_documents:
                new_node = ProvenanceNode(
                    output_data_id=doc.doc_id,
                    output_data_ref={"doc_path": doc.path or ""},
                    source_retriever=RetrieverType.USER,
                    op_description="User-uploaded data",
                )
                self.prov_graph.add_node(new_node, True)
                doc.last_node_id = new_node.id

    def __unpack_external_data(
        self, external_data_paths: list[str]
    ) -> list[AbstractDocument]:
        external_docs: list[AbstractDocument] = []
        os.makedirs("temp", exist_ok=True)
        for data_path in external_data_paths:
            if data_path.startswith("/api") or data_path.startswith("api"):
                if self.config.OPENWEBUI_BASE_URL.endswith(
                    "/"
                ) and data_path.startswith("/"):
                    data_path = data_path[1:]
                if data_path.endswith("/content"):
                    data_path = data_path[: -len("/content")]
                data_url = self.config.OPENWEBUI_BASE_URL + data_path

                resp = requests.get(
                    data_url,
                    headers={
                        "Authorization": f"Bearer {self.config.OPENWEBUI_API_KEY}"
                    },
                )
                resp.raise_for_status()

                content_type = resp.headers.get("Content-Type", "").lower()

                if "csv" in content_type or "excel" in content_type:
                    # direct file (csv/xlsx)
                    ext = ".csv" if "csv" in content_type else ".xlsx"
                    local_path = os.path.join("temp", f"downloaded{ext}")
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                elif "json" in content_type:
                    # metadata wrapper
                    meta = resp.json()
                    file_path = meta.get("path")
                    if not file_path or not os.path.exists(file_path):
                        raise ValueError(
                            f"Invalid API response, no usable file path: {meta}"
                        )
                    local_path = file_path
                else:
                    raise ValueError(f"Unsupported content type: {content_type}")

                try:
                    external_docs.extend(self.__read_external_data_content(local_path))
                finally:
                    if local_path.startswith("temp") and os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
            else:
                external_docs.extend(self.__read_external_data_content(data_path))
        return external_docs

    def __read_external_data_content(self, path: str) -> list[AbstractDocument]:
        """
        Reads external data (CSV or Excel) and returns a list of Table documents.

        Args:
            path (str): Path to the input file.

        Returns:
            list[AbstractDocument]: A list of Table documents.
        """
        retriever_type = RetrieverType.USER
        external_data_content: list[AbstractDocument] = []

        def extract_file_stem(filepath: str) -> str:
            """Extracts the filename without extension."""
            return os.path.splitext(filepath)[0].split("/")[-1]

        if path.endswith((".xls", ".xlsx")):
            excel_name = extract_file_stem(path)

            sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
            for original_name, df in sheets.items():
                standardized_name = f"{clean_column_table_name(excel_name)}_{clean_column_table_name(original_name)}"
                standardized_df = df.rename(columns=clean_column_table_name)

                external_data_content.append(
                    Table(
                        doc_id=standardized_name,
                        retriever_type=retriever_type,
                        content=standardized_df,
                        metadata={"sheet_name": original_name},  # provenance kept
                        path=path,
                    )
                )
        elif path.endswith(".csv"):
            file_stem = extract_file_stem(path)
            df = pd.read_csv(path).rename(columns=clean_column_table_name)

            external_data_content.append(
                Table(
                    doc_id=clean_column_table_name(file_stem),
                    retriever_type=retriever_type,
                    content=df,
                    metadata={},
                    path=path,
                )
            )
        else:
            raise ValueError(f"Unsupported file format: {path}")

        return external_data_content

    def __execute_tool(
        self, tool: str, args: str | dict, user_id: str, chat_id: str
    ) -> str:
        if tool == "ir_system":
            self.__log(f"IR System request with params: {args}")

            if not isinstance(args, dict):
                error_message = "=> `args` must be an object with a `prompt` property"
                self.__log(f"=> {error_message}")
                return error_message
            if "prompt" not in args:
                error_message = "=> `args` must have a `prompt` property"
                self.__log(f"=> {error_message}")
                return error_message

            self.current_retrieval_results = (
                self.toolkit.retrieve_multi_retriever_documents(args["prompt"])
            )
            return "Successfully retrieved documents from the IR system. Notice that the `RETRIEVED DATA` has been updated."
        elif tool == "table_enumerator":
            self.__log(f"Table Enumerater request with params: {args}")

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
        elif tool == "state_manipulation":
            self.__log(f"State Manipulation request with params: {args}")

            if not isinstance(args, dict):
                error_message = "`args` must be an object"
                self.__log(f"=> {error_message}")
                return error_message

            target_schemas: dict[str, list[str]] | None = args.get("target_schemas")
            column_descriptions: dict[str, dict[str, str]] | None = args.get(
                "column_descriptions"
            )
            sqls: list[str] | None = args.get("sqls")

            is_target_schemas_modified = False
            if target_schemas is not None and column_descriptions is not None:
                if column_descriptions is not None:
                    target_schemas_docs: dict[str, AbstractDocument] = dict()
                    for schema_id in target_schemas:
                        target_schema_df = pd.DataFrame(
                            columns=target_schemas[schema_id]
                        )

                        target_schema_path = os.path.join(
                            self.target_tables_path,
                            user_id,
                            chat_id,
                            f"{schema_id}.csv",
                        )
                        os.makedirs(os.path.dirname(target_schema_path), exist_ok=True)

                        target_schema_df.to_csv(target_schema_path, index=False)
                        target_schemas_docs[schema_id] = Table(
                            doc_id=schema_id,
                            retriever_type=RetrieverType.CONDUCTOR,
                            content=target_schema_df,
                            metadata={},
                            path=target_schema_path,
                        )

                    self.info_need_state.target_schemas = target_schemas_docs
                    self.info_need_state.column_descriptions = column_descriptions
                    self.info_need_state.is_target_schemas_materialized = False
                    is_target_schemas_modified = True
                else:
                    return "If you want to change target_schemas, make sure to also define column_descriptions."

            is_sqls_modified = False
            if sqls is not None:
                self.info_need_state.sqls = sqls
                self.info_need_state.is_sql_executed = False
                is_sqls_modified = True

            if is_target_schemas_modified and is_sqls_modified:
                return (
                    "Successfully modified both the target schemas and the SQL queries."
                )
            if is_target_schemas_modified:
                return "Successfully modified the target schemas."
            if is_sqls_modified:
                return "Successfully modified the SQL queries."
            return "No modification is done."
        elif tool == "materializer":
            if len(self.info_need_state.target_schemas.keys()) == 0:
                error_message = "Target schemas have to already be defined before calling Materializer"
                self.__log(f"=> {error_message}")
                return error_message

            note = ""
            if isinstance(args, dict) and "note" in args:
                note = args["note"]

            self.__log(f"Materializer called (note: {note})")

            self.info_need_state.target_schemas = self.toolkit.materialize_T(
                self.info_need_state.target_schemas,
                self.info_need_state.column_descriptions,
                self.info_need_state.sqls,
                note,
                self.external_documents,
                self.current_retrieval_results,
            )
            self.info_need_state.is_target_schemas_materialized = True

            for _, T_doc in self.info_need_state.target_schemas.items():
                updated_content: pd.DataFrame = T_doc.content
                updated_content.to_csv(T_doc.path, index=False)

            return "Successfully materialized the target schemas."
        elif tool == "sql_engine":
            self.__log("SQL Engine called")
            execution_result: list[str] = []
            if not self.info_need_state.is_target_schemas_materialized:
                error_message = "Target schemas have not been materialized, so running SQL Engine will produce empty results. Call Materializer first, then you can call SQL Engine."
                self.__log(f"=> {error_message}")
                return error_message
            if len(self.info_need_state.sqls) == 0:
                error_message = "sqls is still empty, which means there is nothing to execute. Please define the sql queries first in the state's sqls, then ensure target schemas have been materialized using Materializer, and finally, you can call SQL Engine again."
                self.__log(f"=> {error_message}")
                return error_message

            execution_result = self.toolkit.execute_sql(
                self.info_need_state.target_schemas,
                self.info_need_state.sqls,
            )
            self.__log(f"SQL execution result output: {execution_result}")

            self.info_need_state.is_sql_executed = True
            return (
                f"Executed the SQLs, which resulted in this output: {execution_result}"
            )
        elif tool == "categorical_column_information":
            if isinstance(args, dict):
                self.__log(
                    f"categorical_column_information request with params: {args}"
                )
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

                for document in self.current_retrieval_results[RetrieverType.PNEUMA]:
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

    def __log(self, text):
        formatted_log(self.logger, "CONDUCTOR", text)

    def __stream_message_content_from_chunks(
        self,
        chunks: Generator[str, None, None],
    ) -> tuple[Generator[str, None, None], list[str]]:
        """
        Consumes chunks from LLM generator and yield only the 'message' content
        of communicate_with_user actions/intents, ignoring JSON wrappers.
        Returns:
            - A generator that streams the message chunks
            - A mutable list containing the full concatenated output
        """
        raw_buffer: list[str] = []

        def _stream():
            buffer = ""
            json_regex = re.compile(r"\{.*?\}")

            for chunk in chunks:
                buffer += chunk
                raw_buffer.append(chunk)

                while True:
                    match = json_regex.search(buffer)
                    if not match:
                        break

                    json_str = match.group()
                    try:
                        action = json.loads(json_str)
                    except json.JSONDecodeError:
                        break

                    buffer = buffer[match.end() :]
                    intent = action.get("intent") or action.get("action")
                    message_text = action.get("message")

                    if intent == "communicate_with_user" and isinstance(
                        message_text, str
                    ):
                        for char in self.__stream_message_by_whitespace(message_text):
                            yield char

        return _stream(), raw_buffer

    def __stream_message_by_whitespace(
        self, message: str
    ) -> Generator[str, None, None]:
        """
        Yields parts of the message whenever whitespace is encountered,
        so the frontend receives word-level streaming.
        """
        buffer = ""
        for c in message:
            buffer += c
            if c.isspace():
                yield buffer
                buffer = ""
        if buffer:
            yield buffer
