from dataclasses import dataclass
from processor.interaction_conductor.state import ICState
from processor.ir_system.lm_interface import LMInterface
from processor.materializer_engine.materializer_engine import MaterializerEngine
from enum import Enum


class Role(Enum):
    USER = 'user'
    ASSISTANT = 'assistant'

class Tool(Enum):
    IR_SYSTEM = 'IR System'
    MATERIALIZER_ENGINE = 'Materializer Engine'

@dataclass
class DummyMessage:
    """
    Class for representing LLM messages
    """
    text: str
    role: Role
    invoke_tool: bool
    tool: Tool

class DummyLLM:
    def chat(self, conversation: list[DummyMessage]):
        """
        Returns the conversation appended with an output message.
        """
        output = ""
        return conversation + [DummyMessage(
            text=output,
            role=Role.ASSISTANT,
        )]

class LLMConductor:
    def __init__(self, ir_system: LMInterface, materializer: MaterializerEngine):
        """
        Initializes the LLM Conductor with a state, IR system, and materializer.
        """
        self.state = ICState()
        self.llm = DummyLLM()
        self.chat_history = list[DummyMessage]
        self.sys_prompt_engineer = SystemPromptEngineer()

        # Available tools
        self.ir_system = ir_system
        self.materializer = materializer

    def process_input(self, user_input: str) -> str:
        """
        Processes the user input, possibly calling tools and adjusting the state
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
