from logging import INFO
from os import path
from pneuma_seeker.core.conductor import persistence
from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.main import Conductor
from pneuma_seeker.model.llm_message import LLMMessage
from pneuma_seeker.utils.config import Config
from pneuma_seeker.utils.logger import setup_logger


class ChatInterface:
    def __init__(
        self,
        llm_path: str,
        embed_model_path: str,
        user_id: str,
        chat_id: str,
        data_sources: list[str],
        enable_persistence=True,
        env_path=".env",
    ):
        logger = setup_logger(
            name="processor_logger",
            log_path=path.join(".", "log"),
            level=INFO,
            max_bytes=10_000_000,
            backup_count=5,
        )
        self.config = Config(env_path=env_path)
        self.llm_conductor = Conductor(
            llm_path, embed_model_path, logger, data_sources, self.config
        )

        self.user_id = user_id
        self.chat_id = chat_id

        self.enable_persistence = enable_persistence
        if self.enable_persistence:
            persistence.init_db()

            # Restore previous state
            info_state, retr_results, enumerated_table_ids = persistence.load_state(
                user_id, chat_id
            )
            self.llm_conductor.info_need_state = info_state
            self.llm_conductor.current_retrieval_results = retr_results
            self.llm_conductor.enumerated_table_ids = enumerated_table_ids

    def process_user_input(
        self,
        chat_messages: list[LLMMessage],
        external_data_paths: list[str] = [],
    ):
        """
        Processes user input. If persistence is enabled, the `interactions` argument is ignored.
        If not enabled, then interactions must be passed.
        """
        conductor_final_response = ""
        human_input = chat_messages[-1]["content"]
        interaction_history: list[HumanConductorInteraction] = []
        for i in range(0, len(chat_messages) - 1, 2):
            chat_human_input = chat_messages[i]["content"]
            chat_conductor_response = chat_messages[i + 1]["content"]
            interaction_history.append(
                HumanConductorInteraction(
                    chat_human_input,
                    chat_conductor_response,
                )
            )

        for system_response in self.llm_conductor.process_input(
            human_input,
            self.user_id,
            interaction_history,
            external_data_paths,
        ):
            if not system_response.startswith("LOG"):
                conductor_final_response += system_response
            yield system_response

        yield "DONE"

        if self.enable_persistence:
            # Save current state of Conductor
            persistence.save_state(
                self.user_id,
                self.chat_id,
                self.llm_conductor.info_need_state,
                self.llm_conductor.current_retrieval_results,
                self.llm_conductor.enumerated_table_ids,
            )
