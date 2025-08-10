import duckdb

from logging import Logger
from pandas import DataFrame
from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.prompt_factory import ConductorPromptFactory
from pneuma_seeker.core.conductor.state import InformationNeedState
from pneuma_seeker.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from pneuma_seeker.core.ir_system.lm_interface import LMInterface
from pneuma_seeker.core.materializer.main import Materializer
from pneuma_seeker.model.interface.model_factory import get_embed_model, get_llm
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.utils.json_processor import parse_json, parse_sql


ITERATION_LIMIT = 5
PAST_INTERACTIONS_LIMIT = 5


class Conductor:
    def __init__(
        self,
        llm_path: str,
        embed_model_path: str,
        logger: Logger,
        data_sources: list[str],
    ) -> None:
        self.llm = get_llm(llm_path)(llm_path)
        self.embed_model = get_embed_model()(embed_model_path)
        self.logger = logger
        self.prompt_factory = ConductorPromptFactory()
        self.data_sources = data_sources

        self.info_need_state = InformationNeedState()
        self.interaction_history: list[HumanConductorInteraction] = []

        self.current_retrieval_results: dict[RetrieverType, list[AbstractDocument]] = (
            dict()
        )

        self.materializer = Materializer(
            self.llm, self.logger, self.embed_model, data_sources
        )

    def process_input(self, human_input: str, human_id: str, subsequent_chat: bool):
        self.logger.info(f"Processing human input: {human_input}")
        if subsequent_chat:
            human_input += " (Note: please check the current state (target schemas & sqls), if already defined, are they still relevant, or do they need any adjustments? For sqls, ensure all queries use ONLY available columns in the target schemas, so we do not run into errors.)"

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
                        self.interaction_history,
                        actions_taken,
                        self.current_retrieval_results,
                        human_input,
                    ),
                )
            )

            llm_output = self.llm.chat(llm_messages, LLMOption(json_mode=True))
            llm_messages.append(
                LLMMessage(role=Role.ASSISTANT.value, content=llm_output)
            )
            action = parse_json(llm_output)
            intent: str = action.get("intent")
            actions_taken.append(intent)
            action_message: None | str = action.get("message")
            tool: None | str = action.get("tool")
            args: None | dict = action.get("args")

            if intent == "communicate_with_user" and isinstance(action_message, str):
                self.interaction_history.append(
                    HumanConductorInteraction(human_input, action_message)
                )
                user_facing_response = action_message
                is_user_facing_response = True
            elif intent == "internal_reasoning" and isinstance(action_message, str):
                self.logger.info(f"DEBUGGY: num_actions_taken: {num_actions_taken}")
                self.logger.info(f"actions_taken[-1]: {actions_taken[-1]}")
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
                tool_outcome = self.__execute_tool(tool, args, llm_messages)
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
            user_facing_response = self.llm.chat(llm_messages)
            self.interaction_history.append(
                HumanConductorInteraction(human_input, user_facing_response)
            )
        yield user_facing_response

    def __execute_tool(
        self, tool: str, args: str | dict, llm_messages: list[LLMMessage]
    ) -> str:
        if (tool == "IR System" or tool == "ir_system") and isinstance(args, dict):
            self.logger.info(f"IR System request with params: {args}")
            ir_system = LMInterface(
                {"llm": self.llm, "embed_model": self.embed_model},
                self.logger,
            )
            self.current_retrieval_results = ir_system.retrieve_documents(
                args["prompt"],
                self.data_sources,
                10,  # Future-TODO: Change hard-coded sources and k
            )
            return "Successfully retrieved documents from the IR system. Notice that the `RETRIEVED DATA` has been updated."
        elif (
            tool == "State Manipulation" or tool == "state_manipulation"
        ) and isinstance(args, dict):
            self.logger.info(f"State Manipulation request with params: {args}")
            target_schemas: dict[str, list[str]] | None = args.get("target_schemas")
            column_descriptions: dict[str, dict[str, str]] | None = args.get(
                "column_descriptions"
            )
            sqls: list[str] | None = args.get("sqls")

            is_target_schemas_modified = False
            if target_schemas is not None and column_descriptions is not None:
                if column_descriptions is not None:
                    target_schemas_df: dict[str, DataFrame] = dict()
                    for schema_id in target_schemas:
                        target_schemas_df[schema_id] = DataFrame(
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
        elif tool == "Materializer Engine" or tool == "materializer_engine":
            self.logger.info(f"Materializer Engine called")
            note = ""
            if isinstance(args, dict) and "note" in args:
                note = args.get("note", "")
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
        elif tool == "SQL Engine" or tool == "sql_engine":
            self.logger.info("SQL Engine called")
            execution_result: list[str] = []
            if not self.info_need_state.is_target_schemas_materialized:
                return "Target schemas have not been materialized, so running SQL Engine will produce empty results. Call Materializer Engine first, then you can call SQL Engine."
            if len(self.info_need_state.sqls) == 0:
                return "sqls is still empty, which means there is nothing to execute. Please define the sql queries first in the state's sqls, then ensure target schemas have been materialized using Materializer Engine. Finally, you can call SQL Engine again to execute them."
            execution_result = self.__execute_sqls()

            self.logger.info(f"SQL execution result output: {execution_result}")
            return (
                f"Executed the SQLs, which resulted in this output: {execution_result}"
            )
        elif (
            tool == "Categorical Column Information"
            or tool == "categorical_column_information"
        ):
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
                        table: DataFrame = document.content
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
        tables: dict[str, DataFrame] = self.info_need_state.target_schemas
        sqls: list[str] = self.info_need_state.sqls

        self.logger.info(
            f"Executing {sqls} SQL statements on the (materialized) target schemas"
        )

        # Register each table into DuckDB
        for table_name, df in tables.items():
            con.register(table_name, df)

        results: list[DataFrame] = []
        for sql_idx, sql in enumerate(sqls):
            self.logger.info(f"Sanity checking the SQL query {sql}")
            relevant_tables: dict[str, DataFrame] = dict()
            for table_id, table in tables.items():
                if table_id in sql:
                    relevant_tables[table_id] = table
            fixed_sql = parse_sql(
                self.llm.chat(
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
            )
            self.info_need_state.sqls[sql_idx] = fixed_sql
            try:
                self.logger.info(f"Executing Fixed SQL: {fixed_sql}")
                result = con.execute(fixed_sql).fetchdf()
                results.append(result)
            except Exception as e:
                results = [
                    DataFrame(
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

    def __format_available_tables(self, tables: dict[str, DataFrame]):
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
