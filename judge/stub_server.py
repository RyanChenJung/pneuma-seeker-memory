"""
stub_server.py — local /chat stub for developing the harness without the real MVP.

Mimics the Pneuma /chat endpoint: accepts the same request body, returns
NDJSON with log / assistant / done lines.  Responses are hardcoded per
persona so the harness can exercise success/failure scoring logic.

Usage:
    pip install fastapi uvicorn
    python stub_server.py          # runs on http://localhost:8000
    python stub_server.py --port 9000
"""

from __future__ import annotations

import asyncio
import json
import time
import argparse
import random
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI(title="Pneuma /chat stub")

# ── per-persona stub SQL responses ────────────────────────────────────────────
# Maps persona → (sql_snippet, tables_used, tokens_in, tokens_out)
# Designed so:
#   - adm personas → correct tables (students, enrollments, applications)
#   - fin personas → correct tables (transactions, funds, investments)
#   - A future "memory OFF" mode could return wrong tables to simulate baseline
#
PERSONA_RESPONSES: dict[str, dict] = {
    "u_adm_analyst": {
        "sql": (
            "SELECT COUNT(CASE WHEN e.is_enrolled THEN 1 END) * 1.0 / "
            "COUNT(s.student_id) AS retention_rate "
            "FROM students s "
            "JOIN enrollments e ON s.student_id = e.student_id "
            "WHERE s.cohort_year = 2023 AND s.is_transfer = false"
        ),
        "tables": ["students", "enrollments"],
        "tokens_in": 312,
        "tokens_out": 95,
    },
    "u_adm_director": {
        "sql": (
            "SELECT s.program, "
            "ROUND(COUNT(CASE WHEN e.is_enrolled THEN 1 END) * 100.0 / COUNT(s.student_id), 2) AS retention_pct "
            "FROM students s "
            "JOIN enrollments e ON s.student_id = e.student_id "
            "WHERE s.cohort_year = 2023 AND s.is_transfer = false "
            "GROUP BY s.program ORDER BY retention_pct DESC"
        ),
        "tables": ["students", "enrollments"],
        "tokens_in": 340,
        "tokens_out": 120,
    },
    "u_fin_analyst": {
        "sql": (
            "SELECT SUM(CASE WHEN txn_type = 'retained' THEN amount ELSE 0 END) * 1.0 / "
            "SUM(CASE WHEN txn_type = 'inflow' THEN amount ELSE 0 END) AS retention_rate "
            "FROM transactions "
            "WHERE txn_date >= '2025-07-01' AND txn_date < '2026-07-01'"
        ),
        "tables": ["transactions", "funds"],
        "tokens_in": 298,
        "tokens_out": 88,
    },
    "u_fin_director": {
        "sql": (
            "SELECT f.fund_type, "
            "ROUND(SUM(CASE WHEN t.txn_type='retained' THEN t.amount ELSE 0 END) * 100.0 / "
            "SUM(CASE WHEN t.txn_type='inflow' THEN t.amount ELSE 0 END), 2) AS retention_pct "
            "FROM funds f JOIN transactions t ON f.fund_id = t.fund_id "
            "WHERE t.txn_date >= '2025-07-01' AND t.txn_date < '2026-07-01' "
            "GROUP BY f.fund_type"
        ),
        "tables": ["transactions", "funds"],
        "tokens_in": 360,
        "tokens_out": 130,
    },
}

UNKNOWN_PERSONA_RESPONSE = {
    "sql": "-- unknown persona: no injection applied; query may be ambiguous",
    "tables": [],
    "tokens_in": 200,
    "tokens_out": 30,
}


async def _ndjson_stream(
    user_id: str,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Yield NDJSON lines mimicking Pneuma's log / assistant / done sequence."""

    resp = PERSONA_RESPONSES.get(user_id, UNKNOWN_PERSONA_RESPONSE)

    # simulate a short processing delay
    await asyncio.sleep(random.uniform(0.05, 0.15))

    yield json.dumps({"type": "log", "message": "Retrieving relevant tables..."}) + "\n"
    await asyncio.sleep(random.uniform(0.05, 0.10))

    yield json.dumps({"type": "log", "message": "Constructing SQL query..."}) + "\n"
    await asyncio.sleep(random.uniform(0.10, 0.25))

    assistant_payload = {
        "type": "assistant",
        "content": resp["sql"],
        "metadata": {
            "tables_referenced": resp["tables"],
            "usage": {
                "input_tokens": resp["tokens_in"],
                "output_tokens": resp["tokens_out"],
            },
        },
    }
    yield json.dumps(assistant_payload) + "\n"
    await asyncio.sleep(0.02)

    elapsed = round(random.uniform(0.4, 1.2), 3)
    yield json.dumps({
        "type": "done",
        "elapsed_seconds": elapsed,
        "usage": {
            "input_tokens": resp["tokens_in"],
            "output_tokens": resp["tokens_out"],
        },
    }) + "\n"


@app.post("/chat")
async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    user_id  = body.get("user_id", "")
    messages = body.get("messages", [])

    return StreamingResponse(
        _ndjson_stream(user_id, messages),
        media_type="application/x-ndjson",
    )


@app.get("/health")
def health():
    return {"status": "ok", "mode": "stub"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pneuma /chat stub server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"Starting stub server on http://{args.host}:{args.port}")
    print("POST /chat  →  NDJSON stream (stub mode)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
