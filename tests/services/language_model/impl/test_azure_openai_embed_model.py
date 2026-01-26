import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

from pneuma_seeker.services.language_model.impl.azure_openai_embed_model import (
    AzureOpenAIEmbedModel,
)
from pneuma_seeker.shared.config import Config


class DummyAzureOpenAIEmbeddings:
    def __init__(self, **kwargs):
        class Embeddings:
            @staticmethod
            def create(**create_kwargs):
                inputs = create_kwargs.get("input", [])
                data = []
                for inp in inputs:
                    # return a simple 3-dim embedding per input
                    data.append(types.SimpleNamespace(embedding=[1.0, 2.0, 3.0]))
                return types.SimpleNamespace(data=data)

        self.embeddings = Embeddings()


class AzureEmbedTests(unittest.TestCase):
    def setUp(self) -> None:
        import pneuma_seeker.services.language_model.impl.azure_openai_embed_model as mod

        self._orig = getattr(mod, "AzureOpenAI", None)
        mod.AzureOpenAI = DummyAzureOpenAIEmbeddings
        self.cfg = Config()
        self.logger = MagicMock()

    def tearDown(self) -> None:
        import pneuma_seeker.services.language_model.impl.azure_openai_embed_model as mod

        mod.AzureOpenAI = self._orig

    def test_encode_returns_numpy_array_and_dtype(self):
        model = AzureOpenAIEmbedModel(self.cfg, self.logger)
        texts = ["a", "b"]
        arr = model.encode(texts)
        import numpy as np

        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.shape, (2, 3))
        self.assertEqual(arr.dtype, np.float32)

    def test_encode_empty_texts_returns_empty_array(self):
        model = AzureOpenAIEmbedModel(self.cfg, self.logger)
        arr = model.encode([])
        import numpy as np

        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.shape, (0, 0))


if __name__ == "__main__":
    unittest.main()
