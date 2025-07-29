from logging import Logger
import duckdb
from pandas import DataFrame
from processor.core.interaction_conductor.ic_data_model import Interaction
from processor.core.interaction_conductor.ic_prompt_factory import ICPromptFactory
from processor.core.interaction_conductor.ic_state import InformationNeedState
from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.llm_planner import LLMPlanner
from processor.model.interface.model_factory import get_embed_model, get_llm
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption
from processor.utils.json_processor import parse_json, parse_sql


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

    def process_input(self, human_input: str, human_id: str) -> str:
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
                user_facing_response = action_message
                is_user_facing_response = True
            elif intent == "internal_reasoning" and isinstance(action_message, str):
                llm_messages.append(
                    LLMMessage(
                        role=Role.USER.value,
                        content=f"You did some internal reasoning: {action_message}",
                    )
                )
            elif (
                intent == "tool_call"
                or intent != "communicate_with_user"
                or intent != "internal_reasoning"
            ) and tool is not None:
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
            user_facing_response = self.llm.chat(llm_messages)
            self.interaction_history.append(
                Interaction(human_input, user_facing_response)
            )
        return user_facing_response

    def __execute_tool(self, tool: str, args: str | dict) -> str:
        if tool == "IR System" and isinstance(args, dict):
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
        elif tool == "State Manipulation" and isinstance(args, dict):
            self.logger.info(f"State Manipulation request with params: {args}")
            target_schemas: dict[str, list[str]] | None = args.get("target_schemas")
            column_descriptions: dict[str, dict[str, str]] | None = args.get(
                "column_descriptions"
            )
            sqls: list[str] | None = args.get("sqls")

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
                modifications_happening = True

            if modifications_happening:
                return "Successfully modified the state."
            return "No modification is done."
        elif tool == "Materializer Engine":
            self.logger.info(f"Materializer Engine called")
            self.info_need_state.target_schemas = (
                self.materializer.materialize_target_schemas(
                    self.info_need_state.target_schemas,
                    self.info_need_state.column_descriptions,
                    self.info_need_state.sqls,
                )
            )
            self.info_need_state.is_target_schemas_materialized = True
            return "Successfully materialized the target schemas."
        elif tool == "SQL Engine":
            self.logger.info("SQL Engine called")
            execution_result: str = ""
            if not self.info_need_state.is_target_schemas_materialized:
                return "Target schemas have not been materialized, so running SQL Engine will produce empty results."
            if len(self.info_need_state.sqls) == 0:
                return "sqls is still empty, which means there is nothing to execute."
            execution_result = self.__execute_sqls()

            self.logger.info(f"SQL execution result output: {execution_result}")
            return (
                f"Executed the SQLs, which resulted in this output: {execution_result}"
            )
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

        result = DataFrame()
        for sql in sqls:
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
                            content="""You are a SQL query fixer. Given an input SQL query, check if it contains any syntactic or semantic errors (e.g., case sensitivity, unescaped identifiers, invalid field names, type mismatches, or non-standard functions for the target SQL engine: DuckDB). Fix the query as needed to ensure it runs correctly in the specified engine. Use double quotes for identifiers (e.g., "Beach Name" instead of Beach Name), and handle case sensitivity appropriately for string comparisons. Output the updated/fixed/same-if-no-issue SQL query directly without any explanation or formatting.""",
                        ),
                        LLMMessage(
                            role=Role.USER.value,
                            content=f"SQL Query: {sql}\n\nRelevant Tables: {self.__format_available_tables(relevant_tables)}",
                        ),
                    ]
                )
            )
            self.logger.info(f"Executing Fixed SQL: {fixed_sql}")
            result = con.execute(fixed_sql).fetchdf()

        self.logger.info(f"Final result shape: {result.shape}")

        # If the result has only one cell, return it as a scalar string
        if result is not None and result.shape == (1, 1):
            return str(result.iat[0, 0])

        return str(result)

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
