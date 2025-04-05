from dataclasses import dataclass


@dataclass
class LLMOption:
    max_new_tokens: int = 100
    do_sample: bool = False
    temperature: float = None
    top_p: float = None
    top_k: int = None
    penalty_alpha: float = None
