from collections.abc import Generator
import json
import os
import re
from typing import Optional

import duckdb
import pandas as pd

from logging import Logger
from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.prompt_factory import ConductorPromptFactory
from pneuma_seeker.core.conductor.state import InformationNeedState
from pneuma_seeker.core.conductor.table_enumerator import table_enumerator
from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.core.ir_system.main import IRSystem
from pneuma_seeker.core.ir_system.retriever.impl.pneuma import clean_name
from pneuma_seeker.core.materializer.main import Materializer
from pneuma_seeker.model.interface.model_factory import get_embed_model, get_llm
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.utils.parser import parse_json, parse_sql


ITERATION_LIMIT = 5
PAST_INTERACTIONS_LIMIT = 5


class Conductor:
    def __init__(
        self,
        llm_path: str,
        embed_model_path: str,
        logger: Logger,
        data_sources: list[str],
        env_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.llm = get_llm(llm_path)(llm_path)
        self.embed_model = get_embed_model()(embed_model_path)
        self.logger = logger
        self.data_sources = data_sources

        self.prompt_factory = ConductorPromptFactory()
        self.materializer = Materializer(
            self.llm, self.logger, self.embed_model, self.data_sources
        )

        self.info_need_state = InformationNeedState()
        self.current_retrieval_results: dict[RetrieverType, list[AbstractDocument]] = (
            dict()
        )
        self.external_data: list[AbstractDocument] = []
        self.enumerated_table_ids: list[str] = []

    def process_input(
        self,
        human_input: str,
        human_id: str,
        interaction_history: list[HumanConductorInteraction],
        external_data_paths: list[str],
    ):
        self.logger.info(f"Processing human input: {human_input}")
        if len(interaction_history) > 0:
            human_input += " (Note: please check the current state (target schemas & sqls), if already defined, are they still relevant, or do they need any adjustments? For sqls, ensure all queries use ONLY available columns in the target schemas, so we do not run into errors.)"

        if len(external_data_paths) > 0:
            self.logger.info("Utilizing external data...")
            self.external_data = self.__unpack_external_data(external_data_paths)

        num_actions_taken = 0
        user_facing_response = ""
        is_user_facing_response = False
        llm_messages = [
            LLMMessage(
                role=Role.SYSTEM.value,
                content=self.prompt_factory.get_sys_prompt(ITERATION_LIMIT),
            )
        ]
        actions_taken: list[str] = []
        while not is_user_facing_response and num_actions_taken < ITERATION_LIMIT:
            num_actions_taken += 1
            llm_messages.append(
                LLMMessage(
                    role=Role.USER.value,
                    content=self.prompt_factory.get_env_state_prompt(
                        num_actions_taken,
                        ITERATION_LIMIT,
                        self.info_need_state,
                        interaction_history,
                        actions_taken,
                        self.current_retrieval_results,
                        human_input,
                        self.enumerated_table_ids,
                        self.external_data,
                    ),
                )
            )

            # Get streaming generator from LLM
            llm_output_gen = self.llm.chat(
                llm_messages, LLMOption(json_mode=True, stream=True)
            )

            # IMPORTANT: stream_message_content_from_chunks returns (stream_gen, raw_buffer)
            # where raw_buffer is a mutable list the stream helper appends raw chunks into.
            stream_gen, raw_buffer = stream_message_content_from_chunks(llm_output_gen)

            # Stream user-facing characters immediately (if any).
            # Do NOT try to build the full_response from these chars — they are ONLY the
            # user-facing 'message' parts, not the full assistant output (JSON wrappers, etc.).
            for char in stream_gen:
                yield char
                is_user_facing_response = True  # we saw at least one streamed char

            full_response = "".join(raw_buffer) if raw_buffer else ""
            # Append full response to message history (so the next LLM call gets a history)
            if full_response:
                llm_messages.append(
                    LLMMessage(role=Role.ASSISTANT.value, content=full_response)
                )

            # Parse action from accumulated response
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
                            content=f"You cannot select `internal_reasoning` consecutively. Please select a different action!",
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
                tool_outcome = self.__execute_tool(tool, args)
                llm_messages.append(
                    LLMMessage(role=Role.USER.value, content=tool_outcome)
                )

        if not is_user_facing_response:
            self.logger.info("Force produce user-facing response")
            llm_messages.append(
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content=self.prompt_factory.get_direct_response_anyway_prompt(),
                )
            )
            # Consume generator fully
            user_facing_response = "".join(
                self.llm.chat(llm_messages, LLMOption(stream=True))
            )
            yield user_facing_response

    def __unpack_external_data(
        self, external_data_paths: list[str]
    ) -> list[AbstractDocument]:
        external_docs: list[AbstractDocument] = []
        for data_path in external_data_paths:
            if data_path.startswith("http"):
                raise ValueError("API reading is not implemented yet.")
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
                standardized_name = (
                    f"{clean_name(excel_name)}_{clean_name(original_name)}"
                )
                standardized_df = df.rename(columns=clean_name)

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
            df = pd.read_csv(path).rename(columns=clean_name)

            external_data_content.append(
                Table(
                    doc_id=clean_name(file_stem),
                    retriever_type=retriever_type,
                    content=df,
                    metadata={},
                    path=path,
                )
            )
        else:
            raise ValueError(f"Unsupported file format: {path}")

        return external_data_content

    def __execute_tool(self, tool: str, args: str | dict) -> str:
        if tool == "ir_system" and isinstance(args, dict):
            self.logger.info(f"IR System request with params: {args}")
            ir_system = IRSystem(self.llm, self.embed_model, self.logger)
            self.current_retrieval_results = ir_system.retrieve_documents(
                args["prompt"],
                self.data_sources,
                10,  # Future-TODO: Change hard-coded sources and k
            )
            return "Successfully retrieved documents from the IR system. Notice that the `RETRIEVED DATA` has been updated."
        elif tool == "table_enumerator" and isinstance(args, dict):
            self.logger.info(f"Table Enumerater request with params: {args}")
            pattern: str = args.get("pattern", "")
            self.enumerated_table_ids = table_enumerator(pattern)
            return f"Enumerated table IDs based on this pattern: {pattern}. If there are any matches, the IDs will be reflected in `OTHER TABLE IDS WITH SIMILAR NAMING PATTERNS`."
        elif tool == "state_manipulation" and isinstance(args, dict):
            self.logger.info(f"State Manipulation request with params: {args}")
            target_schemas: dict[str, list[str]] | None = args.get("target_schemas")
            column_descriptions: dict[str, dict[str, str]] | None = args.get(
                "column_descriptions"
            )
            sqls: list[str] | None = args.get("sqls")

            is_target_schemas_modified = False
            if target_schemas is not None and column_descriptions is not None:
                if column_descriptions is not None:
                    target_schemas_df: dict[str, pd.DataFrame] = dict()
                    for schema_id in target_schemas:
                        target_schemas_df[schema_id] = pd.DataFrame(
                            columns=target_schemas[schema_id]
                        )
                    self.info_need_state.target_schemas = target_schemas_df
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
            elif is_target_schemas_modified:
                return "Successfully modified the target schemas."
            elif is_sqls_modified:
                return "Successfully modified the SQL queries."
            return "No modification is done."
        elif tool == "materializer":
            note = ""
            if isinstance(args, dict) and "note" in args:
                note = args["note"]
            self.logger.info(f"Materializer called")
            self.info_need_state.target_schemas = (
                self.materializer.materialize_target_schemas(
                    self.info_need_state.target_schemas,
                    self.info_need_state.column_descriptions,
                    self.info_need_state.sqls,
                    note,
                )
            )
            self.info_need_state.is_target_schemas_materialized = True
            return "Successfully materialized the target schemas."
        elif tool == "sql_engine":
            self.logger.info("SQL Engine called")
            execution_result: list[str] = []
            if not self.info_need_state.is_target_schemas_materialized:
                return "Target schemas have not been materialized, so running SQL Engine will produce empty results. Call Materializer first, then you can call SQL Engine."
            if len(self.info_need_state.sqls) == 0:
                return "sqls is still empty, which means there is nothing to execute. Please define the sql queries first in the state's sqls, then ensure target schemas have been materialized using Materializer. Finally, you can call SQL Engine again to execute them."
            execution_result = self.__execute_sqls()

            self.logger.info(f"SQL execution result output: {execution_result}")
            return (
                f"Executed the SQLs, which resulted in this output: {execution_result}"
            )
        elif tool == "categorical_column_information":
            if isinstance(args, dict):
                table_id: str | None = args.get("id")
                table_columns: list[str] | None = args.get("columns")
                if table_id is None:
                    return "The `id` field most not be empty."
                if table_columns is None:
                    return "The `columns` field most not be empty."
                if not isinstance(table_columns, list) or len(table_columns) == 0:
                    return "The `columns` field must be a non-empty list of strings (column names in the table)"

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

        return "Tool calling failed."

    def __execute_sqls(self):
        """
        Executes the SQLs (sequentially) over the target schemas.
        The result (for now) is a scalar (converted to string).
        """
        # Create an in-memory DuckDB connection
        con = duckdb.connect(database=":memory:")
        tables: dict[str, pd.DataFrame] = self.info_need_state.target_schemas
        sqls: list[str] = self.info_need_state.sqls

        self.logger.info(
            f"Executing {sqls} SQL statements on the (materialized) target schemas"
        )

        # Register each table into DuckDB
        for table_name, df in tables.items():
            con.register(table_name, df)

        results: list[pd.DataFrame] = []
        for sql_idx, sql in enumerate(sqls):
            self.logger.info(f"Sanity checking the SQL query {sql}")
            relevant_tables: dict[str, pd.DataFrame] = dict()
            for table_id, table in tables.items():
                if table_id in sql:
                    relevant_tables[table_id] = table
            response = self.llm.chat(
                [
                    LLMMessage(
                        role=Role.SYSTEM.value,
                        content=self.prompt_factory.sql_sanity_checking_prompt(),
                    ),
                    LLMMessage(
                        role=Role.USER.value,
                        content=f"SQL Query: {sql}\n\nRelevant Tables: {self.__format_available_tables(relevant_tables)}",
                    ),
                ]
            )
            response = "".join(response)
            fixed_sql = parse_sql(response)
            self.info_need_state.sqls[sql_idx] = fixed_sql
            try:
                self.logger.info(f"Executing Fixed SQL: {fixed_sql}")
                result = con.execute(fixed_sql).fetchdf()
                results.append(result)
            except Exception as e:
                results = [
                    pd.DataFrame(
                        columns=["error"],
                        data=[
                            [
                                f"Error encountered when executing this SQL: ```{fixed_sql}``` on the target schemas: {e}. Please proceed with internal_reasoning to think what causes the issue (e.g., referencing non-existent tables, non-standard SQL, etc.) and how to fix it."
                            ]
                        ],
                    )
                ]
                print(e)
                break

        # If the result has only one cell, return it as a scalar string
        self.info_need_state.is_sql_executed = True
        final_output: list[str] = []
        for result in results:
            if result.shape == (1, 1):
                final_output.append(str(result.iat[0, 0]))
            else:
                final_output.append(str(result))
        return final_output

    def __format_available_tables(self, tables: dict[str, pd.DataFrame]):
        tables_repr = ""
        for table_id, table in tables.items():
            tables_repr += (
                f"\n- Table {table_id}:\ncol: {" | ".join(list(table.columns))}"
            )
            if len(table) > 0:
                # Sample 5 rows to represent the table
                sample_rows = table.sample(min(5, len(table)), random_state=42)
                sample_row_idx = 1
                for _, data in sample_rows.iterrows():
                    str_data = [str(i) for i in data]
                    tables_repr += (
                        f"\nsample row {sample_row_idx}: {" | ".join(str_data)}"
                    )
                    sample_row_idx += 1
        return tables_repr.strip()


def stream_message_content_from_chunks(
    chunks: Generator[str, None, None],
) -> tuple[Generator[str, None, None], list[str]]:
    """
    Consume chunks from LLM generator and yield only the 'message' content
    of communicate_with_user intents, ignoring JSON wrappers.
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
                if (
                    action.get("intent") == "communicate_with_user"
                    and "message" in action
                ):
                    message_text = action["message"]
                    for char in stream_message_by_whitespace(message_text):
                        yield char  # stream immediately

    return _stream(), raw_buffer


def stream_message_by_whitespace(message: str) -> Generator[str, None, None]:
    """
    Yield parts of the message whenever whitespace is encountered,
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
