from ast import literal_eval
from logging import Logger

import duckdb
from pandas import DataFrame

from processor.core.interaction_conductor.ic_prompt_factory import ICPromptFactory
from processor.core.interaction_conductor.ic_state import ICState
from processor.core.interaction_conductor.ic_data_model import (
    LLMConductorOutputType,
    ToolType,
)
from processor.core.ir_system.ir_data_model import convert_retrieval_results_to_str
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.llm_planner import LLMPlanner
from processor.core.interaction_conductor.ic_data_model import ToolType
from processor.model.interface.model_factory import get_embed_model, get_llm
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption
from processor.utils.json_processor import parse_json


class LLMConductor:
    def __init__(self, llm_path: str, embed_model_path: str, logger: Logger):
        """
        Initializes the LLM Conductor with a state, and materializer.
        """
        self.logger = logger
        self.logger.info(
            f"Initializing LLMConductor with llm_path={llm_path}, embed_model_path={embed_model_path}"
        )
        self.state = ICState()
        self.llm = get_llm(llm_path)(llm_path)
        self.embed_model = get_embed_model()(embed_model_path)
        self.prompt_factory = ICPromptFactory()
        self.materializer = LLMPlanner(self.llm, self.logger, self.embed_model)
        self.curr_thinking_action_history: list[str] = []
        self.conversations: list[LLMMessage] = []

    def process_input(self, user_input: str) -> str:
        """
        Processes the user input, possibly calling tools.
        """
        self.logger.info(f"Start processing this user input: {user_input}")
        is_thinking_done = False
        final_response = ""
        total_iteration = 0
        iteration_limit = 3  # TODO: Determine limit more dynamically based on, e.g., input-output properties
        self.conversations.append(LLMMessage(role=Role.USER.value, content=user_input))
        self.curr_thinking_action_history = []
        while not is_thinking_done and total_iteration < iteration_limit:
            llm_messages = [
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content=self.prompt_factory.get_input_processing_prompt(
                        self.state.sqls,
                        self.state.target_schemas,
                        user_input,
                        self.curr_thinking_action_history,
                        (
                            self.conversations[-3:]
                            if len(self.conversations) >= 3
                            else self.conversations
                        ),
                    ),
                )
            ]
            self.logger.info("Below is the current chat history:")
            self.logger.info("Conversation history:\n" + "\n".join(
                f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.conversations
            ))
            model_output = self.llm.chat(llm_messages, LLMOption(json_mode=True))
            self.logger.info(f"Model output: {model_output}")
            json_output: LLMConductorOutputType = parse_json(model_output)
            self.logger.info(f"Parsed JSON output: {json_output}")

            is_direct_response = json_output.get("is_direct_response")
            tool = json_output.get("tool")
            response = json_output.get("response")

            if is_direct_response and isinstance(response, str):
                final_response = response
                self.logger.info(
                    f"=> Get direct response to return to the user: {final_response}"
                )
                self.conversations.append(
                    LLMMessage(role=Role.ASSISTANT.value, content=final_response)
                )
                is_thinking_done = True
            elif tool and isinstance(response, dict):
                self.logger.info(f"Using tool: {tool}")
                if tool == ToolType.IR_SYSTEM.value:
                    self.logger.info(f"IR System request with params: {response}")
                    ir_system = LMInterface(
                        {"llm": self.llm, "embed_model": self.embed_model}
                    )
                    context = ir_system.retrieve_documents(
                        response["prompt"], ["buysite"], 5  # Hard-coded sources and k
                    )
                    self.logger.info(f"Retrieved context length: {len(str(context))}")

                    context_str = "Retrieving documents from the IR system. The results:\n"
                    for retriever_type in context.keys():
                        retrieved_documents = context[retriever_type]
                        context_str += f"""- Retriever {retriever_type.value}:\n{convert_retrieval_results_to_str(retrieved_documents)}"""
                    self.curr_thinking_action_history.append(
                        context_str
                    )
                elif tool == ToolType.MATERIALIZER_ENGINE.value:
                    self.logger.info("Starting materialization of target schemas")
                    current_state = self.state.get_state()
                    materialized_target_schemas = (
                        self.materializer.materialize_target_schemas(
                            self.__convert_target_schemas_to_target_columns(),
                            current_state["sqls"],
                        )
                    )
                    self.logger.info(
                        f"Materialized schemas count: {len(materialized_target_schemas)}"
                    )
                    self.state.set_state(
                        current_state["sqls"], materialized_target_schemas
                    )
                    self.curr_thinking_action_history.append(
                        "Materializing the target schemas"
                    )
                elif tool == ToolType.STATE_MANIPULATION.value:
                    self.logger.info("Manipulating state with new values")
                    new_sqls = response["new_sqls"]
                    self.logger.info(f"New SQLs count: {len(new_sqls)}")
                    new_target_schemas: dict[str, list[str]] = response[
                        "new_target_schemas"
                    ]
                    new_target_schemas_df: dict[str, DataFrame] = dict()
                    for i in new_target_schemas:
                        new_target_schemas_df[i] = DataFrame(columns=literal_eval(i))
                    self.state.set_state(new_sqls, new_target_schemas_df)
                    self.curr_thinking_action_history.append(
                        f"Adjusting the state (refer to the latest state)."
                    )
                elif tool == ToolType.SQL_ENGINE.value:
                    self.logger.info("Executing SQL statements")
                    result = self.__execute_sqls()
                    self.logger.info(f"SQL execution result type: {type(result)}")
                    self.curr_thinking_action_history.append(
                        f"Executing the SQLs, resulting in this output: {result}"
                    )
            else:
                raise ValueError("The JSON output is invalid.")
            total_iteration += 1
        if total_iteration == iteration_limit and not is_thinking_done:
            llm_messages = [
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content=self.prompt_factory.get_force_produce_final_response_prompt(
                        total_iteration, self.curr_thinking_action_history
                    ),
                )
            ]
            final_response = self.llm.chat(llm_messages)
            self.conversations.append(LLMMessage(role=Role.ASSISTANT.value, content=final_response))
        return final_response

    def __convert_target_schemas_to_target_columns(self):
        target_columns: dict[str, list[str]] = dict()
        for target_schema_id in self.state.target_schemas.keys():
            target_columns[target_schema_id] = list(
                self.state.target_schemas[target_schema_id].columns
            )
        return target_columns

    def __execute_sqls(self) -> DataFrame | str:
        """
        Executes the SQLs (sequentially) over the target schemas.
        The result (for now) is a scalar (converted to string).
        """
        curr_state = self.state.get_state()
        self.logger.info(
            f"Executing {len(curr_state['sqls'])} SQL statements on {len(curr_state['target_schemas'])} tables"
        )
        tables: dict[str, DataFrame] = curr_state["target_schemas"]
        sqls: list[str] = curr_state["sqls"]

        # Create an in-memory DuckDB connection
        con = duckdb.connect(database=":memory:")

        # Register each table into DuckDB
        for table_name, df in tables.items():
            con.register(table_name, df)

        result = DataFrame()
        for sql in sqls:
            self.logger.info(f"Executing SQL: {sql}")
            result = con.execute(sql).fetchdf()

        self.logger.info(f"Final result shape: {result.shape}")

        # If the result has only one cell, return it as a scalar string
        if result is not None and result.shape == (1, 1):
            return str(result.iat[0, 0])

        return result
