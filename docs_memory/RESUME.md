# RESUME — Live State (read this FIRST after /clear)

> The single snapshot of where we are. On resume, read this → then `DECISIONS.md`,
> `TASKS.md`, and (if touching the 6-tier work) `code-vs-6tier-mapping.md`. Continue from
> **"Next action"**. Do not re-derive settled facts. Keep this file updated at the end of
> each working session.
> **Last updated:** 2026-06-10.

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
- **HTML done: ALL 11 module pages written in 易懂規範 v2** (materializer 1028 = gold
  standard; ir_system + action_set retrofitted to v2; db/indexing/language_model/shared/
  provenance/tests/baselines/openwebui fanned out 2026-06-10). All = **needs-review** (user
  to spot-check). Only **batch 5** (3 synthesis pages H12–H14) left. See CHECKPOINT.md.
- **Tier 1 design LOCKED (DECISIONS D11)** — decisions (a)–(d) confirmed; (b) = ephemeral
  `.md` per conversation in gitignored `services/memory/_notebooks/`, behind a small
  `Notebook` interface; ws.db = deferred upgrade path. Spec: `tier1-short-memory-design.md`.

## ⏸ Waiting on the user
- (optional) User spot-check of any v2 module page — all are needs-review but not blocking.
- Whether to fire **batch 5** (synthesis pages) now or after a review pass.

## ▶ Next action
- **Tier 2 discussion** — the append-only **episodic log**: the foundation the Enhancer +
  Tiers 3/5/6 depend on, and likely the first *coding* goal (backlog B4). This is the main
  next thread.
- Secondary: fire HTML **batch 5** (H12 architecture_deep_dive / H13 flow_traces /
  H14 concepts) — depends on H1–H11, which are now all written. Background sub-agents;
  I update CHECKPOINT.md centrally.

## How to resume (minimal prompt)
Type **`繼續`** (or `resume`). `CLAUDE.md` instructs me to read this file and pick up the
"Next action". Nothing else needed.
