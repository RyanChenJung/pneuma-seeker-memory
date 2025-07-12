from dataclasses import dataclass


@dataclass
class LLMOption:
    seed: int = None
    max_new_tokens: int = None
    do_sample: bool = False
    temperature: float = None
    top_p: float = None
    top_k: int = None
    penalty_alpha: float = None
    json_mode: bool = False

@dataclass
class EmbeddingModelOption:
    batch_size: int = 32
