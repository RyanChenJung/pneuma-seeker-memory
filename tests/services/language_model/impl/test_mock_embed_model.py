import os
import sys
import unittest

sys.path.insert(
	0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

from pneuma_seeker.services.language_model.impl.mock_embed_model import MockEmbedModel
import numpy as np


class MockEmbedModelTests(unittest.TestCase):
	def test_chat_yields_empty_string(self):
		m = MockEmbedModel()
		out = list(m.chat([]))
		self.assertEqual(out, [""])

	def test_encode_returns_ndarray(self):
		m = MockEmbedModel()
		arr = m.encode(['a'])
		self.assertIsInstance(arr, np.ndarray)


if __name__ == "__main__":
	unittest.main()

