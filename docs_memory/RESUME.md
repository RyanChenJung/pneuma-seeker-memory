# RESUME — Live State (read this FIRST after /clear)

> The single snapshot of where we are. On resume, read this → then `DECISIONS.md`,
> `TASKS.md`, and (if touching the 6-tier work) `code-vs-6tier-mapping.md`. Continue from
> **"Next action"**. Do not re-derive settled facts. Keep this file updated at the end of
> each working session.
> **Last updated:** 2026-06-11 (the quadruplet discussion landed as **D18**: explicit **sextuple**
> record `(intent, associated_experience, support, last_seen, type, source_episode)`; **T6 v1 =
> inject-whole md, NO embedding/vector DB** — embedding/retrieval demoted to Layer 1+; `support` vs
> **A/B validation** corrected; **T2 = no-delete LOCKED** as the A/B replay corpus; shared
> **base record** across T3–T6; authored **dynamic trust**; **three north-star goals** recorded).
> **Design phase fully done. Next task = coding (B3/B4), needs user go-ahead on a TASKS breakdown.**

## Project in one line
A memory-layer plugin (6-tier design) on a **fork** of pneuma-seeker. **Never PR/push to
upstream.** Operating rules → `CLAUDE.md`. Settled decisions → `DECISIONS.md`.

## Two work threads in flight
1. **Understanding (HTML docs)** — finishing `docs_understanding/` HTML. Goal **G1** in TASKS.md.
2. **Design (6-tier memory)** — defining the memory tier by tier. **ALL SIX TIERS LOCKED**
   (D11/D12/D14/D15/D16/D17); **design phase DONE → next thread is coding (B3/B4)**.

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
  edges = `support` (from success+fail counts)/`negative_constraints[]`/`last_seen`; column nodes
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
  - **New lean (later LOCKED in D18-6):** user leaning toward **T2 = no-delete** (traceability/
    explainability) → downgrades D12 `processed_at` to a pure progress marker. *(Was a lean at D16;
    D18-6 locked it — T2 is the A/B replay corpus.)* T5 unaffected.
- **Tier 6 design LOCKED (DECISIONS D17) — LAST TIER, design phase DONE.** Spec
  `tier6-long-memory-design.md`. Persistent **method skeletons** = the *verb* (how to solve a
  *class* of problem, DB-agnostic); composes with T5's *noun* (how to read this DB).
  **Retrieval key = Option C** (NL-embedding + cheap operator-sequence skeleton from T2, no LLM;
  `problem_type` reserved for **v2 = Option B**, user's true north). **Two entry types**
  (`positive exemplar` / `negative anti-pattern`); magnitude = **`support`** = recurrence-weighted
  importance (source-side, dodges the read-side feedback loop); **causal credit-attribution dropped**
  (attribution unsolvable). **Success gate = two-stage** (heuristic eligibility incl. **ReAct
  self-overturn** + **implicit user pushback read from next-turn tone** → recurrence aggregation +
  LLM **distill**); **LLM reads reactions + distills, never "judges correctness"** (the human is the
  ground truth). **Cross-tier routing principle (D6-4):** the Enhancer routes a lesson by *subject*
  (format→T3/T4, reasoning→T6, join→T5); **recurrence = universal noise filter** across T3–T6.
  **`LongMemory` iface** read (RO) `get_exemplars`/`get_anti_patterns` → planning prompt; write
  (Enhancer only) `distill`/`reinforce_support`; read = inject-or-skip → **miss = today's static
  prompt, no regression.** JSON/JSONL; vector store + v2 abstract templates = BACKLOG.
- **The quadruplet discussion → DECISIONS D18 (partially supersedes D17, locks the D16 no-delete
  lean).** Settled: (1) **three north-star goals** = latent intent / tribal knowledge / schema
  knowledge (Glossary; T6 does NOT solve latent intent). (2) Entry = explicit **sextuple**
  `(intent, associated_experience, support, last_seen, type, source_episode)`; `clinical_intent`→
  **`intent`**; `type`=sign (emulate/avoid), orthogonal to `support`, **applies T3–T6**. (3) **T6
  v1 = inject-whole md, NO embedding/vector DB/retrieval key** — *"inject-whole vs retrieve"*
  depends only on store size; at MVP it's small → inject whole → the embedding latent-intent-
  collision flaw doesn't even arise (it only exists when you select by fuzzy similarity).
  Embedding/retrieval = **Layer 1** (conditioned on T3/T4 context, fixes the collision — NOT v2);
  `problem_type` taxonomy = **Layer 2/v2** (must be discovered from T2, can't be first). (4)
  **`support` vs A/B corrected:** A/B validation is a *separate* Enhancer conflict-resolver, NOT
  replaced by recurrence; Enhancer update = 4-branch (insert / `support`++ / merge-split /
  contradiction), **partial-overlap + contradiction both A/B-replay against T2**. (5) **T2 =
  no-delete LOCKED** (it IS the A/B replay corpus); A/B sampled-replay cost → BACKLOG. (6) shared
  **base record** `{support,last_seen,source_episode,type}` across T3–T6 learned records +
  experiential payload `{intent,associated_experience}`; T5 shares base not intent (keeps graph
  topology); T4-authored/T3-provisioned don't inherit. (7) **authored dynamic trust** = f(authority,
  learned negative `support`) → BACKLOG. Specs updated: tier6 (core rewrite), tier2, tier4, BACKLOG.

## ⏸ Waiting on the user
- (optional) User spot-check of any v2 HTML page — all needs-review but not blocking.
- **User to email the upstream author** re: whether the `DocumentDB`/`Knowledge` local/global
  design generalizes / where our memory interface should attach (D13/D15 OPEN item). **Draft
  ready** at `docs_memory/_email-draft-upstream-author.md` (untracked temp; user will delete
  after sending). Asks 4 things: purpose, local-vs-global semantics, the `index()` conflict
  TODO, and their roadmap (collision-avoidance). Sender = master's-capstone collaborator.

## ▶ Next action
- **STEP 1 (user will ask first): verify the docs are clean & correct.** D18 just landed across 7
  files (DECISIONS, tier6 core rewrite, tier2, tier4, BACKLOG, code-vs-6tier-mapping, RESUME). On
  resume the user wants a consistency pass — check no stale "T6 v1 = embedding/trajectory-RAG"
  claims survive, `support`/A-B/sextuple/no-delete are coherent across files, no dangling pointers.
  *(Nothing committed yet — all 7 are unstaged working-tree edits; `git diff` to review.)*
- **STEP 2 (the actual next discussion): how to design the ENHANCER.** This is the next
  architecture topic the user wants to drill. The Enhancer is the **background synthesizer** that
  reads T2 and writes T3–T6; the design phase already pinned much of its *behaviour* — pull these
  together as the starting material:
  - **4-branch update logic** (D18-5): no-match→INSERT / exact→`support`++ / partial→LLM merge-split
    / contradiction→A/B; partial+contradiction both **A/B-replay against the no-delete T2**.
  - **Two-stage success gate** (D6-3): heuristic eligibility (terminal state / ReAct self-overturn /
    implicit user pushback) → recurrence aggregation + LLM **distill** (never "judge correctness").
  - **Cross-tier routing by subject** (D6-4): format→T3/T4, reasoning→T6, join→T5; **recurrence =
    universal noise filter**.
  - **One shared distiller**, writes the shared **base record** (D18-7), Enhancer-only write client
    on every persistent tier, runs **offline**.
  - Open Enhancer questions likely to surface: trigger/scheduling (when does it run), how clustering
    + recurrence threshold are actually computed, A/B replay cost (→ sampled replay, BACKLOG), LLM
    budget/prompt design for distillation, ordering of the per-tier passes.
- **Design phase status:** all six tiers locked (D11/D12/D14/D15/D16/D17) + cross-tier D18. No open
  *tier* drills remain; the Enhancer is the *cross-cutting mechanism* discussion, not a 7th tier.
- **STEP 3 (after the Enhancer discussion): coding — needs user go-ahead (workflow step 3).**
  - **B3** — scaffold `services/memory/` package + `ENABLE_MEMORY_*` config flags (default OFF).
  - **B4** — implement **Tier 2 episodic log** (JSONL behind `EpisodicLog`, dumb-capture, gitignored).
  Both need an approved TASKS.md breakdown before sub-agents dispatch.
- **Open non-coding item still pending:** user to **email the upstream author** re: `DocumentDB`
  local/global reuse (D13/D15) — draft at `docs_memory/_email-draft-upstream-author.md`. Affects
  only T4's *authored* backend (behind `OrgMemory`), so it does **not** block the Enhancer talk or B3/B4.
- Reference: `system_architecture.md` (6-tier spec) + `code-vs-6tier-mapping.md` (per-tier gap
  analysis + build order) + `BACKLOG.md` (deferred items) + each tier's `tierN-*-design.md` spec.

## How to resume (minimal prompt)
Type **`繼續`** (or `resume`). `CLAUDE.md` instructs me to read this file and pick up the
"Next action". Nothing else needed.
