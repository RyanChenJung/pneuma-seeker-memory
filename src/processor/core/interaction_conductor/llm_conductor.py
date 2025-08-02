from logging import Logger
from typing import Any
import duckdb
from pandas import DataFrame
from processor.core.interaction_conductor.ic_data_model import Interaction
from processor.core.interaction_conductor.ic_prompt_factory import ICPromptFactory
from processor.core.interaction_conductor.ic_state import InformationNeedState
from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.llm_planner import LLMPlanner
from processor.core.materializer_engine.operation.python_executor import (
    execute_python_code,
)
from processor.model.interface.model_factory import get_embed_model, get_llm
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption
from processor.utils.json_processor import parse_code, parse_json, parse_sql


ITERATION_LIMIT = 5
PAST_INTERACTIONS_LIMIT = 5


class LLMConductor:
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

        self.info_need_state = InformationNeedState()
        self.interaction_history: list[Interaction] = []

        self.prompt_factory = ICPromptFactory()
        self.current_retrieval_results: dict[RetrieverType, list[AbstractDocument]] = (
            dict()
        )

        self.materializer = LLMPlanner(
            self.llm, self.logger, self.embed_model, data_sources
        )
        self.data_sources = data_sources

    def process_input(
        self, human_input: str, human_id: str, subsequent_chat: bool
    ) -> str:
        if subsequent_chat:
            human_input += " (Note: please check the current state (target schemas & sqls), if already defined, are they still relevant, or do they need any adjustments?)"
        self.logger.info(f"Processing human input: {human_input}")
        # self.logger.info(f"Preliminary step: extracting domain knowledge")
        # domain_knowledge_extraction_messages = [
        #     LLMMessage(
        #         role=Role.SYSTEM.value,
        #         content=self.prompt_factory.get_knowledge_extraction_prompt(
        #             human_input
        #         ),
        #     )
        # ]
        # domain_knowledge_extraction_decision = self.llm.chat(
        #     domain_knowledge_extraction_messages, LLMOption(json_mode=True)
        # )
        # extraction_decision_json = parse_json(domain_knowledge_extraction_decision)
        # if extraction_decision_json["contains_domain_knowledge"]:
        #     domain_knowledge: list[str] = extraction_decision_json["domain_knowledge"]
        #     self.logger.info(f"=> Domain knowledge extracted: {domain_knowledge}")
        #     domain_knowledge_docs: list[AbstractDocument] = [
        #         Knowledge(
        #             doc_id="new_doc",
        #             retriever_type=RetrieverType.KNOWLEDGE_BASE,
        #             content=curr_domain_knowledge,
        #             metadata={"type": "global", "user": human_id},
        #         )
        #         for curr_domain_knowledge in domain_knowledge
        #     ]
        #     ir_system = LMInterface(
        #         {"llm": self.llm, "embed_model": self.embed_model},
        #         self.logger,
        #     )
        #     ir_system.index_documents(
        #         RetrieverType.KNOWLEDGE_BASE, domain_knowledge_docs
        #     )

        num_iteration = 0
        user_facing_response = ""
        is_user_facing_response = False
        llm_messages = [
            LLMMessage(
                role=Role.SYSTEM.value,
                content=self.prompt_factory.get_sys_prompt(ITERATION_LIMIT),
            )
        ]
        actions_taken: list[str] = []
        while not is_user_facing_response and num_iteration < ITERATION_LIMIT:
            num_iteration += 1
            llm_messages.append(
                LLMMessage(
                    role=Role.USER.value,
                    content=self.prompt_factory.get_env_state_prompt(
                        num_iteration,
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
            """Format of action:
            {
                "intent": "communicate_with_user" | "internal_reasoning" | "tool_call",
                "message": null | "<string>",
                "tool": null | "IR System" | "Materializer Engine" | "State Manipulation" | "SQL Engine",
                "args": null | { ... }
            }
            """
            action = parse_json(llm_output)
            intent: str = action.get("intent")
            action_message: None | str = action.get("message")
            tool: None | str = action.get("tool")
            args: None | dict = action.get("args")

            if intent == "communicate_with_user" and isinstance(action_message, str):
                self.interaction_history.append(
                    Interaction(human_input, action_message)
                )
                if num_iteration > 1:
                    user_facing_response = action_message
                    is_user_facing_response = True
            elif intent == "internal_reasoning" and isinstance(action_message, str):
                llm_messages.append(
                    LLMMessage(
                        role=Role.USER.value,
                        content=f"You did some internal reasoning: {action_message}",
                    )
                )
            else:
                if tool is None:
                    tool = intent
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
                Interaction(human_input, user_facing_response)
            )
        return user_facing_response

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
            return "Successfully retrieved documents from the IR system. Notice that the `PREVIOUSLY RETRIEVED DATA FROM THE IR SYSTEM` has been updated."
        elif (
            tool == "State Manipulation" or tool == "state_manipulation"
        ) and isinstance(args, dict):
            self.logger.info(f"State Manipulation request with params: {args}")
            target_schemas: dict[str, list[str]] | None = args.get("target_schemas")
            column_descriptions: dict[str, dict[str, str]] | None = args.get(
                "column_descriptions"
            )
            sqls: list[str] | None = args.get("sqls", [])

            modifications_happening = False
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
                    modifications_happening = True
                else:
                    return "If you want to change target_schemas, make sure to also define column_descriptions."

            if sqls is not None:
                self.info_need_state.sqls = sqls
                self.info_need_state.is_sql_executed = False
                modifications_happening = True

            if modifications_happening:
                self.logger.info(f"=> Self-loop, sanity checking of state modification")
                modification_validation_messages = [llm_messages[0]]
                modification_validation_messages.append(
                    LLMMessage(
                        role=Role.ASSISTANT.value,
                        content=f"Performed state modification: {args}"
                    )
                )
                modification_validation_messages.append(
                    LLMMessage(
                        role=Role.USER.value,
                        content="""You just decided to manipulate the state, so we need to sanity-check the modification, ensuring you do not miss important columns in your design, and the SQLs are indeed based on the target schema IDs.
To do this, you need to perform an `internal_reasoning` action. Reflect out loud whether the manipulation makes sense given your goal with this change.""",
                    )
                )
                first_action_llm_output = self.llm.chat(
                    modification_validation_messages, LLMOption(json_mode=True)
                )
                internal_reflection_info: dict[str, str] = parse_json(
                    first_action_llm_output
                )
                internal_reflection = internal_reflection_info.get("message", "")
                self.logger.info(f"==> INTERNAL REFLECTION: {internal_reflection}")
                modification_validation_messages.extend(
                    [
                        LLMMessage(
                            role=Role.ASSISTANT.value,
                            content=f"I just reflected internally: {internal_reflection}",
                        ),
                        LLMMessage(
                            role=Role.USER.value,
                            content="""Now that you have reflected internally, it is time to perform "tool_call": State Manipulation.""",
                        ),
                    ]
                )

                second_action_llm_output = self.llm.chat(
                    modification_validation_messages, LLMOption(json_mode=True)
                )
                state_manipulation_info: dict[str, Any] = parse_json(
                    second_action_llm_output
                )
                state_manipulation_args: None | dict[str, Any] = (
                    state_manipulation_info.get("args")
                )

                self.logger.info(f"==> ARGS: {state_manipulation_args}")

                if state_manipulation_args is not None:
                    target_schemas: dict[str, list[str]] | None = (
                        state_manipulation_args.get("target_schemas")
                    )
                    column_descriptions: dict[str, dict[str, str]] | None = (
                        state_manipulation_args.get("column_descriptions")
                    )
                    sqls: list[str] | None = state_manipulation_args.get("sqls")

                    if target_schemas is not None:
                        target_schemas_df: dict[str, DataFrame] = dict()
                        for schema_id in target_schemas:
                            target_schemas_df[schema_id] = DataFrame(
                                columns=target_schemas[schema_id]
                            )
                        self.info_need_state.target_schemas = target_schemas_df
                        self.info_need_state.is_target_schemas_materialized = False

                    if column_descriptions is not None:
                        self.info_need_state.column_descriptions = column_descriptions

                    if sqls is not None:
                        self.info_need_state.sqls = sqls
                        self.info_need_state.is_sql_executed = False

                return "Successfully modified the state with sanity-checking."
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
        
        elif tool == "Categorical Column Information" or tool == "categorical_column_information":
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
                                cat_col_info += f"Column `{column}` does not exist in the table.\n"
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
                            content="""You are a SQL query fixer for DuckDB. 
Given an input SQL query, check for syntactic or semantic errors (case sensitivity, unescaped identifiers, invalid field names, type mismatches, or unsupported functions).
Ensure the query ONLY accesses available tables in the target schemas. If not, convert it to an equivalent SQL query.
Fix the query so it runs correctly in DuckDB, replacing non-standard or unsupported functions with SQL-standard equivalents when possible. 
If no standard equivalent exists, use the closest DuckDB-supported function. 
Use double quotes for identifiers with spaces or special characters, and handle string comparisons case-sensitively where needed. 
Always output only the corrected SQL query, without explanations.""",
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
