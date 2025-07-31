from logging import INFO
from os import path
from typing import TypedDict

from processor.core.interaction_conductor.ic_state import InformationNeedState
from processor.core.interaction_conductor.llm_conductor import LLMConductor
from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from processor.utils.logger import setup_logger


class ChatInterfaceOutputFormat(TypedDict):
    system_response: str
    state: InformationNeedState
    current_retrieval_results: dict[RetrieverType, list[AbstractDocument]]


class ChatInterface:
    def __init__(
        self,
        llm_path: str,
        embed_model_path: str,
        user_id: str,
        data_sources: list[str],
    ):
        """
        Initializes the Chat Interface with access to the LLM Conductor.
        """
        logger = setup_logger(
            name="processor_logger",
            log_path=path.join(".", "log"),
            level=INFO,
            max_bytes=10_000_000,
            backup_count=5,
        )
        self.llm_conductor = LLMConductor(
            llm_path, embed_model_path, logger, data_sources
        )
        self.user_id = user_id
        self.subsequent_chat = False

    def process_user_input(self, user_input: str) -> ChatInterfaceOutputFormat:
        """
        Accepts user prompt and forwards it to the LLM conductor for processing.
        """
        system_response = self.llm_conductor.process_input(user_input, self.user_id, self.subsequent_chat)
        state = self.llm_conductor.info_need_state
        curr_retrieval_results = self.llm_conductor.current_retrieval_results
        self.subsequent_chat = True
        return {
            "system_response": system_response,
            "state": state,
            "current_retrieval_results": curr_retrieval_results,
        }
