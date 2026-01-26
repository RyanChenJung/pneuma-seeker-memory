import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

from pneuma_seeker.services.language_model.impl.mock_llm import MockLLM
import numpy as np


class MockLLMTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = MagicMock()
        self.logger = MagicMock()

    def test_default_chat_yields_noop(self):
        m = MockLLM(self.config, self.logger)
        out = list(m.chat([]))
        self.assertTrue(out)
        self.assertIn("noop", out[0])

    def test_queued_responses(self):
        m = MockLLM(self.config, self.logger, responses=['{"a":1}', '{"b":2}'])
        first = list(m.chat([]))
        second = list(m.chat([]))
        self.assertEqual(first, ['{"a":1}'])
        self.assertEqual(second, ['{"b":2}'])

    def test_batch_chat(self):
        m = MockLLM(self.config, self.logger)
        res, bs = m.batch_chat([])
        self.assertEqual(res, [])
        self.assertEqual(bs, -1)

    def test_encode_returns_ndarray(self):
        m = MockLLM(self.config, self.logger)
        arr = m.encode(['a'])
        self.assertIsInstance(arr, np.ndarray)


if __name__ == "__main__":
    unittest.main()

