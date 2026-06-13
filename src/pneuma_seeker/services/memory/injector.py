"""``MemoryInjector`` — the single entry point the conductor calls (DECISIONS D19).

Ties Tier 3 (who is asking) to Tier 4 (that department's authored knowledge) and composes
one SYSTEM message of institutional context. v1 = inject-whole, no retrieval. Returns ``None``
when the persona is unknown, so an unmapped ``user_id`` behaves exactly like baseline.
"""

from pneuma_seeker.services.memory.t3_identity import UserIdentity
from pneuma_seeker.services.memory.t4_authored import AuthoredKnowledge


class MemoryInjector:
    def __init__(self) -> None:
        self._identity = UserIdentity()
        self._knowledge = AuthoredKnowledge()

    def get_injection(self, user_id: str, query: str) -> str | None:
        """Compose the institutional-context SYSTEM message for this asker, or ``None``.

        ``query`` is part of the interface for future retrieval; v1 injects the whole
        department block and does not branch on it.
        """
        identity = self._identity.lookup(user_id)
        if identity is None:
            return None
        department, role = identity
        entries = self._knowledge.get_dept_knowledge(department)
        return self._compose(department, role, entries)

    @staticmethod
    def _compose(department: str, role: str, entries: list[dict]) -> str:
        lines = [
            f"The asking user is in the {department} department (role: {role}).",
            f"Apply {department}'s conventions when interpreting ambiguous terms:",
        ]
        for e in entries:
            tables = ", ".join(e["target_tables"])
            lines.append(
                f'- "{e["term"]}" = {e["definition"]} '
                f"Target table(s): {tables}. Rule: {e['hidden_rule']}"
            )
        return "\n".join(lines)
