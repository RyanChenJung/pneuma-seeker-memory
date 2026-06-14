"""
metrics.py — scoring and metric aggregation.

Takes a ChatResult (from caller.py) and a TestCase (from parser.py) and
produces a scored ScoredResult.  Also aggregates a list of ScoredResults
into a summary report (CSV rows + a Markdown table).

W1: success scoring is table-match only (rule scoring is a stub).
W2: fill in rule_matched logic once we see how the real LLM signals rules.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from caller import ChatResult
from parser import TestCase


# ── scored result ─────────────────────────────────────────────────────────────

@dataclass
class ScoredResult:
    # identity
    case_id: str
    persona: str
    run_mode: str          # "memory_off" | "memory_on"

    # ground truth
    expected_tables: List[str]
    expected_rule: str

    # what the model produced
    tables_extracted: List[str]
    assistant_content: str

    # metrics
    latency_seconds: float
    input_tokens: int
    output_tokens: int
    clarifying_turns: int

    # scoring
    table_match: bool        # all expected tables present in output
    rule_matched: Optional[bool] = None   # None = not yet scored (W2)
    success: bool = False    # table_match AND rule_matched (or just table_match for W1)

    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# ── scoring logic ─────────────────────────────────────────────────────────────

def _score_table_match(extracted: List[str], expected: List[str]) -> bool:
    """All expected tables must appear in the extracted list (case-insensitive)."""
    extracted_lower = {t.lower() for t in extracted}
    return all(t.lower() in extracted_lower for t in expected)


def _score_rule_match(assistant_content: str, expected_rule: str) -> Optional[bool]:
    """
    W1 STUB — returns None (not scored yet).

    W2 plan: parse the assistant SQL or reasoning for signals that the rule
    was applied, e.g.:
      - "is_transfer = false"  in the WHERE clause
      - "is_realized = true"
      - date range matching fiscal year (Jul 1 – Jun 30)
    Fill this in once we see real LLM output patterns.
    """
    # TODO (W2): implement keyword/regex checks against known rule signals
    return None


def score(result: ChatResult, case: TestCase) -> ScoredResult:
    """Score a single ChatResult against its TestCase ground truth."""
    table_match  = _score_table_match(result.tables_extracted, case.ground_truth.target_tables)
    rule_matched = _score_rule_match(result.assistant_content, case.ground_truth.rule_applied)

    # W1: success = table match only (rule scoring not yet implemented)
    # W2: success = table_match AND rule_matched
    success = table_match  # upgrade to: table_match and (rule_matched is True) in W2

    return ScoredResult(
        case_id=result.case_id,
        persona=result.persona,
        run_mode=result.run_mode,
        expected_tables=case.ground_truth.target_tables,
        expected_rule=case.ground_truth.rule_applied,
        tables_extracted=result.tables_extracted,
        assistant_content=result.assistant_content[:300],   # truncate for report
        latency_seconds=result.latency_seconds,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        clarifying_turns=result.clarifying_turns,
        table_match=table_match,
        rule_matched=rule_matched,
        success=success,
        error=result.error,
    )


# ── aggregation ───────────────────────────────────────────────────────────────

@dataclass
class BenchmarkSummary:
    run_mode: str
    total_cases: int
    successful: int
    success_rate: float
    avg_latency: float
    avg_input_tokens: float
    avg_output_tokens: float
    avg_clarifying_turns: float
    errors: int


def aggregate(results: List[ScoredResult], run_mode: str) -> BenchmarkSummary:
    """Compute aggregate metrics for one run mode (OFF or ON)."""
    subset = [r for r in results if r.run_mode == run_mode and r.error is None]
    total  = len(subset)
    if total == 0:
        return BenchmarkSummary(
            run_mode=run_mode, total_cases=0, successful=0,
            success_rate=0.0, avg_latency=0.0, avg_input_tokens=0.0,
            avg_output_tokens=0.0, avg_clarifying_turns=0.0, errors=0,
        )

    errors = sum(1 for r in results if r.run_mode == run_mode and r.error is not None)

    return BenchmarkSummary(
        run_mode=run_mode,
        total_cases=total,
        successful=sum(1 for r in subset if r.success),
        success_rate=round(sum(1 for r in subset if r.success) / total, 4),
        avg_latency=round(sum(r.latency_seconds for r in subset) / total, 3),
        avg_input_tokens=round(sum(r.input_tokens for r in subset) / total, 1),
        avg_output_tokens=round(sum(r.output_tokens for r in subset) / total, 1),
        avg_clarifying_turns=round(sum(r.clarifying_turns for r in subset) / total, 2),
        errors=errors,
    )


# ── report generation ─────────────────────────────────────────────────────────

CSV_FIELDS = [
    "case_id", "persona", "run_mode",
    "success", "table_match", "rule_matched",
    "latency_seconds", "input_tokens", "output_tokens", "total_tokens",
    "clarifying_turns",
    "expected_tables", "tables_extracted",
    "error",
]


def to_csv(results: List[ScoredResult]) -> str:
    """Return all results as a CSV string."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for r in results:
        row = {
            **{k: getattr(r, k, "") for k in CSV_FIELDS},
            "expected_tables": "|".join(r.expected_tables),
            "tables_extracted": "|".join(r.tables_extracted),
            "total_tokens": r.total_tokens,
        }
        writer.writerow(row)
    return buf.getvalue()


def to_markdown(results: List[ScoredResult]) -> str:
    """Return a Markdown report: per-case table + OFF vs ON summary."""
    lines = ["# Benchmark Results\n"]

    # ── per-case table ────────────────────────────────────────────────────────
    lines.append("## Per-case results\n")
    lines.append(
        "| case_id | persona | mode | success | table_match | "
        "latency(s) | tokens | clarify_turns | error |"
    )
    lines.append("|---------|---------|------|---------|-------------|"
                 "-----------|--------|---------------|-------|")
    for r in results:
        err = r.error or ""
        lines.append(
            f"| {r.case_id} | {r.persona} | {r.run_mode} "
            f"| {'✓' if r.success else '✗'} "
            f"| {'✓' if r.table_match else '✗'} "
            f"| {r.latency_seconds:.3f} "
            f"| {r.total_tokens} "
            f"| {r.clarifying_turns} "
            f"| {err} |"
        )

    # ── summary table ─────────────────────────────────────────────────────────
    lines.append("\n## Summary: memory OFF vs ON\n")
    lines.append(
        "| metric | memory_off | memory_on |"
    )
    lines.append("|--------|-----------|----------|")

    off = aggregate(results, "memory_off")
    on  = aggregate(results, "memory_on")

    def _row(label: str, off_val, on_val) -> str:
        return f"| {label} | {off_val} | {on_val} |"

    lines += [
        _row("success_rate",         f"{off.success_rate:.0%}", f"{on.success_rate:.0%}"),
        _row("avg_latency (s)",      off.avg_latency,           on.avg_latency),
        _row("avg_input_tokens",     off.avg_input_tokens,      on.avg_input_tokens),
        _row("avg_output_tokens",    off.avg_output_tokens,     on.avg_output_tokens),
        _row("avg_clarifying_turns", off.avg_clarifying_turns,  on.avg_clarifying_turns),
        _row("errors",               off.errors,                on.errors),
    ]

    lines.append("\n> rule_matched scoring: W1 stub — will be filled in W2.\n")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("metrics.py: import and use score(), to_csv(), to_markdown().")
    print("Run harness.py for a full end-to-end smoke test.")
