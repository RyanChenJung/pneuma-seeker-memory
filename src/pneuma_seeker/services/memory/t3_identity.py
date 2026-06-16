"""Tier 3 (provisioned identity) — map an opaque ``user_id`` to ``(department, role)``.

This is the *only* place that interprets Pneuma's ``user_id`` as a persona (DECISIONS D19):
``user_id`` stays an opaque namespace key for Pneuma; the profile lookup lives entirely here.
v1 is a static provisioned map loaded from JSON; multi-user and the *learned* half of Tier 3
are deferred (see BACKLOG).

Auth note (DECISIONS D27 → refined by **D28**): the post-sync design splits the two axes by
source of truth. **Department** is the user's *group* (`UserDB`: `user_id → group.name`), the
single source of truth — so it is **not** stored here anymore. **Role** stays in a thin
Ryan-owned map (the v1 ``u_*`` placeholder shrinks from ``(dept, role)`` to role-only). To keep
this package unit-testable and free of a hard ``UserDB`` import, department is fetched through an
injected **dept-resolver** (``Callable[[user_id], department | None]``) wired at the composition
root; only that resolver is Postgres-coupled. (The resolver + role_map wiring is implemented in
the B-migration TASKS build — see D28-6 — not in this skeleton yet.)
"""

from json import loads
from pathlib import Path

_MAP_PATH = Path(__file__).parent / "_config" / "identity_map.json"


class UserIdentity:
    def __init__(self, map_path: Path = _MAP_PATH) -> None:
        self._map: dict[str, dict[str, str]] = loads(map_path.read_text())

    def lookup(self, user_id: str) -> tuple[str, str] | None:
        """Return ``(department, role)`` for a known persona, else ``None``.

        ``None`` is the graceful path: an unmapped ``user_id`` gets no injection, so the
        request behaves exactly like baseline Pneuma.
        """
        entry = self._map.get(user_id)
        if entry is None:
            return None
        return entry["department"], entry["role"]
