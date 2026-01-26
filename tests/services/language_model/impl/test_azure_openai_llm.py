import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

from pneuma_seeker.services.language_model.impl.azure_openai_llm import AzureOpenAILLM
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.option import LLMOption


class DummyAzureOpenAI:
    def __init__(self, **kwargs):
        # expose a `.chat.completions.create(...)` interface
        class Completions:
            @staticmethod
            def create(**create_kwargs):
                # streaming return: an iterable of events
                if create_kwargs.get("stream"):
                    # produce two events with content then a keep-alive
                    ev1 = types.SimpleNamespace(
                        choices=[
                            types.SimpleNamespace(
                                delta=types.SimpleNamespace(content="chunk1")
                            )
                        ]
                    )
                    ev2 = types.SimpleNamespace(
                        choices=[
                            types.SimpleNamespace(
                                delta=types.SimpleNamespace(content="chunk2")
                            )
                        ]
                    )
                    ev_keep = types.SimpleNamespace(choices=[])
                    return [ev_keep, ev1, ev2]

                # non-streaming return: object with choices[0].message.content
                return types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(content="full response")
                        )
                    ]
                )

        self.chat = types.SimpleNamespace(completions=Completions())


class AzureOpenAILLMTests(unittest.TestCase):
    def setUp(self) -> None:
        # Patch the AzureOpenAI symbol used in the module
        import pneuma_seeker.services.language_model.impl.azure_openai_llm as mod

        self._orig_Azure = getattr(mod, "AzureOpenAI", None)
        mod.AzureOpenAI = DummyAzureOpenAI

        cfg = Config()
        self.cfg = cfg
        self.logger = MagicMock()

    def tearDown(self) -> None:
        import pneuma_seeker.services.language_model.impl.azure_openai_llm as mod

        mod.AzureOpenAI = self._orig_Azure

    def test_chat_non_streaming_returns_full_response(self):
        llm = AzureOpenAILLM(self.cfg, self.logger)
        messages = [LLMMessage(role="user", content="hello")]
        out = list(llm.chat(messages))
        self.assertEqual(out, ["full response"])

    def test_chat_streaming_yields_chunks(self):
        llm = AzureOpenAILLM(self.cfg, self.logger)

        # provide an llm_option to enable streaming
        chunks = list(llm.chat([], LLMOption(stream=True, json_mode=False)))
        # Dummy returns two chunks
        self.assertEqual(chunks, ["chunk1", "chunk2"])

    def test_batch_chat_aggregates_and_respects_batch_size(self):
        llm = AzureOpenAILLM(self.cfg, self.logger)
        batch = [
            [LLMMessage(role="user", content="a")],
            [LLMMessage(role="user", content="b")],
        ]
        opt = LLMOption(
            batch_size=4,
            stream=False,
            json_mode=False,
            max_new_tokens=None,
            temperature=None,
        )
        responses, bs = llm.batch_chat(batch, opt)
        # Each response should be the dummy non-stream full response
        self.assertEqual(responses, ["full response", "full response"])
        self.assertEqual(bs, 4)

    def test_encode_raises_not_implemented(self):
        llm = AzureOpenAILLM(self.cfg, self.logger)
        with self.assertRaises(NotImplementedError):
            llm.encode(["a"])


if __name__ == "__main__":
    unittest.main()
