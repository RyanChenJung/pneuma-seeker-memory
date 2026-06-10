# RESUME — Live State (read this FIRST after /clear)

> The single snapshot of where we are. On resume, read this → then `DECISIONS.md`,
> `TASKS.md`, and (if touching the 6-tier work) `code-vs-6tier-mapping.md`. Continue from
> **"Next action"**. Do not re-derive settled facts. Keep this file updated at the end of
> each working session.
> **Last updated:** 2026-06-10 (Tier 2 design locked; HTML batch 5 done).

## Project in one line
A memory-layer plugin (6-tier design) on a **fork** of pneuma-seeker. **Never PR/push to
upstream.** Operating rules → `CLAUDE.md`. Settled decisions → `DECISIONS.md`.

## Two work threads in flight
1. **Understanding (HTML docs)** — finishing `docs_understanding/` HTML. Goal **G1** in TASKS.md.
2. **Design (6-tier memory)** — defining the memory tier by tier. Current focus = **Tier 1**.

## Done recently
- PR-safety guardrails + `gh` installed/authed, default repo = fork (S0.1–S0.4 ✅).
- Foundation docs: `CLAUDE.md`, `DECISIONS.md`, `TASKS.md`, `codebase-map.md`,
  `code-vs-6tier-mapping.md` — **committed** to `feat-memory-experiement`.
  (`docs_understanding/` HTML stays local/uncommitted — CN-ignore, DECISIONS D10.)
- **HTML GOAL G1 COMPLETE** — all 14 module pages + 3 synthesis pages (H12 architecture
  deep dive 804 / H13 flow traces 835 / H14 concepts 805, fanned out 2026-06-10, claims
  verified vs source) + overview, all in 易懂規範 v2. **All = needs-review** (user to
  spot-check, not blocking). Nothing left to write. See CHECKPOINT.md.
- **Tier 1 design LOCKED (DECISIONS D11)** — ephemeral `.md` per conversation in gitignored
  `services/memory/_notebooks/` behind a `Notebook` interface; ws.db = deferred upgrade
  path. Spec: `tier1-short-memory-design.md`.
- **Tier 2 design LOCKED (DECISIONS D12)** — append-only episodic log; **dumb capture, zero
  extra LLM** at write time (serialize ReAct trajectory before GC; condensing = async
  Enhancer). Our own store `services/memory/_episodic/` (gitignored), **not** ws.db
  (delete-and-replace clashes w/ append-only). v1 = **JSONL** behind `EpisodicLog`
  interface; **upgrade path = DuckDB table** (user asked to record this). Step-level full
  trajectory incl. failures + raw CoT; turn-envelope + step-event schema, fields chosen by
  backward-reasoning from Tiers 3–6. Cleanup deferred (`processed_at` watermark). Provenance
  referenced, not reused.

## ⏸ Waiting on the user
- (optional) User spot-check of any v2 HTML page — all needs-review but not blocking.

## ▶ Next action
- **Tier 3 discussion (User Memory)** — continue the tier-by-tier design-lock cadence the
  user set (discuss → lock → record into mapping + DECISIONS; no coding yet). Tier 3 = per-
  user persona/habits store, the "prior" that accelerates latent-intent convergence; fed by
  the Tier 2 log keyed on `user_id`.
- **Now unblocked when the user wants to start *coding*:** B3 (scaffold `services/memory/`
  + `ENABLE_MEMORY_*` flags, default off) and B4 (Tier 2 episodic log — first coding goal,
  design now locked). Both need user go-ahead (workflow step 3) before moving to `todo`.

## How to resume (minimal prompt)
Type **`繼續`** (or `resume`). `CLAUDE.md` instructs me to read this file and pick up the
"Next action". Nothing else needed.
