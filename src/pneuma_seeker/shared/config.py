# src/pneuma_seeker/shared/config.py
import os

from dotenv import load_dotenv


class Config:
    def __init__(self, env_path=".env") -> None:
        """Loads configuration from environment variables or a .env file."""
        load_dotenv(env_path)
        self.LLM_PATH = os.getenv("LLM_PATH", "gpt-4.1-mini")
        self.EMBED_MODEL_PATH = os.getenv("EMBED_MODEL_PATH", "text-embedding-3-small")
        self.EMBEDDING_MAX_TOKENS = int(os.getenv("EMBEDDING_MAX_TOKENS", "1536"))

        self.PERSIST_CHAT_SESSION = (
            os.getenv("PERSIST_CHAT_SESSION", "true").lower() == "true"
        )
        self.DATA_SOURCES = ["buysite"]
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

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
        self.SEMANTIC_JOIN_BATCH_SIZE = max(
            1, int(os.getenv("SEMANTIC_JOIN_BATCH_SIZE", "30"))
        )
        self.SEMANTIC_JOIN_DELIMITER = os.getenv("SEMANTIC_JOIN_DELIMITER", " [SEP] ")
        self.SEMANTIC_JOIN_ALPHA = float(os.getenv("SEMANTIC_JOIN_ALPHA", "0.5"))

        self.SEMANTIC_COL_GEN_ROW_PROCESSING_BATCH_SIZE = max(
            1, int(os.getenv("SEMANTIC_COL_GEN_ROW_PROCESSING_BATCH_SIZE", "60"))
        )
        self.SEMANTIC_COL_GEN_VALUE_GENERATION_BATCH_SIZE = max(
            1, int(os.getenv("SEMANTIC_COL_GEN_VALUE_GENERATION_BATCH_SIZE", "10"))
        )

        self.MATERIALIZER_HARD_ITERATION_LIMIT = 100
        self.ENABLE_WEB_SEARCH = self.__get_enable_web_search()
        self.ENABLE_WEB_CRAWL = os.getenv("ENABLE_WEB_CRAWL", "true").lower() == "true"
        self.WEB_CRAWL_MAX_CHARS = int(os.getenv("WEB_CRAWL_MAX_CHARS", "5000"))

        self.DB_BACKEND_PATH = os.getenv(
            "DB_BACKEND_PATH", os.path.join("..", "..", "data_src", "duckdb")
        )

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
