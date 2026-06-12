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
| 5 — Schema routing memory | Persistent property graph: tables/cols as nodes, **validated join paths** as edges with `support` (evidential weight) + negative constraints | `join_paths` (string) and `ProvenanceGraph` (op DAG) | 🔴 |
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
(success **and** errors)*. JSON/JSONL. The Enhancer's input. *(The brief's "user feedback"
field is dropped — no explicit channel; inferred from the next turn, D17.)*

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

**Internal design — LOCKED (DECISIONS D12; full spec `tier2-episodic-log-design.md`).** The
authoritative design lives in those two; not duplicated here, to keep a single source of
truth. This section keeps only the code↔tier gap above (Spec / Code / Attach).

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

**Internal design — LOCKED (DECISIONS D13 direction → D14 lock; full spec
`tier3-user-memory-design.md`).** The authoritative design lives in those; not duplicated
here, to keep a single source of truth. This section keeps only the code↔tier gap above.

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

**Internal design — LOCKED (DECISIONS D13 direction → D15 lock; full spec
`tier4-org-memory-design.md`).** The authoritative design lives in those; not duplicated
here, to keep a single source of truth. Two-headed tier (authored authoritative KB +
learned org conventions); the still-OPEN `DocumentDB`-reuse question is parked in
`BACKLOG.md`. This section keeps only the code↔tier gap above (note the dormant `DocumentDB`
scaffold is the lowest-effort attach point).

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

**Why the gap matters (this is the "big difference" the user sensed):** Tier 5 wants a
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

**Internal design — LOCKED (DECISIONS D13 direction → D16 lock; full spec
`tier5-schema-graph-design.md`).** The authoritative design lives in those; not duplicated
here, to keep a single source of truth. Property graph (table/column nodes, column-level
join edges) behind a `SchemaGraph` interface, graph-first/heuristic-fallback read, organic
growth (no pre-built FK expansion), edge weight = `support` (see Glossary). This section
keeps only the code↔tier gap above (`join_paths` and `ProvenanceGraph` are **not** T5).

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

**Internal design — LOCKED (DECISIONS D13 direction → D17 lock → D18 refinement; full spec
`tier6-long-memory-design.md`). LAST TIER — all six locked + D18 cross-tier refinement.** The
authoritative design lives in those; not duplicated here, to keep a single source of truth.
Method-skeleton store (the *verb*, composes with T5's *noun*): **v1 = inject-whole `.md`** few-shot
exemplars + negative anti-patterns (NO embedding/vector DB — that is a Layer 1+ scale upgrade,
D18-4), weight = `support` (see Glossary), Enhancer-distilled behind a `LongMemory` interface,
inject-or-skip read (miss = today's static prompt, no regression). This section keeps only the
code↔tier gap above (static prompt factories are **not** T6).

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
