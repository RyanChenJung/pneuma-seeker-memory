# judge/ — The Benchmark Harness

**Role:** Lawrence (The Judge) — automated black-box benchmark that drives
Pneuma's `/chat` endpoint, runs the same test set with memory **OFF vs ON**,
captures four metrics, and produces CSV + Markdown reports.

---

## Project layout

```
judge/
  harness.py        ← main runner (start here)
  parser.py         ← loads + validates test_cases.json
  caller.py         ← async /chat HTTP client (NDJSON streaming)
  metrics.py        ← scoring + report generation
  stub_server.py    ← local /chat fake for offline development
  test_cases.json   ← placeholder test cases (6 cases, W1)
  reports/          ← CSV + Markdown output (auto-created)
  requirements.txt
```

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Running against the stub (W1 / W2)

**Terminal 1 — start the stub server:**
```bash
python stub_server.py
# → http://127.0.0.1:8000
```

**Terminal 2 — run the harness:**
```bash
# memory OFF only (baseline)
python harness.py --base-url http://127.0.0.1:8000 --mode memory_off

# memory ON only
python harness.py --base-url http://127.0.0.1:8000 --mode memory_on

# full A/B (both modes in sequence)
python harness.py --base-url http://127.0.0.1:8000 --mode both
```

Reports land in `reports/results_<timestamp>.csv` and `reports/report_<timestamp>.md`.

---

## Running against the real MVP (W3+)

The A/B toggle is a **server-side environment variable**, not a request parameter.
You run the same harness twice against two separate server instances:

**Step 1 — baseline run (memory OFF):**
```bash
# Ryan starts Pneuma WITHOUT the flag:
#   ENABLE_MEMORY_INJECTION=false uvicorn ...

python harness.py --base-url http://<pneuma-host>:8000 --mode memory_off
```

**Step 2 — memory run (memory ON):**
```bash
# Ryan restarts Pneuma WITH the flag:
#   ENABLE_MEMORY_INJECTION=true uvicorn ...

python harness.py --base-url http://<pneuma-host>:8000 --mode memory_on
```

**Do NOT set `data_source` in requests** — both departments are co-loaded server-side.

---

## The /chat request contract

```json
{
  "user_id":  "u_adm_analyst",
  "chat_id":  "TC001-memory_off",
  "messages": [{"role": "user", "content": "What is our retention rate?"}]
}
```

- `user_id` = persona key (carries department + role identity)
- `chat_id` = `<case_id>-<run_mode>` — unique per case per run
- `messages` = full turn history re-sent every call (multi-turn safe)

Valid persona keys: `u_adm_analyst` · `u_adm_director` · `u_fin_analyst` · `u_fin_director`

---

## Metrics captured

| Metric | Source | Description |
|--------|--------|-------------|
| `success` | scored | table_match (W1); + rule_matched (W2) |
| `latency_seconds` | `done` line | server-reported elapsed time |
| `input_tokens` | `done` / `assistant` | LLM input token count |
| `output_tokens` | `done` / `assistant` | LLM output token count |
| `clarifying_turns` | stream count | assistant turns before final SQL |

---

## test_cases.json schema

```json
[
  {
    "case_id":     "TC001",
    "description": "optional human note",
    "persona":     "u_adm_analyst",
    "turns": [
      {"role": "user",      "content": "What is our retention rate?"},
      {"role": "assistant", "content": "..."},
      {"role": "user",      "content": "First-year students."}
    ],
    "ground_truth": {
      "target_tables": ["students", "enrollments"],
      "rule_applied":  "exclude transfer students (is_transfer = true)"
    }
  }
]
```

Juan delivers the real `test_cases.json` by **6/24 (W2)**. Replace the placeholder
file; the parser will validate it automatically.

---

## W1 → W4 Roadmap

| Week | Due | What |
|------|-----|------|
| W1 | 6/17 | This harness on stub ✓ |
| W2 | 6/24 | Real `/chat` caller + rule_matched scoring + Juan's test cases |
| W3 | 7/1  | Hook to real MVP; first true A/B run; CSV/MD report |
| W4 | 7/8  | Full A/B on v0.1-MVP; Phase-1 benchmark report |

---

## Individual module smoke tests

```bash
python parser.py test_cases.json      # validate test_cases.json
python caller.py http://127.0.0.1:8000 memory_off   # one-shot caller test
```
