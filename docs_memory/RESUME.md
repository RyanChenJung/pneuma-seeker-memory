# RESUME — Live State (read this FIRST after /clear)

> The single snapshot of where we are. On resume, read this → then `DECISIONS.md`,
> `TASKS.md`, and (if touching the 6-tier work) `code-vs-6tier-mapping.md`. Continue from
> **"Next action"**. Do not re-derive settled facts. Keep this file updated at the end of
> each working session.
> **Last updated:** 2026-06-11 (Tier 5 internal design LOCKED as D16; spec
> `tier5-schema-graph-design.md`). Next = Tier 6 (last tier).

## Project in one line
A memory-layer plugin (6-tier design) on a **fork** of pneuma-seeker. **Never PR/push to
upstream.** Operating rules → `CLAUDE.md`. Settled decisions → `DECISIONS.md`.

## Two work threads in flight
1. **Understanding (HTML docs)** — finishing `docs_understanding/` HTML. Goal **G1** in TASKS.md.
2. **Design (6-tier memory)** — defining the memory tier by tier. Tiers 1–5 LOCKED
   (D11/D12/D14/D15/D16); **current focus = Tier 6 (last tier)**.

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
  Enhancer). Spec: `tier2-episodic-log-design.md`. Our own store
  `services/memory/_episodic/` (gitignored), **not** ws.db
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
- **Tier 3 design LOCKED (DECISIONS D14)** — spec `tier3-user-memory-design.md`. Persistent
  prior *about a person*; two sources = **Provisioned** (manual file: role/dept/grade) +
  **Learned** (Enhancer from T2: alias map, focus range, corrections, format prefs). **Focus
  range = derived (Enhancer tallies a schema/concept frequency distribution), NOT a hand-typed
  free-text line** — this is the single-user seed of the BACKLOG "user-similarity space /
  emergent departments" idea. **Authorization deferred** (T3 = where the user *focuses*, not
  what they may *see*). **Corrected D13's "T3 is a leaf of T4"** → two distinct tiers
  (owner/authority/subject differ), only sharing the overlay *injection* mechanism. Read =
  inject whole small block (no runtime summarization); write = async Enhancer, rewritable,
  recurrence threshold; backend = file/user behind `UserMemory` iface (vector + multi-user =
  deferred swaps).
- **Opened `docs_memory/BACKLOG.md`** — registry of intentionally-deferred *design items*
  (distinct from TASKS.md's unapproved-work backlog), each with a back-pointer. Seeded with:
  authorization, vector/graph backends, DuckDB upgrade, multi-user T3, user-similarity space
  + emergent departments, decay, DocumentDB-reuse question.
- **Backfilled `tier2-episodic-log-design.md`** — Tier 2 had been locked only inside
  DECISIONS D12 (no standalone spec like T1/T3); created the spec from D12 (no new design),
  added "Spec:" back-pointers in D12 + this file. T1/T2/T3 spec form now consistent.
- **Tier 4 design LOCKED (DECISIONS D15)** — spec `tier4-org-memory-design.md`. **Two-headed
  tier**: (A) **Authored** authoritative KB (externally ingested, NOT from T2/Enhancer — the
  heavy main body, the reason `DocumentDB` exists) + (B) **Learned** org conventions (Enhancer
  from *aggregated* T2). **Authority/trust = T4-unique**: authored always wins, learned only
  supplements. **Read splits by head**: learned → inject-whole (joins D14 overlay), authored →
  top-k retrieval (Retriever → Tier 1). **One `OrgMemory` facade** (`get_org_overlay` +
  `search_authored`, scope=(institution,department)); authored backend hidden (DocumentDB-reuse
  = the OPEN email Q). **Only learned promotes** (T1→T3→T4-dept→T4-inst). **Refines D13**:
  T4's authored side breaks "all tiers from T2"; T4 read ≠ single overlay (learned=overlay,
  authored=retrieval). **MVP = single inst + single dept w/ a small REAL authored set; NEAR-
  TERM (not backlog) = ≥2 departments** to prove "same question, different dept → each
  converges to its own correct latent intent."
- **Tier 5 design LOCKED (DECISIONS D16)** — spec `tier5-schema-graph-design.md`. Persistent
  **property graph** patching messy EHR schemas. **Data model**: `table`+`column` nodes,
  `column` hangs off table via `contains`, **join edges connect two column nodes**. **Payload**:
  edges = `utility_score`/success+fail counts/`negative_constraints[]`/`last_seen`; column nodes
  = value/temporal caveats; every learned item carries `source_episode` = **Tier 2 id as a SOFT
  back-pointer** (self-contained lessons → **no retention lock on T2**, decoupled from the
  delete/keep decision). **`SchemaGraph` iface**: read (RO) `get_join_path`/`get_column_caveats`;
  write (**Enhancer only**) `reinforce`/`penalize`/`annotate`; permission = two different clients.
  **Read = graph-first, heuristic fallback** (graph hit → validated edge + inject caveats; miss →
  today's `join_paths` heuristic, no regression; corrected joins written back). **Organic growth,
  NO pre-built FK expansion** (declared FK = intent not guarantee; dirty EHR joins fail). Node key
  = fully-qualified `schema.table.column`; rename → orphaned node (relearn from zero) → BACKLOG.
  **T4/T5 boundary sharpened**: authored = org norms/definitions only, **all empirical join
  knowledge = T5 evidence-first**. NetworkX/JSON; Neo4j = deferred swap.
  - **New lean (not locked):** user leaning toward **T2 = no-delete** (traceability/explainability)
    → would downgrade D12 `processed_at` to a pure progress marker. Parked in BACKLOG; T5 unaffected.

## ⏸ Waiting on the user
- (optional) User spot-check of any v2 HTML page — all needs-review but not blocking.
- **User to email the upstream author** re: whether the `DocumentDB`/`Knowledge` local/global
  design generalizes / where our memory interface should attach (D13/D15 OPEN item). **Draft
  ready** at `docs_memory/_email-draft-upstream-author.md` (untracked temp; user will delete
  after sending). Asks 4 things: purpose, local-vs-global semantics, the `index()` conflict
  TODO, and their roadmap (collision-avoidance). Sender = master's-capstone collaborator.

## ▶ Next action
- **Tier 5 drill is DONE and recorded (D16).** Tiers 1–5 now LOCKED (D11/D12/D14/D15/D16);
  only Tier 6 has a D13 "Decided (direction)" block left.
- **NEXT: drill into Tier 6 (Long Memory — the LAST tier)** and lock it, same cadence
  (discuss → lock → record into mapping + DECISIONS; no coding yet). Anchor against D13's T6
  "Decided (direction)" block (`code-vs-6tier-mapping.md`): T6 = the **method skeleton / the
  *verb*** (how to solve a *class* of problem, DB-agnostic) vs T5's navigation (the *noun*:
  how to read *this* DB) — they compose. **v1 = trajectory-RAG** (retrieve the most-similar
  past *successful* trajectory, inject as a few-shot worked example); **v2 = abstracted,
  parameterized plan templates** keyed by problem-type (the Enhancer's hardest LLM-as-judge
  job, deferred). Risk to resolve: un-abstracted T6 collapses into a SQL cache (v1 mitigates
  by being explicitly few-shot). Likely D6 questions to settle: what "problem-type" key to
  retrieve on, success-detection from Tier 2, T6/T2 boundary (template vs raw trace), and the
  `LongMemory` interface surface. After T6, **all six tiers are locked** → design phase done,
  coding (B3/B4) is the natural next move.
- Reference: `system_architecture.md` (6-tier spec) + `code-vs-6tier-mapping.md` (per-tier
  gap analysis) + `BACKLOG.md` (deferred items).
- **Coding is unblocked when the user wants it** (not the immediate path): B3 (scaffold
  `services/memory/` + `ENABLE_MEMORY_*` flags, default off) and B4 (Tier 2 episodic log —
  first coding goal, design locked). Both need user go-ahead (workflow step 3).

## How to resume (minimal prompt)
Type **`繼續`** (or `resume`). `CLAUDE.md` instructs me to read this file and pick up the
"Next action". Nothing else needed.
