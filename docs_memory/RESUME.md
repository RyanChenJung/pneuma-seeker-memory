# RESUME — Live State (read this FIRST after /clear)

> The single snapshot of where we are. On resume, read this → then `DECISIONS.md`,
> `TASKS.md`, and (if touching the 6-tier work) `code-vs-6tier-mapping.md`. Continue from
> **"Next action"**. Do not re-derive settled facts. Keep this file updated at the end of
> each working session.
> **Last updated:** 2026-06-09.

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
- HTML **batch 1** written (materializer / ir_system / action_set). **Materializer revised
  to the new "易懂規範 v2" easier style** (1028 lines) — now the gold-standard template.
- Tier 1 understanding corrected & recorded (DECISIONS **D9**): it is a curated salience
  **"notebook"**, NOT the raw `llm_messages`. Design DRAFT → `tier1-short-memory-design.md`.

## ⏸ Waiting on the user (can be answered now or after /clear)
**A — HTML style lock.** Open
`docs_understanding/modules/services_core_materializer/index.html`; confirm the easier v2
style is good (or say what to adjust). This gates fanning out the rest of the HTML.

**B — Tier 1 design decisions (a)–(d)** in `tier1-short-memory-design.md`:
(a) write trigger · (b) storage (.md vs ws.db) · (c) pin position · (d) capacity policy.
My recommendation for each is in that file — user just confirms or adjusts.

## ▶ Next action once unblocked
- **If user OKs v2 style** → dispatch HTML **batch 2–4** agents (db, indexing,
  language_model, shared, provenance, tests, baselines, openwebui) using the v2 standard,
  AND retrofit ir_system + action_set to v2. Then **batch 5** (3 deep-dive pages). Track in
  TASKS G1. (Use background sub-agents; I update CHECKPOINT.md centrally.)
- **If user answers Tier 1 (a)–(d)** → finalize `tier1-short-memory-design.md`, then move
  to **Tier 2** discussion (the episodic log — the foundation the Enhancer + Tiers 3/5/6
  depend on).

## How to resume (minimal prompt)
Type **`繼續`** (or `resume`). `CLAUDE.md` instructs me to read this file and pick up the
"Next action". Nothing else needed.
