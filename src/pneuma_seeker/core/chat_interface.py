# src/pneuma_seeker/core/chat_interface.py
import os

from pneuma_seeker.core.persistence import init_db, load_state, save_state
from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.main import Conductor
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.provenance.graph import ProvenanceGraph
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
        logger = setup_logger(log_path=os.path.join(".", "log"))

        self.user_id = user_id
        self.chat_id = chat_id
        self.enable_persistence = enable_persistence

        if self.enable_persistence:
            init_db()
            info_need_state, retr_results, enumerated_table_ids, prov_graph = (
                load_state(self.user_id, self.chat_id, logger)
            )
            self.conductor = Conductor(
                llm_path,
                embed_model_path,
                logger,
                data_sources,
                Config(env_path=env_path),
                prov_graph,
                self.user_id,
                self.chat_id,
            )
            self.conductor.info_need_state = info_need_state
            self.conductor.retrieved_tables = retr_results
            self.conductor.enumerated_table_ids = enumerated_table_ids
        else:
            self.conductor = Conductor(
                llm_path,
                embed_model_path,
                logger,
                data_sources,
                Config(env_path=env_path),
                ProvenanceGraph(logger),
            )

    def process_user_input(
        self,
        chat_messages: list[LLMMessage],
        external_data_paths: list[str] | None = None,
    ):
        """
        Processes user input, as encapsulated in `chat_messages`,
        optionally leveraging external data (if specified).
        """
        external_data_paths = external_data_paths or []
        interaction_history: list[HumanConductorInteraction] = []
        for i in range(0, len(chat_messages) - 1, 2):
            if (
                chat_messages[i]["role"] == Role.USER.value
                and chat_messages[i + 1]["role"] == Role.ASSISTANT.value
            ):
                interaction_history.append(
                    HumanConductorInteraction(
                        chat_messages[i]["content"],
                        chat_messages[i + 1]["content"],
                    )
                )

        for conductor_response in self.conductor.process_input(
            chat_messages[-1]["content"],
            interaction_history,
            external_data_paths,
        ):
            yield conductor_response

        yield "DONE"

    def persist_state(self):
        """Callback to persist the current state of Provenance Graph."""
        try:
            node_count = len(self.conductor.prov_graph.nodes)
            self.conductor.logger.info(
                f"[Persist] Saving provenance graph with {node_count} nodes"
            )
            save_state(
                self.user_id,
                self.chat_id,
                self.conductor.info_need_state,
                self.conductor.retrieved_tables,
                self.conductor.enumerated_table_ids,
                self.conductor.prov_graph,
            )
            self.conductor.logger.info("[ChatInterface] State persisted successfully.")
        except Exception as e:
            self.conductor.logger.exception(
                f"[ChatInterface] Failed to persist state: {e}"
            )
