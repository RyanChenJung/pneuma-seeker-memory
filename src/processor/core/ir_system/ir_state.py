from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from processor.model.llm_message import LLMMessage


class IRState:
    def __init__(self):
        self.current_query = (
            ""  # May be refined along the way if the caller provides any feedback
        )
        self.retrieved_results: list[AbstractDocument] = []
        self.llm_messages: list[LLMMessage] = []
        self.relevant_retrievers: list[RetrieverType] = []