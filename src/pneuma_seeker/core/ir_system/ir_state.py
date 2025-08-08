from pneuma_seeker.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from pneuma_seeker.model.llm_message import LLMMessage


class IRState:
    def __init__(self):
        self.current_queries: dict[RetrieverType, str] = dict()
        self.llm_messages: list[LLMMessage] = []
