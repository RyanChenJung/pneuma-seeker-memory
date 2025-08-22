from pneuma_seeker.core.ir_system.data_model import RetrieverType
from pneuma_seeker.model.llm_message import LLMMessage


class IRState:
    def __init__(self):
        self.current_queries: dict[RetrieverType, str] = dict()
        self.llm_messages: list[LLMMessage] = []
