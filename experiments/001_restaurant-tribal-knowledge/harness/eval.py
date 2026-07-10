"""
eval.py — Rules 1/3/5 tribal knowledge benchmark scorer

Adapted from Ryan's eval.py (same scoring logic, unchanged) — only the
file paths and group labels are adjusted to match our harness structure.

Usage:
    python eval.py round1_baseline
    python eval.py round2_semantic

Expects:
    harness/reference_results/questions.json   (ground truth, fixed)
    harness/<round>/results/answers.json        (model's answers for that round)

Produces:
    harness/<round>/results/eval_report.json
    printed summary to stdout
"""

import json
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).parent
QUESTIONS_FILE = HARNESS_DIR / "reference_results" / "questions.json"

TOLERANCE_DEFAULT = 0.02  # 2% relative tolerance for numbers unless overridden

GROUP_LABELS = {
    "A": "Schema baseline (no tribal knowledge)",
    "B": "Visitors definition (Rule 1)",
    "C": "Fiscal year convention (Rule 3)",
    "D": "Booking channel scope (Rule 5)",
    "E": "Compound business rules",
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def numbers_close(got, expected, tolerance):
    if expected == 0:
        return abs(got) <= tolerance
    return abs(got - expected) / abs(expected) <= tolerance


def normalize(value):
    """Coerce strings that look like numbers to float."""
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value.strip().lower()
    if isinstance(value, int):
        return float(value)
    return value


def score_single_number(got, expected, tolerance):
    got = normalize(got)
    expected = float(expected)
    if not isinstance(got, (int, float)):
        return False, f"expected number, got {repr(got)}"
    tol = tolerance if tolerance is not None else TOLERANCE_DEFAULT
    ok = numbers_close(float(got), expected, tol)
    return ok, f"got {got}, expected {expected} (±{tol*100:.1f}%)"


def score_single_value(got, expected):
    got_n = normalize(got)
    exp_n = normalize(str(expected))
    ok = got_n == exp_n
    return ok, f"got {repr(got)}, expected {repr(expected)}"


def score_ordered_list(got, expected, tolerance):
    if not isinstance(got, list):
        return False, f"expected list, got {type(got).__name__}"
    if len(got) != len(expected):
        return False, f"length mismatch: got {len(got)}, expected {len(expected)}"

    mismatches = []
    for i, (g_row, e_row) in enumerate(zip(got, expected)):
        if not isinstance(g_row, list):
            g_row = [g_row]
        if not isinstance(e_row, list):
            e_row = [e_row]
        if len(g_row) != len(e_row):
            mismatches.append(f"row {i}: length mismatch")
            continue
        for j, (gv, ev) in enumerate(zip(g_row, e_row)):
            gv_n = normalize(gv)
            ev_n = normalize(ev)
            if isinstance(ev_n, float):
                tol = tolerance if tolerance is not None else TOLERANCE_DEFAULT
                if not isinstance(gv_n, (int, float)):
                    mismatches.append(f"row {i} col {j}: expected number, got {repr(gv)}")
                elif not numbers_close(float(gv_n), ev_n, tol):
                    mismatches.append(f"row {i} col {j}: got {gv_n}, expected {ev_n}")
            else:
                if gv_n != ev_n:
                    mismatches.append(f"row {i} col {j}: got {repr(gv)}, expected {repr(ev)}")

    if mismatches:
        return False, "; ".join(mismatches[:3])
    return True, "ok"


def score_answer(q, got_answer):
    atype = q.get("answer_type", "single_number")
    tol = q.get("tolerance", None)

    if atype == "single_number":
        return score_single_number(got_answer, q["expected"], tol)
    elif atype == "single_value":
        return score_single_value(got_answer, q["expected"])
    elif atype == "ordered_list":
        return score_ordered_list(got_answer, q["expected"], tol)
    else:
        return False, f"unknown answer_type: {atype}"


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("round1_baseline", "round2_semantic"):
        print("Usage: python eval.py <round1_baseline|round2_semantic>")
        sys.exit(1)

    round_name = sys.argv[1]
    answers_file = HARNESS_DIR / round_name / "results" / "answers.json"

    questions = load_json(QUESTIONS_FILE)
    q_index = {q["id"]: q for q in questions}

    if not answers_file.exists():
        print(f"ERROR: answers file not found at {answers_file}")
        print(f"Run the model session for {round_name} first, save its output there, then re-run eval.py")
        sys.exit(1)

    answers = load_json(answers_file)
    a_index = {a["id"]: a for a in answers}

    results = []
    for q in questions:
        qid = q["id"]
        if qid not in a_index:
            results.append({"id": qid, "group": q["group"], "correct": False,
                            "detail": "MISSING — not answered", "tribal_knowledge": q.get("tribal_knowledge")})
            continue

        got = a_index[qid].get("answer")
        ok, detail = score_answer(q, got)
        results.append({
            "id": qid,
            "group": q["group"],
            "correct": ok,
            "detail": detail,
            "tribal_knowledge": q.get("tribal_knowledge"),
            "sql": a_index[qid].get("sql", ""),
        })

    # ── Summary ──────────────────────────────────────────────────────────────
    groups = {g: [] for g in GROUP_LABELS}
    for r in results:
        groups[r["group"]].append(r)

    tribal_buckets = {}
    for r in results:
        tk = r.get("tribal_knowledge") or "none"
        tribal_buckets.setdefault(tk, []).append(r)

    total = len(results)
    correct = sum(1 for r in results if r["correct"])

    print("=" * 60)
    print(f"  {round_name.upper()} ACCURACY REPORT")
    print("=" * 60)
    print()
    print(f"  Overall:  {correct}/{total}  ({100*correct/total:.1f}%)")
    print()

    for g, label in GROUP_LABELS.items():
        rs = groups[g]
        if not rs:
            continue
        c = sum(1 for r in rs if r["correct"])
        print(f"  Group {g} — {label}")
        print(f"    {c}/{len(rs)}  ({100*c/len(rs):.1f}%)")
    print()

    print("  Tribal Knowledge Breakdown:")
    for tk, rs in sorted(tribal_buckets.items()):
        if tk == "none":
            continue
        c = sum(1 for r in rs if r["correct"])
        print(f"    {tk[:55]:<55}  {c}/{len(rs)}")
    print()

    print("  ── Incorrect Answers ────────────────────────────────")
    for r in results:
        if not r["correct"]:
            print(f"  {r['id']:6s}  {r['detail']}")
    print()
    print("=" * 60)

    # ── Save machine-readable report ─────────────────────────────────────────
    report = {
        "round": round_name,
        "overall": {"correct": correct, "total": total, "pct": round(100*correct/total, 1)},
        "by_group": {
            g: {
                "correct": sum(1 for r in rs if r["correct"]),
                "total": len(rs),
                "pct": round(100 * sum(1 for r in rs if r["correct"]) / len(rs), 1) if rs else None
            } for g, rs in groups.items() if rs
        },
        "by_tribal_knowledge": {
            tk: {
                "correct": sum(1 for r in rs if r["correct"]),
                "total": len(rs),
                "wrong_ids": [r["id"] for r in rs if not r["correct"]]
            } for tk, rs in tribal_buckets.items() if tk != "none"
        },
        "per_question": results,
    }

    report_path = answers_file.parent / "eval_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Full report saved to: {report_path}")


if __name__ == "__main__":
    main()
