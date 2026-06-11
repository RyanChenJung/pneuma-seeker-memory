# Existing Code vs. 6-Tier Memory — Precise Mapping & Gap Analysis

> Purpose: honestly map what Pneuma-Seeker **already has** onto the
> [6-tier memory design](system_architecture.md), and call out the **subtle but
> consequential gaps**. The earlier "high overlap" summary was too generous; this
> document is the corrected, conservative version. Read the "Gap" rows carefully —
> several "analogues" are related in spirit but architecturally different.
>
> Legend for **Reuse rating**:
> - 🟢 *Reusable* — existing structure can be adopted nearly as-is.
> - 🟡 *Seam only* — there's an attachment point/scaffold, but no real substance.
> - 🔴 *Build new* — spirit-level resemblance at best; architecture differs enough that
>   "reuse" would mislead.

| Tier | Spec intent (1-line) | Closest existing code | Reuse |
|------|----------------------|------------------------|-------|
| 1 — Short-term reasoning buffer | **Curated salience "notebook"** — LLM judges which retrieved evidence / reasoning conclusions / user corrections matter, pins them, and re-reads them right before answering (defeats "lost in the middle"). Conversation-scoped. | `Conductor.llm_messages` is only the *raw* transcript (no curation, per-turn reset) | 🔴 |
| 2 — Episodic state log | Append-only full trace: thoughts, tool calls, SQL outcomes, **failures**, feedback | `chat_history` + `provenance_*` tables | 🔴 |
| 3 — User memory | Persona/constraints/habits, vector store | *(none)* | 🔴 |
| 4 — Organization memory | Clinical defs/guidelines, vector + doc store | `DocumentDB` retriever + `Knowledge` type + `indices/kb/{local,global}` | 🟡 |
| 5 — Schema routing memory | Persistent property graph: tables/cols as nodes, **validated join paths** as edges with utility scores + negative constraints | `join_paths` (string) and `ProvenanceGraph` (op DAG) | 🔴 |
| 6 — Long memory | Abstract procedural skills, few-shot template store | *(none; static prompt factories)* | 🔴 |
| Agents | Conductor/Retriever/Materializer/**Enhancer** with tiered R/W permissions | First three exist; no Enhancer, no permission model | 🟡 |

---

## Tier 1 — Short-Term Reasoning Buffer  🔴 (corrected — earlier "already exists" was wrong)

> Status: **understanding v1, confirmed with user 2026-06-09.** Earlier this doc rated
> Tier 1 🟢 ("≈ `llm_messages`"). That was wrong — see below.

**User's actual intent (the design we are building):**
- Within **one conversation** (the LLM/process is not restarted), context accumulates —
  not only the multi-turn user dialogue, but also the LLM's own ReAct / reasoning.
- **Problem being solved — "lost in the middle":** if we retrieve a key piece of evidence
  and it lands in the *middle* of the context window, it gets buried; the LLM tends to
  forget it, fails to use it as ground truth, and hallucination risk rises.
- **The mechanism:** a **short-memory notebook** (likely a Markdown doc). It is *not* the
  raw conversation. Instead, the LLM **judges** whether each retrieved datum / reasoning
  conclusion / user correction is genuinely useful for the current problem; if important,
  it is written into the notebook. **Before producing an answer, the LLM glances at the
  notebook** — exactly like a human taking notes on the side and consulting them when
  answering.
- **Injection model (user's analogy):** like `CLAUDE.md` / skills in Claude Code — a
  pinned, always-present context, re-surfaced every step, never buried in history.
- **Scope & reset:** conversation-scoped. When we move on to a *different problem / new
  conversation*, the notebook is no longer relevant, so it resets. (This is what "purge to
  prevent contamination" means here — not cross-session bleed, just "this conversation's
  notepad is done.")
- **Which agents:** the **Conductor** definitely has this notebook. Whether the
  **Materializer** also gets one is **OPEN** (Q2, undecided).

**What exists in code (and why it is NOT this):**
- `Conductor.llm_messages: list[LLMMessage]` is the **raw, unfiltered transcript** — it is
  *precisely the thing that suffers "lost in the middle."* It is not curated, not
  salience-filtered, and is reset **per turn** (narrower than conversation scope).
- `interaction_history` + persisted `chat_history` carry prior turns, but again as raw
  Q/A pairs, not a judged-importance notebook.
- So the **data shape** (a list/text blob) trivially exists, but the **valuable
  mechanism** — LLM-judged salience extraction + a persistent, pinned, re-read notebook —
  **does not exist**. Hence 🔴 build-new.

**Attach (provisional):** a new notebook store in `services/memory/`, written by an
LLM-judgment step hooked into the Conductor's ReAct loop (after retrieval / reasoning /
user-correction events), and **pinned into the system/env-state prompt** where
`Conductor.chat` assembles `get_sys_prompt()` / `get_env_state_prompt()` — so it sits at a
non-buried position every step. Internal structure of the notebook (Q5) is still to be
designed; recommendation pending once intent is fully locked.

**Open questions still in flight:** Q1 (shared definitions of "turn" vs "conversation" —
see DECISIONS glossary), Q2 (Materializer notebook yes/no), Q5 (notebook internal
structure — Claude to propose).

---

## Tier 2 — Episodic State Log  🔴 (the biggest "looks done but isn't" gap)

**Spec:** append-only **raw recording of the entire session** — user prompts,
*Conductor's internal thoughts (ReAct trace)*, *tool calls*, *SQL execution outcomes
(success **and** errors)*, *user feedback*. JSON/JSONL. The Enhancer's input.

**Code — what actually gets persisted (`PneumaDB.persist_session`):**
- `chat_history`: only `(role, content)` for the **user input** and the **final
  assistant response**. Nothing in between.
- `provenance_nodes/edges`: the **successful** materialization steps, as runnable code.
- `conductor_state`: the final `(T, S)` + flags + `join_paths`.

**Why this is NOT Tier 2 (three real gaps):**
1. **No trajectory.** The ReAct loop (each planned action, its args, its outcome
   message, the LLM's reasoning) lives only in the in-memory `llm_messages` and the
   `formatted_log` text logs — **neither is persisted in a queryable form**. The DB
   keeps the *destination*, not the *journey*.
2. **Failures are dropped.** The spec explicitly wants "instructive failure
   trajectories" (errors, dead-ends, retries). The provenance graph is a "what worked"
   DAG; `reset_materialization_nodes()` and per-turn resets actively *discard* failed
   attempts. The single most valuable Enhancer signal is largely **not recorded**.
3. **Not append-only by default.** With `ENABLE_FINE_GRAINED_STATE_CHANGE_TRACKING=false`
   (the default), `persist_session` **deletes** prior `documents`, `provenance_*`,
   `conductor_state` rows before inserting — keep-latest, not append.

**Implication:** Tier 2 is mostly **new instrumentation work**: structured logging of the
Conductor/Materializer loops (action, args, result, error, tokens, timing, feedback) to
an append-only JSONL/table. The existing `chat_history`/provenance are a *thin* subset.
*Do not* assume the Enhancer can run on current persistence — it can't see failures or
reasoning.

**Attach:** new append-only episodic store (ours), written by a hook inside the
existing ReAct loops (Tier 🟡 seam edits in `conductor/main.py` & `materializer/main.py`).

**Decided (v1) — LOCKED 2026-06-10 (DECISIONS D12):**
- **Dumb capture, zero extra LLM** at write time (Pneuma latency is already high). Tier 2
  just serializes the ReAct trajectory (already in `llm_messages`) before it's GC'd; all
  condensing is the async Enhancer's job. Contrast Tier 1, which is LLM-*curated*.
- **Own store** at `services/memory/_episodic/` (gitignored), **not** in upstream `ws.db`
  — because `persist_session` is delete-and-replace (`db/main.py:592-595`), which clashes
  with append-only, and ws.db is upstream-owned + per-conversation.
- **Backend:** v1 = **JSONL** behind an `EpisodicLog` interface (`append`/`iter`/
  `mark_processed`). **Upgrade path = DuckDB table** (reuse existing stack; can attach
  Postgres) — Conductor unchanged.
- **Granularity:** **step-level full trajectory** incl. failures + raw CoT (free on the LLM
  axis). Turn envelope + step-event stream; field set chosen by backward-reasoning from what
  Tiers 3/4/5/6 need the Enhancer to distill.
- **Lifecycle:** append-only, survives session, `processed_at` watermark; **cleanup policy
  deferred** (keep-forever vs TTL decided later, doesn't block schema).
- Provenance graph is **referenced, not reused** as Tier 2 (it's a success-only DAG).

---

## Tier 3 — User Memory  🔴

**Spec:** persona constraints + inquiry habits, vector store, accelerates "latent intent
convergence."

**Code:** none. `interaction_history` is transient (rebuilt each call from message
history). There is no user profile, no per-user persistent store, no semantic recall of
"how this user tends to ask."

**Attach:** entirely new, in `services/memory/`. Read path: inject a compact user-profile
summary into the Conductor env-state prompt. Write path: Enhancer derives habits from the
episodic log keyed by `user_id` (which already flows through every layer).

**Decided (direction) — 2026-06-10 (DECISIONS D13):**
- **MVP = single-user.** Build for one user first, but keep `user_id` as the scope key and
  wrap the store in an interface, so the multi-user upgrade (a company DB keyed by
  `user_id`) is a **backend swap, not a redesign**. Same interface-first pattern as D11/D12.

**LOCKED v1 — 2026-06-10 (DECISIONS D14; full spec `tier3-user-memory-design.md`):**
- **Two content sources:** (A) **Provisioned** = declared identity (role/grade/department/
  clinical/location), v1 a **manually-filled file** (HR feed deferred); (B) **Learned** =
  Enhancer-distilled from this user's Tier 2 (alias map, focus range, standing corrections,
  format prefs).
- **Focus range = derived, not typed** — Enhancer tallies a frequency distribution over the
  schema elements/concepts the user touches (rejected a hand-typed free-text line as
  unscalable). This is the single-user **seed** of the BACKLOG "user-similarity space /
  emergent departments" idea (which refines D13: org scope may be soft overlapping clusters,
  not a hard hierarchy; `department` label = weak prior only).
- **Authorization deferred** (→ BACKLOG): T3 stores where the user *focuses*, never what
  they're *permitted* to see; enforcement stays at the execution layer.
- **T3 ↔ T4 corrected:** two distinct tiers (owner/authority/subject differ); they only
  share the overlay *injection* mechanism (`institution → department → user`), NOT "T3 ⊂ T4".
  The T1→T3→T4 promotion ladder applies only to generalizable learned conventions, gated by
  content-kind.
- **Read:** inject whole (small) block into Conductor env-state, no runtime summarization.
  **Write:** async Enhancer, recurrence threshold, rewritable living doc (last-write-wins +
  `last_seen`). **Backend:** one file/user behind a `UserMemory` interface; vector + multi-
  user = deferred swaps.

---

## Tier 4 — Organization Memory  🟡 (strongest existing scaffold — corrects my earlier under-rating)

**Spec:** clinical definitions, guidelines, hospital protocols; vector + document store;
provides "contextual priors."

**Code — real, but dormant:**
- A whole retriever exists: `DocumentDB` (`RetrieverType.DOCUMENT_DB`,
  `ir_system/retriever/impl/document_db.py`), backed by BM25 indices at
  `indices/kb/local` and `indices/kb/global` — and that **local/global split mirrors the
  spec's user-vs-organization distinction**.
- A document type exists: `Knowledge` (`schemas/core/ir_system.py`), which `DocumentDB`
  validates against. Its docstring even describes `metadata {"type": "local/global", "user": ...}`.

**Subtle gaps:**
1. **Dormant / unwired.** `DOCUMENT_DB` is **not** in `valid_conductor_actions` or
   `valid_materializer_actions`, so neither agent can call it today. The `IndexingService`
   never populates the KB indices. It's a built scaffold with no content and no caller.
2. **Lexical only.** It's BM25 (full-text), not the spec's vector/semantic store. Fine as
   a start, but "vector DB for semantic retrieval" would need adding embeddings.
3. **No governance.** No notion of authoritative protocols, versioning, or trust.

**Attach:** this is the **lowest-effort tier to light up** — populate `indices/kb/*`,
re-enable the `DOCUMENT_DB` action behind a flag, and (optionally) back it with vectors.
Most of the plumbing already exists.

**Decided (direction) — 2026-06-10 (DECISIONS D13):**
- **Content filter = actionability, not breadth.** Store specific, groundable facts
  ("in Admissions, 'matriculant' means X"), not vague descriptions ("UChicago is a
  university"). A broad org scope is fine; vague content is not.
- **Scope is a HIERARCHY, not flat:** `User → Department (local-org) → Institution
  (global-org)`, retrieved as a **layered overlay** (Claude Code's CLAUDE.md global+project
  model: broad base, narrower scope augments/overrides). Heterogeneous departments ⇒ the
  institution layer is naturally *thin*; actionable mass concentrates at the department
  layer automatically.
- **Scalability (resolves the "redesign per department?" worry): NO.** Build the *mechanism*
  (scope hierarchy + Enhancer promotion + overlay retrieval) **once**; each scope's *content*
  is **auto-learned** by the Enhancer from its users' Tier 2 logs. New department = new
  auto-filled bucket, zero redesign. Two-stage convergence: commonality within a department
  (→ local-org), then promote across departments (local-org → global-org) when a lesson
  recurs; too-specific lessons stay local. Same machinery gives the user→org convergence
  that lets a new user benefit from accumulated shared knowledge on day 1.
- **OPEN (pending email to upstream author):** whether to **reuse the author's `DocumentDB`/
  `Knowledge` (local/global) design and attach our memory interface there** (working
  assumption: local≈Tier 3, global≈Tier 4) vs build our own. Don't rebuild the wheel until
  we hear back.

**LOCKED (internal design) — 2026-06-10 (DECISIONS D15), full spec `tier4-org-memory-design.md`:**
- **Two-headed tier.** (A) **Authored** authoritative knowledge base (externally ingested,
  NOT from Tier 2 / Enhancer — the heavy main body, the reason `DocumentDB` exists) + (B)
  **Learned** org conventions (Enhancer-distilled from *aggregated* Tier 2). Refines D13's
  "all tiers Enhancer-written from T2": T4's authored side breaks that by design.
- **Authority/trust = T4-unique.** Authored = authoritative & **always wins**; learned =
  heuristic, may only **supplement, never override** authored. Both injected labelled with
  provenance + trust level. Versioning/sign-off = thin metadata v1; full governance → BACKLOG.
- **Promotion ladder: only (B) learned promotes** (T1→T3→T4-dept→T4-institution), gated by
  recurrence N + content-kind. (A) authored never promotes (already authoritatively placed).
- **Read = split by head, one facade.** Learned → **inject whole** (joins D14's
  `institution→department→user` overlay); authored → **retrieve top-k** (Retriever → Tier 1
  buffer). One **`OrgMemory` facade**: `get_org_overlay(scope)` + `search_authored(query,
  scope)`, `scope=(institution, department)`. Authored backend hidden behind facade (our own
  vs reused `DocumentDB` = the OPEN email question; interface-first → not blocking).
- **MVP scope = single institution + single department; NEAR-TERM (not backlog) = ≥2
  departments** to test the core claim: different departments, same question → each converges
  to its own correct latent intent. MVP **does seed a small real authored set** (differing
  per-department definitions are the likely convergence variable).

---

## Tier 5 — Schema Routing Memory  🔴 (CRITICAL tier, and the most misleading "overlap")

**Spec:** a **persistent property graph** that *patches messy EHR schemas*:
- Nodes = physical tables and columns.
- Edges = **validated SQL join paths**.
- Edge payload = `Empirical_Utility_Score` (reliability weight) + `Associated_Experience`
  (tribal knowledge / **negative constraints**, e.g. *"don't join on `id`, use
  `patient_id`; failed log #123"*).
- Purpose: turn blind schema inference into high-confidence graph retrieval.

**Two things in the code look related — neither is this:**

1. **`join_paths`** (`JoinPathExtraction.discover_join_paths`, surfaced as
   `Conductor.join_paths: str`):
   - A **heuristic, ephemeral string**. Computed each retrieval from column-name
     similarity (Damerau–Levenshtein) + value overlap over the *currently retrieved*
     tables.
   - Persisted only as a text blob on `conductor_state.join_paths`; **recomputed**, not
     accumulated. No utility scores. No record of what actually *worked* vs failed. No
     negative constraints. Not a graph.

2. **`ProvenanceGraph`** (`provenance/graph.py`):
   - A **per-session DAG of operations** (nodes = code transformations; edges = data
     flow). It answers "how was *this* result built," and renders to runnable `.py`.
   - It is **operation-level, not entity-level** (nodes aren't tables/columns), **single-
     session** (reset between materializations), and carries **no utility/experience
     payload**.

**Why the gap matters (this is the "差很多" the user sensed):** Tier 5 wants a
*cross-session, persistent, table/column-level* graph whose edges accumulate empirical
reliability and human-readable failure lessons. The provenance graph is a *per-session,
operation-level* lineage DAG; `join_paths` is *throwaway heuristic text*. Spirit overlaps
(both concern joins/structure), but data model, lifetime, granularity, and payload all
differ. Building Tier 5 by "extending the provenance graph" would fight its design.

**Attach:** a **new persistent graph** (NetworkX/JSON or a graph store) in
`services/memory/`. It can be *fed* by the episodic log (Tier 2): every executed join in
the trace → reinforce/penalize an edge; failures → append a negative constraint. Read path:
the Materializer consults it before choosing joins. This is the highest-value, highest-
effort tier.

**Decided (direction) — 2026-06-10 (DECISIONS D13):**
- **Property graph is the right backbone** (joins *are* a graph; path queries beat a flat
  rule list / vector store). Nodes = tables/columns; edges = validated join paths carrying
  `utility_score` + `associated_experience` (incl. negative constraints).
- **Node annotations are first-class too, not only edges:** column-level value/temporal
  caveats ("pre-2000 vs post-2000 encoding differs") live on **nodes**, not on joins.
- **Infra (same pattern as D11/D12):** v1 = **NetworkX + JSON persistence** behind a
  `SchemaGraph` interface in `services/memory/` (gitignored); **NOT** Neo4j yet (too heavy).
  Upgrade path = a real graph DB, backend swap only.
- **Learn-by-correction loop:** user corrections land in Tier 2 → the Enhancer distills them
  into an edge or node annotation. No pre-built templates; the graph grows from usage, and
  only join paths actually used/corrected get reinforced (so we never pre-map a giant schema).

**Decided (internal) — 2026-06-11 (DECISIONS D16, LOCKED). Full spec:
`tier5-schema-graph-design.md`.**
- **Data model:** two node types (`table`, `column`); `column` hangs off `table` via a
  `contains` edge; **join edges connect two `column` nodes** (joins are column-level). Node
  payload = value/temporal caveats; edge payload = join utility + failure lessons.
- **Payload:** edge = `utility_score`, `success_count`/`fail_count`, `negative_constraints[]`,
  `last_seen`; column node = `value_caveats[]` / `temporal_caveats[]`. Every learned item
  carries `source_episode` = a **Tier 2 episode id as a SOFT back-pointer** (audit/reversibility,
  not a hard FK); distilled lessons are self-contained → **no retention lock on T2**, decoupled
  from the T2 delete/keep decision. *(User leaning toward T2 = no-delete as of 2026-06-11 — a
  lean, not locked; T5 unaffected either way.)*
- **`SchemaGraph` interface:** read (frontline RO) `get_join_path` / `get_column_caveats`;
  write (**Enhancer only**) `reinforce_edge` / `penalize_edge(…, lesson, source_episode)` /
  `annotate_node(…, caveat, source_episode)`. Permission = **two different clients** (RO vs
  write), not self-discipline — realises "only Enhancer writes persistent memory".
- **Read path = graph-first, heuristic fallback:** graph is a high-confidence empirical cache
  in front of the existing dumb `join_paths` heuristic. Hit → use validated edge + inject its
  caveats; miss/cold → fall back to today's heuristic (**no regression**); corrected heuristic
  joins get written back → graph hits next time.
- **Organic growth, no pre-build:** do **NOT** auto-expand declared FKs (a declared FK is
  intent, not a guarantee — dirty EHR joins routinely fail). Only joins actually used/corrected
  get edges; negative constraints distilled from **Tier 2 failure steps**.
- **Node keying:** v1 = fully-qualified `schema.table.column`; cross-session persistence by key
  match. Table/column rename → old node **orphaned** (relearn from zero; degraded, never wrong);
  schema-drift aliasing deferred → BACKLOG (a *table* alias, distinct from T3's *person* alias).
- **T4/T5 boundary sharpened:** authored (T4) = authoritative org norms/definitions only; **all
  empirical join knowledge = T5, evidence-first**; a declared FK in an authored data dictionary
  does **not** seed T5.
- **Backend:** NetworkX + JSON behind `SchemaGraph`, gitignored; Neo4j = deferred swap.

---

## Tier 6 — Long Memory  🔴

**Spec:** abstract procedural skills + reasoning strategies; vector store for few-shot
prompt injection; reduces reasoning latency by reusing successful templates.

**Code:** none. Prompt factories (`*/prompt_factory*.py`) are **static**; there is no
mechanism to retrieve and inject past successful plans as exemplars. (`get_graph_code()`
emits reusable Python for one result, but it isn't abstracted into a skill or retrieved.)

**Attach:** new skill store in `services/memory/`. Enhancer abstracts successful
trajectories (from Tier 2) into templates; read path injects top-k exemplars into the
Conductor/Materializer planning prompts.

**Decided (direction) — 2026-06-10 (DECISIONS D13):**
- **Verb vs noun split from Tier 5:** Tier 6 = the *method skeleton* (how to solve a
  *class* of problem, DB-agnostic, e.g. "cohort → index date → outcome window → aggregate");
  Tier 5 = the *navigation* (how to read *this* DB). They compose: T6 supplies the plan
  shape, T5 grounds it to physical tables.
- **v1 = trajectory-RAG** (retrieve the most-similar past *successful* trajectory, inject as
  a few-shot worked example) — concrete, needs no perfect abstraction, still useful.
- **v2 = abstracted, parameterized plan templates** keyed by problem-type (the spec's
  "abstract procedural skills"). The abstraction is the Enhancer's hardest LLM-as-judge job;
  deferred so T6 doesn't stall on it.
- **Risk noted:** if entries aren't abstracted, T6 collapses into a cache of past SQL and
  adds little over T5+T2. v1 mitigates by being explicitly few-shot, not a query cache.

---

## Agents & Permissions  🟡

**Spec:** four agents — Conductor, Retriever, Materializer, **Enhancer** — with strict
tiered R/W (e.g., frontline agents read-only on persistent memory; only Enhancer writes;
Enhancer runs offline).

**Code:** Conductor, Retriever (the IR `Retriever`), and Materializer exist as classes,
but:
- **No Enhancer** at all (no offline consolidation process).
- **No permission model** — the agents share `DBAPI`/`LanguageModelAPI` freely; nothing
  enforces "read-only on memory."
- The current "Retriever" is an *IR/table* retriever, not a *memory* retriever — same word,
  different job. Watch the naming collision.

**Attach:** Enhancer is a new offline component (a script/job consuming the Tier 2 log).
The permission model can be enforced simply by giving frontline agents a read-only memory
client and the Enhancer the only writable one.

---

## Bottom line

- **Genuinely reusable today:** Tier 1 (data shape) and Tier 4 (a whole dormant
  `DocumentDB` + `Knowledge` + local/global KB scaffold — light it up).
- **Looks reusable but isn't (verify before relying):** Tier 2 (persistence captures the
  destination, not the journey, and drops failures) and Tier 5 (`join_paths`/provenance
  are *not* a persistent scored schema graph).
- **Net-new:** Tiers 3 and 6, the Enhancer, the permission model, and — critically — the
  **append-only episodic log** that everything else feeds on.
- **Build order this implies:** Tier 2 (episodic log) is the foundation — without it, the
  Enhancer has nothing to learn from, and Tiers 3/5/6 have no write path. Start there.
