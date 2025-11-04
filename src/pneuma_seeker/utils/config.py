# src/pneuma_seeker/utils/config.py
import os

from dotenv import load_dotenv


class Config:
    def __init__(self, env_path=".env") -> None:
        """Loads configuration from environment variables or a .env file."""
        load_dotenv(env_path)
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")
        self.USE_AZURE = self.__get_use_azure()

        self.OPENWEBUI_BASE_URL = os.getenv(
            "OPENWEBUI_BASE_URL", "http://localhost:8080/"
        )
        self.OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "")

        self.CONDUCTOR_ITERATION_LIMIT = int(
            os.getenv("CONDUCTOR_ITERATION_LIMIT", "5")
        )

        self.SEMANTIC_JOIN_TOP_K = 1
        self.MATERIALIZER_HARD_ITERATION_LIMIT = 100
        self.ENABLE_WEB_SEARCH = self.__get_enable_web_search()

        self.WEB_CRAWL_MAX_CHARS = int(os.getenv("WEB_CRAWL_MAX_CHARS", "5000"))

    def __get_use_azure(self):
        """Determines whether to use Azure OpenAI based on environment variable."""
        use_azure = os.getenv("USE_AZURE", "false").lower()
        if use_azure == "true":
            return True
        return False

    def __get_enable_web_search(self):
        """Determines whether to enable web search based on environment variable."""
        enable_web_search = os.getenv("ENABLE_WEB_SEARCH", "false").lower()
        if enable_web_search == "true":
            return True
        return False
