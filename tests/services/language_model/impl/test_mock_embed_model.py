import os
import sys
import unittest
from unittest.mock import MagicMock

from pneuma_seeker.shared.config import Config

sys.path.insert(
	0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

from pneuma_seeker.services.language_model.impl.mock_embed_model import MockEmbedModel
import numpy as np


class MockEmbedModelTests(unittest.TestCase):
	def setUp(self) -> None:
		self.logger = MagicMock()
		self.config = Config()
	
	def test_chat_yields_empty_string(self):
		m = MockEmbedModel(self.config, self.logger)
		out = list(m.chat([]))
		self.assertEqual(out, [""])

	def test_encode_returns_ndarray(self):
		m = MockEmbedModel(self.config, self.logger)
		arr = m.encode(['a'])
		self.assertIsInstance(arr, np.ndarray)


if __name__ == "__main__":
	unittest.main()

