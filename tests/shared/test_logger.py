# tests/pneuma_seeker/shared/test_logger.py
import sys
import unittest
import logging
import tempfile
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)
from pneuma_seeker.shared.logger import setup_logger, formatted_log


class LoggerTests(unittest.TestCase):
    def test_setup_logger_stdout(self):
        logger = setup_logger(name="test_logger", log_path=None, level=logging.INFO)
        self.assertIsInstance(logger, logging.Logger)

    def test_setup_logger_file(self):
        temp_dir = tempfile.TemporaryDirectory()
        logger = setup_logger(name="file_logger", log_path=temp_dir.name)
        self.assertIsInstance(logger, logging.Logger)
        temp_dir.cleanup()

    def test_formatted_log(self):
        import io

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        test_logger = logging.getLogger("formatted_log_test")
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        formatted_log(test_logger, "COMPONENT", "Hello")
        handler.flush()
        log_contents = stream.getvalue()
        self.assertIn("[COMPONENT] Hello", log_contents)


if __name__ == "__main__":
    unittest.main()
