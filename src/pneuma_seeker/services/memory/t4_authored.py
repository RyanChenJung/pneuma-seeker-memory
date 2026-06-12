"""Tier 4 (authored knowledge) loader — the authoritative tribal-knowledge KB.

v1 reads a static JSON in the exact format teammate "Juan" delivers
(``scenario-spec-v1.md`` §6.2); swapping in the real file needs no code change. Retrieval /
embedding is deferred — the store is small, so callers inject the whole department block
(DECISIONS D18).
"""

from json import loads
from pathlib import Path

_KB_PATH = Path(__file__).parent / "_config" / "tribal_knowledge.sample.json"


class AuthoredKnowledge:
    def __init__(self, kb_path: Path = _KB_PATH) -> None:
        self._entries: list[dict] = loads(kb_path.read_text())

    def get_dept_knowledge(self, department: str) -> list[dict]:
        """All authored entries for a department (case-insensitive match)."""
        return [e for e in self._entries if e["department"].lower() == department.lower()]
