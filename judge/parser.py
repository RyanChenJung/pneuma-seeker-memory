"""
parser.py — test_cases.json loader and validator.

Loads Juan's test_cases.json and returns a list of validated TestCase objects
that the harness can iterate over. Fails loudly on schema violations so bad
test cases never silently produce wrong benchmark results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

# ── canonical persona keys (from scenario spec §E) ──────────────────────────
VALID_PERSONAS = {
    "u_adm_analyst",
    "u_adm_director",
    "u_fin_analyst",
    "u_fin_director",
}

REQUIRED_CASE_FIELDS = {"case_id", "persona", "turns", "ground_truth"}
REQUIRED_GT_FIELDS   = {"target_tables", "rule_applied"}
VALID_TURN_ROLES     = {"user", "assistant"}


# ── data classes ─────────────────────────────────────────────────────────────

@dataclass
class Turn:
    role: str
    content: str


@dataclass
class GroundTruth:
    target_tables: List[str]
    rule_applied: str


@dataclass
class TestCase:
    case_id: str
    persona: str
    turns: List[Turn]
    ground_truth: GroundTruth
    description: str = ""

    def department(self) -> str:
        """Infer department from persona key."""
        if "adm" in self.persona:
            return "Admissions"
        if "fin" in self.persona:
            return "Finance"
        return "Unknown"

    def is_multi_turn(self) -> bool:
        return len(self.turns) > 1

    def user_turns_only(self) -> List[Turn]:
        """Returns only the user-side turns (for building messages[])."""
        return [t for t in self.turns if t.role == "user"]

    def as_messages(self) -> List[Dict[str, str]]:
        """Returns the full turn list as the messages[] array for /chat."""
        return [{"role": t.role, "content": t.content} for t in self.turns]


# ── validation helpers ───────────────────────────────────────────────────────
# All required fields exist (case_id, persona, turns, ground_truth)
# Persona is one of the four valid keys — rejects typos like u_adm_Analyst
# Turns list is non-empty and starts with a user message
# No duplicate case_ids
# target_tables is a non-empty list

def _validate_turn(raw: Any, case_id: str, idx: int) -> Turn:
    if not isinstance(raw, dict):
        raise ValueError(f"[{case_id}] turn[{idx}] must be a dict, got {type(raw)}")
    # Every turn contains role and content
    for f in ("role", "content"):
        if f not in raw:
            raise ValueError(f"[{case_id}] turn[{idx}] missing field '{f}'")
    # Turn role is valid
    if raw["role"] not in VALID_TURN_ROLES:
        raise ValueError(
            f"[{case_id}] turn[{idx}] role '{raw['role']}' not in {VALID_TURN_ROLES}"
        )
    return Turn(role=raw["role"], content=raw["content"])


def _validate_ground_truth(raw: Any, case_id: str) -> GroundTruth:
    if not isinstance(raw, dict):
        raise ValueError(f"[{case_id}] ground_truth must be a dict")
    
    #All required fields exist (case_id, persona, turns, ground_truth)
    missing = REQUIRED_GT_FIELDS - raw.keys()
    if missing:
        raise ValueError(f"[{case_id}] ground_truth missing fields: {missing}")
    if not isinstance(raw["target_tables"], list) or not raw["target_tables"]:
        raise ValueError(f"[{case_id}] ground_truth.target_tables must be a non-empty list")
    return GroundTruth(
        target_tables=raw["target_tables"],
        rule_applied=raw["rule_applied"],
    )


def _validate_case(raw: Any, idx: int) -> TestCase:
    # Every turn is a dictionary
    if not isinstance(raw, dict):
        raise ValueError(f"Case[{idx}] must be a dict, got {type(raw)}")

    missing = REQUIRED_CASE_FIELDS - raw.keys()
    if missing:
        raise ValueError(f"Case[{idx}] missing required fields: {missing}")

    case_id = raw["case_id"]
    
    # case_id is a non-empty string
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError(f"Case[{idx}] case_id must be a non-empty string")
    # Persona is one of the valid personas
    if raw["persona"] not in VALID_PERSONAS:
        raise ValueError(
            f"[{case_id}] unknown persona '{raw['persona']}'. "
            f"Valid: {sorted(VALID_PERSONAS)}"
        )
    # turns is a non-empty list
    if not isinstance(raw["turns"], list) or not raw["turns"]:
        raise ValueError(f"[{case_id}] turns must be a non-empty list")

    turns = [_validate_turn(t, case_id, i) for i, t in enumerate(raw["turns"])]

    # turns must start with a user message
    if turns[0].role != "user":
        raise ValueError(f"[{case_id}] first turn must have role 'user'")

    ground_truth = _validate_ground_truth(raw["ground_truth"], case_id)

    return TestCase(
        case_id=case_id,
        persona=raw["persona"],
        turns=turns,
        ground_truth=ground_truth,
        description=raw.get("description", ""),
    )


# ── public API ───────────────────────────────────────────────────────────────

def load_test_cases(path: str | Path = "test_cases.json") -> List[TestCase]:
    """
    Load and validate test_cases.json.

    Raises:
        FileNotFoundError: if path doesn't exist
        json.JSONDecodeError: if the file isn't valid JSON
        ValueError: if any case fails schema validation
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"test_cases.json not found at: {path.resolve()}")

    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("test_cases.json must be a JSON array at the top level")

    cases = [_validate_case(item, i) for i, item in enumerate(raw)]

    # check for duplicate case_ids
    seen: set[str] = set()
    for c in cases:
        if c.case_id in seen:
            raise ValueError(f"Duplicate case_id: '{c.case_id}'")
        seen.add(c.case_id)

    return cases


def summarise(cases: List[TestCase]) -> str:
    """Return a short human-readable summary of the loaded test cases."""
    lines = [f"Loaded {len(cases)} test case(s):"]
    for c in cases:
        multi = " [multi-turn]" if c.is_multi_turn() else ""
        lines.append(
            f"  {c.case_id:8s}  persona={c.persona:20s}  "
            f"tables={c.ground_truth.target_tables}{multi}"
        )
    return "\n".join(lines)


# ── CLI smoke test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "test_cases.json"
    try:
        cases = load_test_cases(path)
        print(summarise(cases))
        print("\n✓ All cases valid.")
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"✗ Validation failed: {e}", file=sys.stderr)
        sys.exit(1)
