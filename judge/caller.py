"""
caller.py — async /chat HTTP caller.

Sends requests to the Pneuma /chat endpoint (or stub) and returns a
structured ChatResult with all metrics pre-extracted from the NDJSON stream.

Key design decisions (matching the handoff contract):
  - user_id carries the persona — NO department/role fields in the request body
  - data_source is NOT set — server loads both departments together
  - Multi-turn: same chat_id across turns, full message history resent each call
  - Configurable base_url so you can point at stub or real MVP without code changes
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

import aiohttp

# ── result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ChatResult:
    case_id: str
    persona: str
    run_mode: str                        # "memory_off" | "memory_on"

    # raw
    assistant_content: str = ""          # full assistant text / SQL
    log_messages: List[str] = field(default_factory=list)

    # metrics (populated by caller)
    latency_seconds: float = 0.0         # from "done".elapsed_seconds
    input_tokens: int = 0
    output_tokens: int = 0
    clarifying_turns: int = 0            # assistant turns before final SQL

    # scoring (populated by metrics.py, not here)
    tables_extracted: List[str] = field(default_factory=list)
    success: Optional[bool] = None       # None = not yet scored
    rule_matched: Optional[bool] = None

    error: Optional[str] = None          # set if HTTP/parse error occurred

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# ── NDJSON parsing ────────────────────────────────────────────────────────────

def _parse_ndjson_line(line: str) -> Optional[dict]:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _extract_tables_from_sql(sql: str) -> List[str]:
    """
    Heuristic: pull table names from FROM and JOIN clauses.
    Good enough for scoring against ground truth; not a full SQL parser.
    """
    pattern = re.compile(
        r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        re.IGNORECASE
    )
    return list(dict.fromkeys(m.group(1).lower() for m in pattern.finditer(sql)))


# ── core caller ───────────────────────────────────────────────────────────────

async def call_chat(
    *,
    base_url: str,
    case_id: str,
    persona: str,
    messages: List[dict],
    run_mode: str,
    session: aiohttp.ClientSession,
    timeout_seconds: float = 30.0,
) -> ChatResult:
    """
    POST /chat and stream the NDJSON response.

    Args:
        base_url:        e.g. "http://localhost:8000"
        case_id:         used for chat_id and result labelling
        persona:         one of the four persona keys (u_adm_analyst, etc.)
        messages:        full turn list to send (resend all turns each call)
        run_mode:        "memory_off" or "memory_on" — for labelling only,
                         actual flag is set server-side at startup
        session:         shared aiohttp.ClientSession
        timeout_seconds: hard cap on the whole stream
    """
    result = ChatResult(case_id=case_id, persona=persona, run_mode=run_mode)

    payload = {
        "user_id": persona,
        "chat_id": f"{case_id}-{run_mode}",
        "messages": messages,
    }

    url = f"{base_url.rstrip('/')}/chat"
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        t0 = time.perf_counter()
        assistant_turns = 0

        async with session.post(url, json=payload, timeout=timeout) as resp:
            resp.raise_for_status()

            async for raw_line in resp.content:
                line = raw_line.decode("utf-8")
                obj = _parse_ndjson_line(line)
                if obj is None:
                    continue

                line_type = obj.get("type")

                if line_type == "log":
                    result.log_messages.append(obj.get("message", ""))

                elif line_type == "assistant":
                    assistant_turns += 1
                    result.assistant_content = obj.get("content", "")
                    # token counts may live here or in "done" — accept either
                    usage = obj.get("metadata", {}).get("usage", {})
                    if usage:
                        result.input_tokens  = usage.get("input_tokens", 0)
                        result.output_tokens = usage.get("output_tokens", 0)

                elif line_type == "done":
                    result.latency_seconds = obj.get("elapsed_seconds", 0.0)
                    usage = obj.get("usage", {})
                    if usage and result.input_tokens == 0:
                        result.input_tokens  = usage.get("input_tokens", 0)
                        result.output_tokens = usage.get("output_tokens", 0)

        # clarifying turns = all assistant turns except the final one
        result.clarifying_turns = max(0, assistant_turns - 1)

        # extract table names from the final SQL for scoring
        result.tables_extracted = _extract_tables_from_sql(result.assistant_content)

        if not result.latency_seconds:
            result.latency_seconds = round(time.perf_counter() - t0, 3)

    except aiohttp.ClientError as e:
        result.error = f"HTTP error: {e}"
    except asyncio.TimeoutError:
        result.error = f"Timeout after {timeout_seconds}s"
    except Exception as e:
        result.error = f"Unexpected error: {e}"

    return result


# ── convenience: run a single case end-to-end ─────────────────────────────────

async def run_case(
    *,
    base_url: str,
    case_id: str,
    persona: str,
    messages: List[dict],
    run_mode: str,
) -> ChatResult:
    """Thin wrapper that manages the aiohttp session for one-off calls."""
    async with aiohttp.ClientSession() as session:
        return await call_chat(
            base_url=base_url,
            case_id=case_id,
            persona=persona,
            messages=messages,
            run_mode=run_mode,
            session=session,
        )


# ── CLI smoke test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    url  = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    mode = sys.argv[2] if len(sys.argv) > 2 else "memory_off"

    async def _demo():
        result = await run_case(
            base_url=url,
            case_id="DEMO001",
            persona="u_adm_analyst",
            messages=[{"role": "user", "content": "What is our retention rate this year?"}],
            run_mode=mode,
        )
        if result.error:
            print(f"✗ Error: {result.error}", file=sys.stderr)
            sys.exit(1)

        print(f"case_id         : {result.case_id}")
        print(f"persona         : {result.persona}")
        print(f"run_mode        : {result.run_mode}")
        print(f"latency_seconds : {result.latency_seconds}")
        print(f"input_tokens    : {result.input_tokens}")
        print(f"output_tokens   : {result.output_tokens}")
        print(f"clarifying_turns: {result.clarifying_turns}")
        print(f"tables_extracted: {result.tables_extracted}")
        print(f"assistant_content:\n  {result.assistant_content[:200]}")
        print("✓ caller smoke test passed.")

    asyncio.run(_demo())
