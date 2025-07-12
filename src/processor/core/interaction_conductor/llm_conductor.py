from ast import literal_eval
import json
from typing import cast

from pandas import DataFrame

from processor.core.interaction_conductor.ic_prompt_engineer import ICPromptEngineer
from processor.core.interaction_conductor.ic_state import ICState
from processor.core.interaction_conductor.data_model import LLMConductorOutputType, ToolType, IRSystemToolCallingType, StateManipulationToolCallingType
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.llm_planner import LLMPlanner
from processor.core.interaction_conductor.data_model import ToolType
from processor.model.interface.model_factory import get_llm
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption


class LLMConductor:
    def __init__(self, llm_path: str, materializer: LLMPlanner):
        """
        Initializes the LLM Conductor with a state, and materializer.
        """
        self.state = ICState()
        self.llm = get_llm(llm_path)()
        self.chat_history: list[LLMMessage] = []
        self.prompt_engineer = ICPromptEngineer()
        self.materializer = materializer

    def process_input(self, user_input: str) -> str:
        """
        Processes the user input, possibly calling tools.
        """
        is_thinking_done = False
        final_response = ""
        self.chat_history.append(
            LLMMessage(
                user_input,
                Role.USER,
            )
        )
        while not is_thinking_done:
            model_output = self.llm.chat(self.chat_history, LLMOption(json_mode=True))
            json_output: LLMConductorOutputType = json.loads(model_output)
            if json_output["is_direct_response"] and json_output["direct_response"]:
                final_response = json_output["direct_response"]
                is_thinking_done = True
            elif json_output["tool"]:
                tool = json_output["tool"]
                if tool == ToolType.IR_SYSTEM:
                    ir_system_instructions = cast(IRSystemToolCallingType, json_output)
                    retrieval_prompt = ir_system_instructions["prompt"]
                    context = self.retrieve_context(retrieval_prompt)
                    self.chat_history.append(LLMMessage(
                        role=Role.ASSISTANT, content=f"The context requested: {context}"
                    ))
                elif tool == ToolType.MATERIALIZER_ENGINE:
                    current_state = self.state.get_state()
                    materialized_target_schemas = self.materializer.materialize_target_schemas(
                        current_state["target_schemas"], current_state["sqls"]
                    )
                    self.state.set_state(current_state["sqls"], materialized_target_schemas)
                    self.chat_history.append(LLMMessage(
                        role=Role.ASSISTANT, content="The target schema has been materialized. You can ask the user if they want to execute the SQL statements to get the answer to their information need."
                    ))
                elif tool == ToolType.STATE_MANIPULATION:
                    state_manipulation_instructions = cast(StateManipulationToolCallingType, json_output)
                    new_sqls = state_manipulation_instructions["new_sqls"]
                    new_target_schemas = state_manipulation_instructions["new_target_schemas"]
                    new_target_schemas_df = []
                    for i in new_target_schemas:
                        # Assume i is a list of column names
                        new_target_schemas_df.append(
                            DataFrame(columns=literal_eval(i))
                        )
                    self.state.set_state(new_sqls, new_target_schemas_df)
                    self.chat_history.append(LLMMessage(
                        role=Role.ASSISTANT, content="The state has been adjusted as requested."
                    ))
            else:
                raise ValueError("The JSON output is invalid.")

        return final_response

    def retrieve_context(self, prompt: str) -> str:
        """
        Retrieves context from the IR system with auto sanity check mechanism.
        """
        # TODO: Handle provenance information!
        ir_system = LMInterface(self.llm)
        context = ir_system.retrieve(prompt)
        is_make_sense = False
        total_sanity_check_iteration = 0
        sanity_check_messages = [
            LLMMessage(role=Role.USER, content=self.prompt_engineer.get_ir_sanity_check_prompt(prompt, context))
        ]
        while not is_make_sense and total_sanity_check_iteration <= 5:
            sanity_check_result = self.llm.chat(sanity_check_messages).strip().lower()
            if sanity_check_result.startswith("yes"):
                is_make_sense = True
                break
            else:
                context = ir_system.retrieve(sanity_check_result)
                sanity_check_messages[0]["content"] = self.prompt_engineer.get_ir_sanity_check_prompt(prompt, context)
            total_sanity_check_iteration += 1
        return context
