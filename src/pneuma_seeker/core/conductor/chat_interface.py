from logging import INFO
from os import path
from pneuma_seeker.core.conductor import persistence
from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.main import Conductor
from pneuma_seeker.utils.logger import setup_logger


class ChatInterface:
    def __init__(
        self,
        llm_path: str,
        embed_model_path: str,
        user_id: str,
        chat_id: str,
        data_sources: list[str],
    ):
        logger = setup_logger(
            name="processor_logger",
            log_path=path.join(".", "log"),
            level=INFO,
            max_bytes=10_000_000,
            backup_count=5,
        )
        self.llm_conductor = Conductor(llm_path, embed_model_path, logger, data_sources)
        self.user_id = user_id
        self.chat_id = chat_id
        persistence.init_db()

        # Restore previous state
        info_state, retr_results = persistence.load_state(user_id, chat_id)
        self.llm_conductor.info_need_state = info_state
        self.llm_conductor.current_retrieval_results = retr_results

    def process_user_input(self, user_input: str):
        conductor_final_response = ""
        interactions = persistence.load_interactions(self.user_id, self.chat_id)

        for system_response in self.llm_conductor.process_input(
            user_input,
            self.user_id,
            interactions,
        ):
            if not system_response.startswith("LOG"):
                conductor_final_response = system_response
            yield system_response

        # Save new interaction
        persistence.save_interaction(
            self.user_id,
            self.chat_id,
            HumanConductorInteraction(user_input, conductor_final_response),
        )

        # Save current state of Conductor
        persistence.save_state(
            self.user_id,
            self.chat_id,
            self.llm_conductor.info_need_state,
            self.llm_conductor.current_retrieval_results,
        )
