# backend/services/core-service/src/core_service/chat_session.py
from logging import Logger

from pneuma_seeker.provenance.graph import ProvenanceGraph
from pneuma_seeker.services.core.api.db import DBAPI
from pneuma_seeker.services.core.api.language_model import LanguageModelAPI
from pneuma_seeker.services.core.conductor.main import Conductor
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.core.conductor import UserConductorInteraction
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.role import Role


class ChatSession:
    """Represents a chat session for a user."""

    def __init__(
        self,
        user_id: str,
        chat_id: str,
        config: Config,
        logger: Logger,
        db_api: DBAPI,
        language_model_api: LanguageModelAPI,
    ):
        """Initializes the ChatSession with user and chat IDs, configuration, logger, and APIs."""
        self.user_id = user_id
        self.chat_id = chat_id
        self.config = config
        self.logger = logger
        self.db_api = db_api
        self.language_model_api = language_model_api

        self.conductor = Conductor(
            self.user_id,
            self.chat_id,
            self.config,
            self.logger,
            ProvenanceGraph(self.logger),
            self.db_api,
            self.language_model_api,
        )

        if self.config.PERSIST_CHAT_SESSION:
            info_need_state, retrieved_tables, enumerated_table_ids, prov_graph = (
                self.db_api.load_state(
                    self.user_id,
                    self.chat_id,
                )
            )

            self.conductor.info_need_state = info_need_state
            self.conductor.retrieved_tables = retrieved_tables
            self.conductor.enumerated_table_ids = enumerated_table_ids
            self.conductor.prov_graph = prov_graph

    def chat(
        self,
        messages: list[LLMMessage],
        external_data_paths: list[str] | None = None,
    ):
        """Processes chat messages and yields responses from the Conductor."""
        external_data_paths = external_data_paths or []
        interaction_history: list[UserConductorInteraction] = []
        for i in range(0, len(messages) - 1, 2):
            if (
                messages[i]["role"] == Role.USER.value
                and messages[i + 1]["role"] == Role.ASSISTANT.value
            ):
                interaction_history.append(
                    UserConductorInteraction(
                        messages[i]["content"],
                        messages[i + 1]["content"],
                    )
                )

        for conductor_response in self.conductor.chat(
            messages[-1]["content"],
            interaction_history,
            external_data_paths,
        ):
            yield conductor_response

        yield "DONE"

    def persist_session(self):
        """Callback to persist the current state of Provenance Graph."""
        try:
            node_count = len(self.conductor.prov_graph.nodes)
            self.conductor.logger.info(
                f"[Persist] Saving provenance graph with {node_count} nodes"
            )
            self.db_api.save_state(
                self.user_id,
                self.chat_id,
                self.conductor.info_need_state,
                self.conductor.retrieved_tables,
                self.conductor.enumerated_table_ids,
                self.conductor.prov_graph,
            )
            self.conductor.logger.info("[ChatSession] State persisted successfully.")
        except Exception as e:
            self.conductor.logger.exception(
                f"[ChatSession] Failed to persist state: {e}"
            )
