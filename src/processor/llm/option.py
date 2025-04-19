from dataclasses import dataclass


@dataclass
class LLMOption:
    seed: int = None
    max_new_tokens: int = 100
    do_sample: bool = False
    temperature: float = None
    top_p: float = None
    top_k: int = None
    penalty_alpha: float = None
