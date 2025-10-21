# tests/pneuma_seeker/utils/test_config.py
import unittest
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)
from pneuma_seeker.utils.config import Config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        # Temporary environment variables
        os.environ["OPENAI_API_KEY"] = "test_openai"
        os.environ["USE_AZURE"] = "true"
        os.environ["ENABLE_WEB_SEARCH"] = "false"

    def tearDown(self):
        for var in ["OPENAI_API_KEY", "USE_AZURE", "ENABLE_WEB_SEARCH"]:
            if var in os.environ:
                del os.environ[var]

    def test_config_loads_env(self):
        cfg = Config(env_path=".env")
        self.assertEqual(cfg.OPENAI_API_KEY, "test_openai")
        self.assertTrue(cfg.USE_AZURE)
        self.assertFalse(cfg.ENABLE_WEB_SEARCH)

    def test_default_values(self):
        for var in [
            "AZURE_API_VERSION",
            "OPENWEBUI_BASE_URL",
            "CONDUCTOR_ITERATION_LIMIT",
        ]:
            cfg = Config(env_path=".env")
            self.assertIsNotNone(getattr(cfg, var))


if __name__ == "__main__":
    unittest.main()
