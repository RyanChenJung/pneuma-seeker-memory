import json

from processor.core.interaction_conductor.ic_prompt_engineer import ICPromptEngineer
from processor.core.interaction_conductor.ic_state import ICState
from processor.core.interaction_conductor.data_model import ToolType, IRSystemToolCallingType, MaterializerEngineToolCallingType, StateManipulationToolCallingType
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.llm_planner import LLMPlanner
from processor.core.interaction_conductor.data_model import ToolType
from processor.model.interface.model_factory import get_llm
from processor.model.llm_message import LLMMessage, Role


class LLMConductor:
    def __init__(self, llm_path: str, ir_system: LMInterface, materializer: LLMPlanner):
        """
        Initializes the LLM Conductor with a state, IR system, and materializer.
        """
        self.state = ICState()
        self.llm = get_llm(llm_path)()
        self.chat_history: list[LLMMessage] = []
        self.prompt_engineer = ICPromptEngineer()

        self.ir_system = ir_system
        self.materializer = materializer

    def process_input(self, user_input: str) -> str:
        """
        Processes the user input, possibly calling tools and adjusting the state.
        """
        model_output = self.llm.chat(
            self.chat_history + [DummyMessage(
                user_input, Role.USER,
            )]
        )
        self.chat_history = model_output

        # TODO: better handle tool calling (refer to best practices from HF for example)
        last_message = self.chat_history[-1]
        if last_message.invoke_tool:
            tool = last_message.tool
            if tool == Tool.IR_SYSTEM:
                context = self.retrieve_context(last_message.text)
                self.process_input(
                    f"Context from IR: {context}"
                )
            elif tool == Tool.MATERIALIZER_ENGINE:
                materialized_target_schemas = self.materialize_state()
                # TODO: what's next?

    def update_state(self, sqls: list[str] = None, target_schemas: list[str] = None) -> None:
        """
        Updates the current state.
        """
        self.state.set_state(sqls, target_schemas)
    
    def retrieve_context(self, prompt: str) -> str:
        """
        Retrieves context from the IR system.
        """
        # TODO: Handle provenance information!
        context = self.ir_system.retrieve_context(
            prompt
        )
        return context

    def check_state_convergence(self) -> bool:
        """
        Checks if the current state is ready to be materialized.
        """
        pass

    def materialize_state(self) -> str:
        """
        Sends the state to the Materializer Engine for execution.
        """
        current_state = self.state.get_state()
        self.materializer.materialize(
            current_state['sqls'], current_state['target_schemas'],
        )

class SystemPromptEngineer:
    def get_general_prompt():
        """
        Returns prompt for general chat.
        """

    def get_ir_prompt():
        """
        Returns prompt for the IR system.
        """
    
    def get_materializer_prompt():
        """
        Returns prompt for the materializer engine.
        """
