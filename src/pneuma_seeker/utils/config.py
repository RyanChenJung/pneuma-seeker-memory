import os

from dotenv import load_dotenv


class Config:
    def __init__(self, env_path=".env") -> None:
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

    def __get_use_azure(self):
        use_azure = os.getenv("USE_AZURE", "false").lower()
        if use_azure == "true":
            return True
        return False
