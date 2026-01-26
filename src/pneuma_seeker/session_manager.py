# src/pneuma_seeker/session_manager.py
from logging import Logger

from pneuma_seeker.chat_session import ChatSession
from pneuma_seeker.shared.config import Config


class SessionManager:
    """Manages chat sessions for users."""

    def __init__(self, config: Config, logger: Logger):
        """Initializes the SessionManager with configuration and logger."""
        self.config = config
        self.logger = logger
        self.chat_sessions: dict[tuple[str, str], ChatSession] = {}

    def get_chat_session(self, user_id: str, chat_id: str) -> ChatSession:
        """Retrieves or creates a ChatSession for the given user and chat IDs."""
        key = (user_id, chat_id)
        if key not in self.chat_sessions:
            self.chat_sessions[key] = ChatSession(
                user_id=user_id,
                chat_id=chat_id,
                config=self.config,
                logger=self.logger,
            )
        return self.chat_sessions[key]
