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
        self.state = ICState()
        self.llm = get_llm(llm_path)(llm_path)
        self.embed_model = get_embed_model()(embed_model_path)
        self.chat_history: list[LLMMessage] = []
        self.prompt_factory = ICPromptFactory()
        self.logger = logger
        self.materializer = LLMPlanner(self.llm, self.logger, self.embed_model)

    def process_input(self, user_input: str) -> str:
        """
        Processes the user input, possibly calling tools.
        """
        self.logger.info(f"Start processing this user input: {user_input}")
        is_thinking_done = False
        final_response = ""
        self.chat_history.append(
            LLMMessage(
                role=Role.USER.value,
                content=user_input,
            )
        )

        total_iteration = 0
        iteration_limit = 5  # TODO: Determine limit more dynamically based on, e.g., input-output properties
        while not is_thinking_done and total_iteration < iteration_limit:
            model_output = self.llm.chat(self.chat_history, LLMOption(json_mode=True))
            self.logger.info(f"Model output: {model_output}")
            json_output: LLMConductorOutputType = parse_json(model_output)

            is_direct_response = json_output.get("is_direct_response")
            tool = json_output.get("tool")
            response = json_output.get("response")

            if is_direct_response and isinstance(response, str):
                final_response = response
                self.logger.info(
                    f"=> Get direct response to return to the user: {final_response}"
                )
                is_thinking_done = True
            elif tool and isinstance(response, dict):
                if tool == ToolType.IR_SYSTEM:
                    ir_system = LMInterface({"llm": self.llm, "embed_model": self.embed_model})
                    context = ir_system.retrieve_documents(response["prompt"], response["sources"], response["k"])
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM.value,
                            content=f"The context requested: {context}",
                        )
                    )
                elif tool == ToolType.MATERIALIZER_ENGINE:
                    current_state = self.state.get_state()
                    materialized_target_schemas = (
                        self.materializer.materialize_target_schemas(
                            current_state["target_schemas"], current_state["sqls"]
                        )
                    )
                    self.state.set_state(
                        current_state["sqls"], materialized_target_schemas
                    )
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM.value,
                            content="The target schema has been materialized. You can ask the user if they want to execute the SQL statements to get the answer to their information need. It's possible that they decide to reset the state.",
                        )
                    )
                elif tool == ToolType.STATE_MANIPULATION:
                    new_sqls = response["new_sqls"]
                    new_target_schemas: dict[str, list[str]] = response["new_target_schemas"]
                    new_target_schemas_df: dict[str, DataFrame] = dict()
                    for i in new_target_schemas:
                        new_target_schemas_df[i] = DataFrame(columns=literal_eval(i))
                    self.state.set_state(new_sqls, new_target_schemas_df)
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM.value,
                            content="The state has been adjusted as requested.",
                        )
                    )
                elif tool == ToolType.SQL_ENGINE:
                    result = self.__execute_sqls()
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM.value,
                            content=f"The SQLs have been executed, and this is the output: {result}",
                        )
                    )
            else:
                raise ValueError("The JSON output is invalid.")
            total_iteration += 1
        if total_iteration == iteration_limit and not is_thinking_done:
            self.chat_history.append(
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content=self.prompt_factory.get_force_produce_final_response_prompt(total_iteration)
                )
            )
            final_response = self.llm.chat(self.chat_history)
        return final_response

    def __execute_sqls(self) -> DataFrame | str:
        """
        Executes the SQLs (sequentially) over the target schemas.
        The result (for now) is a scalar (converted to string).
        """
        curr_state = self.state.get_state()
        tables: dict[str, DataFrame] = curr_state["target_schemas"]
        sqls: list[str] = curr_state["sqls"]

        # Create an in-memory DuckDB connection
        con = duckdb.connect(database=':memory:')

        # Register each table into DuckDB
        for table_name, df in tables.items():
            con.register(table_name, df)

        result = DataFrame()
        for sql in sqls:
            result = con.execute(sql).fetchdf()

        # If the result has only one cell, return it as a scalar string
        if result is not None and result.shape == (1, 1):
            return str(result.iat[0, 0])

        return result
