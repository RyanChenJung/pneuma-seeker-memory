from logging import INFO
from os import path

from pneuma_seeker.core.conductor.llm_conductor import LLMConductor
from pneuma_seeker.utils.logger import setup_logger


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

    def process_user_input(self, user_input: str):
        """
        Accepts user prompt and forwards it to the LLM conductor for processing.
        """
        for system_response in self.llm_conductor.process_input(
            user_input, self.user_id, self.subsequent_chat
        ):
            yield system_response
