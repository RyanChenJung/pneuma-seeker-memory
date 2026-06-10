# RESUME — Live State (read this FIRST after /clear)

> The single snapshot of where we are. On resume, read this → then `DECISIONS.md`,
> `TASKS.md`, and (if touching the 6-tier work) `code-vs-6tier-mapping.md`. Continue from
> **"Next action"**. Do not re-derive settled facts. Keep this file updated at the end of
> each working session.
> **Last updated:** 2026-06-10 (Tiers 3–6 big-picture/boundary pass recorded as D13).

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
- **Tiers 3–6 BIG-PICTURE / BOUNDARY pass DONE → DECISIONS D13** (per-tier "Decided
  (direction)" blocks added to `code-vs-6tier-mapping.md`). Agreed: Tiers 3–6 = persistent
  priors, Enhancer-written, distilled from Tier 2. **T3 MVP = single-user** (keep `user_id`
  + interface → multi-user = backend swap). **T4 Org = scope HIERARCHY** (User→Department
  →Institution, CLAUDE.md-style overlay; content filtered by *actionability* not breadth);
  **scalability answer = build mechanism once, Enhancer auto-fills each scope's content from
  Tier 2 → zero per-department redesign**. **T4/T5 boundary = meaning vs physical
  navigation**. **T5 = NetworkX/JSON property graph** (`SchemaGraph` iface; nodes+edges both
  carry payload; learn-by-correction). **T6 = method skeleton** (v1 trajectory-RAG, v2
  abstract templates). **OPEN:** reuse author's `DocumentDB` local/global design? — user will
  **email upstream author** (local≈T3, global≈T4 working assumption); exact scope-level count
  + overlay precedence still provisional.

## ⏸ Waiting on the user
- (optional) User spot-check of any v2 HTML page — all needs-review but not blocking.
- **User to email the upstream author** re: whether the `DocumentDB`/`Knowledge` local/global
  design generalizes / where our memory interface should attach (D13 OPEN item).

## ▶ Next action
- **Big-picture/boundary pass is DONE and recorded (D13).** Two OPEN items remain before/
  alongside the Tier 3 drill: (i) user's email to the upstream author (DocumentDB reuse?),
  (ii) exact scope-level count + overlay precedence (provisional).
- **NEXT: drill into Tier 3 (User Memory)** detail and lock it, continuing the tier-by-tier
  design-lock cadence (discuss → lock → record into mapping + DECISIONS; no coding yet).
  Tier 3 = per-user persona/habits store, the "prior" that accelerates latent-intent
  convergence; fed by the Tier 2 log keyed on `user_id`. **MVP = single-user (D13).** Drill
  topics: what a user profile holds, how it's summarized for env-state injection, write/update
  cadence via Enhancer, and how it overlays under the T4 scope hierarchy.
- Reference: `system_architecture.md` (6-tier spec) + `code-vs-6tier-mapping.md` (per-tier
  gap analysis; Tiers 1–2 LOCKED D11/D12, Tiers 3–6 now have D13 "Decided (direction)"
  blocks). Anchor Tier 3 against D11/D12/D13.
- **Coding is unblocked when the user wants it** (not the immediate path): B3 (scaffold
  `services/memory/` + `ENABLE_MEMORY_*` flags, default off) and B4 (Tier 2 episodic log —
  first coding goal, design locked). Both need user go-ahead (workflow step 3).

## How to resume (minimal prompt)
Type **`繼續`** (or `resume`). `CLAUDE.md` instructs me to read this file and pick up the
"Next action". Nothing else needed.
