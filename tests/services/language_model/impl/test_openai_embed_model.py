import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

from pneuma_seeker.services.language_model.impl.openai_embed_model import (
    OpenAIEmbedModel,
)
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.option import EmbeddingModelOption


class DummyOpenAIEmbeddings:
    def __init__(self, **kwargs):
        class Embeddings:
            @staticmethod
            def create(**create_kwargs):
                inputs = create_kwargs.get("input", [])
                data = []
                for inp in inputs:
                    data.append(types.SimpleNamespace(embedding=[0.5, 0.25]))
                return types.SimpleNamespace(data=data)

        self.embeddings = Embeddings()


class OpenAIEmbedTests(unittest.TestCase):
    def setUp(self) -> None:
        import pneuma_seeker.services.language_model.impl.openai_embed_model as mod

        self._orig = getattr(mod, "OpenAI", None)
        mod.OpenAI = DummyOpenAIEmbeddings
        self.cfg = Config()
        self.logger = MagicMock()

    def tearDown(self) -> None:
        import pneuma_seeker.services.language_model.impl.openai_embed_model as mod

        mod.OpenAI = self._orig

    def test_encode_returns_expected_shape_and_dtype(self):
        model = OpenAIEmbedModel(self.cfg, self.logger)
        texts = ["one", "two", "three"]
        arr = model.encode(texts)
        import numpy as np

        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.shape, (3, 2))
        self.assertEqual(arr.dtype, np.float32)

    def test_encode_handles_batching(self):
        model = OpenAIEmbedModel(self.cfg, self.logger)
        texts = ["a", "b", "c"]
        opt = EmbeddingModelOption(batch_size=1)
        arr = model.encode(texts, embed_model_option=opt)
        import numpy as np

        self.assertEqual(arr.shape, (3, 2))


if __name__ == "__main__":
    unittest.main()
