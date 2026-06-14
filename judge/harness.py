"""
harness.py — The Judge's main benchmark runner.

Loads test cases, runs them against /chat (stub or real), scores results,
and writes CSV + Markdown reports.

Usage:
    # W1: run against stub (start stub_server.py first)
    python harness.py --base-url http://localhost:8000 --mode memory_off

    # W2+: point at real MVP
    python harness.py --base-url http://localhost:8000 --mode memory_off
    python harness.py --base-url http://localhost:8000 --mode memory_on

    # Run both modes in sequence (full A/B — W3/W4)
    python harness.py --base-url http://localhost:8000 --mode both

Options:
    --test-cases   path to test_cases.json  (default: test_cases.json)
    --base-url     Pneuma /chat base URL    (default: http://localhost:8000)
    --mode         memory_off | memory_on | both  (default: memory_off)
    --concurrency  max parallel requests    (default: 4)
    --out-dir      directory for reports    (default: reports/)
    --timeout      per-request timeout (s)  (default: 30)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import aiohttp

from parser import load_test_cases, TestCase
from caller import call_chat, ChatResult
from metrics import score, ScoredResult, to_csv, to_markdown


# ── run one mode ──────────────────────────────────────────────────────────────

async def _run_mode(
    cases: List[TestCase],
    base_url: str,
    run_mode: str,
    concurrency: int,
    timeout: float,
) -> List[ScoredResult]:
    """Run all test cases for a single mode (memory_off or memory_on) concurrently."""
    sem = asyncio.Semaphore(concurrency)
    results: List[ScoredResult] = []

    async def _run_one(case: TestCase, session: aiohttp.ClientSession) -> ScoredResult:
        async with sem:
            print(f"  → [{run_mode}] {case.case_id} ({case.persona}) ...", flush=True)
            chat_result = await call_chat(
                base_url=base_url,
                case_id=case.case_id,
                persona=case.persona,
                messages=case.as_messages(),
                run_mode=run_mode,
                session=session,
                timeout_seconds=timeout,
            )
            scored = score(chat_result, case)
            status = "✓" if scored.success else "✗"
            err    = f"  ERROR: {scored.error}" if scored.error else ""
            print(
                f"  {status} [{run_mode}] {case.case_id}  "
                f"latency={scored.latency_seconds:.3f}s  "
                f"tokens={scored.total_tokens}  "
                f"tables={scored.tables_extracted}{err}",
                flush=True,
            )
            return scored

    async with aiohttp.ClientSession() as session:
        tasks = [_run_one(c, session) for c in cases]
        results = await asyncio.gather(*tasks)

    return list(results)


# ── write reports ─────────────────────────────────────────────────────────────

def _write_reports(results: List[ScoredResult], out_dir: Path, tag: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"results_{tag}.csv"
    md_path  = out_dir / f"report_{tag}.md"

    csv_path.write_text(to_csv(results), encoding="utf-8")
    md_path.write_text(to_markdown(results), encoding="utf-8")

    print(f"\n  Wrote CSV    → {csv_path}")
    print(f"  Wrote report → {md_path}")


# ── main ──────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> int:
    # 1. load + validate test cases
    print(f"\nLoading test cases from: {args.test_cases}")
    try:
        cases = load_test_cases(args.test_cases)
    except (FileNotFoundError, ValueError) as e:
        print(f"✗ Failed to load test cases: {e}", file=sys.stderr)
        return 1
    print(f"  {len(cases)} case(s) loaded.")

    modes = ["memory_off", "memory_on"] if args.mode == "both" else [args.mode]
    tag   = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_results: List[ScoredResult] = []

    for mode in modes:
        print(f"\nRunning mode: {mode}  (base_url={args.base_url})")
        if mode == "memory_on":
            print(
                "  ⚠  Make sure the server was started with "
                "ENABLE_MEMORY_INJECTION=true before this run."
            )
        results = await _run_mode(
            cases=cases,
            base_url=args.base_url,
            run_mode=mode,
            concurrency=args.concurrency,
            timeout=args.timeout,
        )
        all_results.extend(results)

        success_count = sum(1 for r in results if r.success and not r.error)
        error_count   = sum(1 for r in results if r.error)
        print(
            f"\n  Mode {mode}: "
            f"{success_count}/{len(results)} success  "
            f"{error_count} error(s)"
        )

    # 2. write combined reports
    print("\nWriting reports...")
    out_dir = Path(args.out_dir)
    _write_reports(all_results, out_dir, tag)

    # 3. quick summary to stdout
    print("\n" + "─" * 60)
    print(to_markdown(all_results))

    # return non-zero if any case errored
    return 1 if any(r.error for r in all_results) else 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pneuma memory benchmark harness (The Judge)")
    p.add_argument("--test-cases",  default="test_cases.json", help="Path to test_cases.json")
    p.add_argument("--base-url",    default="http://localhost:8000", help="Pneuma /chat base URL")
    p.add_argument("--mode",        choices=["memory_off", "memory_on", "both"], default="memory_off")
    p.add_argument("--concurrency", type=int, default=4, help="Max parallel requests")
    p.add_argument("--out-dir",     default="reports", help="Directory to write CSV/MD reports")
    p.add_argument("--timeout",     type=float, default=30.0, help="Per-request timeout in seconds")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(asyncio.run(main(args)))
