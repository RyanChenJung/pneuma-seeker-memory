# Decision Log — Memory Layer Project

> Settled conclusions. The point of this file: **conclusions live here, not in the
> chat context** — so they survive across sessions and the user never has to re-explain.
> Append new decisions; supersede old ones explicitly (don't silently edit history).
> Format: `Dn — <decision>` + rationale. Cross-refs: [`CLAUDE.md`](../CLAUDE.md),
> [`TASKS.md`](TASKS.md), [`code-vs-6tier-mapping.md`](code-vs-6tier-mapping.md).

## D1 — Never push / PR to upstream (`TheDataStation/pneuma-seeker`)
This repo is a fork. All work targets `origin` (`RyanChenJung/pneuma-seeker-memory`),
base branch `prod`.
- Guardrails applied: `upstream` push URL = `DISABLE`; `remote.pushDefault = origin`.
- `gh` is now installed (v2.93.0). One-time `gh auth login` still needed; then
  `gh repo set-default RyanChenJung/pneuma-seeker-memory`. **Preferred PR path going
  forward:** the agent runs `gh pr create --repo RyanChenJung/pneuma-seeker-memory
  --base prod ...` — the explicit `--repo` means it can never target upstream — replacing
  manual GUI/web PRs.
- The earlier accidental upstream PR was made manually via github.com (the web UI
  defaults the base to the fork parent).
- **Standing rule:** any PR via a GUI/web tool — verify the base repo reads
  `RyanChenJung/pneuma-seeker-memory`, never `TheDataStation/...`. Prefer `gh` with an
  explicit `--repo` to sidestep the issue entirely.

## D2 — We are a plugin; minimize edits to upstream code
Ownership tiers (full detail in `CLAUDE.md`): 🟢 ours (`docs_memory/`,
`services/memory/`, `tests/memory/`) · 🟡 surgical+flagged (`conductor/`, `ir_system/`,
`services/db/main.py`, `shared/config.py`, `main.py`) · 🔴 never touch (`docs/`,
`README`, `LICENSE`, `baselines/`, upstream `data_src/`).

## D3 — Memory code location
`src/pneuma_seeker/services/memory/` (sibling of `core/`, `db/`, `indexing/`).

## D4 — Docs layout
`docs/` stays 100% upstream's (untouched). Our docs live in `docs_memory/`:
`codebase-map.md` (existing-system reference), `system_architecture.md` (6-tier design),
`code-vs-6tier-mapping.md` (gap analysis), `TASKS.md`, this file.

## D5 — Workflow
Goal → I decompose into ledger tasks → **user approves (single human gate)** →
multi-agent implementation (parallel, isolated worktrees) → I aggregate + run tests +
surface only decisions/problems → one small commit per task, fork branch only.
`docs_memory/TASKS.md` is the single source of truth for task state.

## D6 — md management
Global `~/.claude/CLAUDE.md` untouched. A project `CLAUDE.md` at repo root (committed to
the fork) carries operating rules; Claude Code *layers* it on the global, never overrides.

## D7 — Sequencing: understanding first (path A)
Before any memory coding, build understanding. Immediate work = finish the
`docs_understanding/` HTML (the user's reading artifact). This also serves as the first
run through the multi-agent workflow (low risk, parallelizable, no upstream code touched).

## Glossary — shared vocabulary (so we stop talking past each other)
Pinned definitions, grounded in the code. Use these terms consistently.
- **Turn (一輪)** = one user message → one final system answer. In code = one
  `Conductor.chat()` call. The *entire* ReAct loop (up to `MAX_CONDUCTOR_STEPS`) happens
  **inside one turn**. `Conductor.llm_messages` is reset at the **start of each turn**.
- **Conversation / Session (整段對話 / 一個對話框)** = the whole thread in one chat box,
  keyed by `(user_id, chat_id)`, spanning **many turns**, for as long as the process/LLM
  is not restarted. In code = one `ChatSession`, persisted in one `ws.db`. The 6-tier
  spec's word "session" = **this** (a conversation), not a single turn.
- **Materialization run** = one `Materializer.materialize_T()` call, nested *inside* a
  turn; has its own separate buffer.
- Convention: we say **"turn"** for 一輪 and **"conversation"** (or session) for the whole
  chat box. The Tier 1 notebook lives at **conversation** scope and resets on a new
  conversation/problem.

## D9 — Tier 1 = a curated salience "notebook", NOT the raw transcript
(Confirmed with user 2026-06-09. Supersedes the earlier wrong claim that Tier 1 already
exists as `Conductor.llm_messages`.)
- **Purpose:** counter "lost in the middle." Key evidence retrieved mid-context gets
  buried and forgotten, raising hallucination. Tier 1 keeps the important bits at hand.
- **Mechanism:** an LLM-judged notebook (likely Markdown). The LLM decides whether a
  retrieved datum / a reasoning conclusion / a user correction is *important*; if so it's
  written to the notebook. **Before answering, the LLM re-reads the notebook** (human
  taking notes → consulting them).
- **Injection:** pinned like `CLAUDE.md`/skills in Claude Code — always present, never
  buried; re-surfaced every step (attach where the Conductor builds its system/env-state
  prompt).
- **Scope/reset:** conversation-scoped; resets on a new conversation/problem.
- **Agents:** Conductor = yes (definite). Materializer = **OPEN** (Q2).
- **Existing code:** only the *raw* buffer exists (the very thing that gets buried); the
  curation + pinned re-read mechanism is **new** (rated 🔴 in the mapping doc).
- **Still open:** Q5 (notebook internal structure) — Claude to propose a design once
  intent is fully locked.

## D8 — The 6-tier mapping is provisional and will be refined tier-by-tier
`code-vs-6tier-mapping.md` is a first pass; the user found it not precise enough because
the 6-tier intent wasn't fully conveyed. We will go **tier by tier**: I elaborate the
similarities I see, the user corrects/adds concepts, I record the agreed version into the
mapping doc (and key conclusions here). Current ratings (Tier 2 & 5 = build-new, Tier 4 =
strongest existing scaffold) are **subject to revision** after that discussion.

## D10 — Traditional-Chinese files are git-ignored (not committed)
Per user convention, Traditional-Chinese content stays out of git. Concretely,
`docs_understanding/` (the zh-Hant HTML understanding docs + its `CHECKPOINT.md`) is
ignored via `.git/info/exclude` (local — so it does **not** modify upstream's tracked
`.gitignore`). The committed project record is the **English** `docs_memory/` set +
`CLAUDE.md`. Implication: the HTML is personal/regenerable, lives only on local disk, is
NOT in git, and must not be relied on for handoff. (When writing new files, English →
`docs_memory/` and commit; Traditional-Chinese reading aids → `docs_understanding/`, local
only.)

## D11 — Tier 1 notebook v1: ephemeral .md behind a `Notebook` interface
Decisions (a)–(d) for the Tier 1 short-memory notebook are LOCKED (2026-06-10; full spec
in `tier1-short-memory-design.md`). Key points: **(a)** LLM writes via a lightweight
`note` action; **(b)** storage is **ephemeral/use-and-discard** — one `.md` per
conversation in a **gitignored** scratch dir `services/memory/_notebooks/`, accessed only
through a small `Notebook` interface (`append`/`read_all`/`clear`) so the backend is
hidden; **(c)** pinned at the **end** of the assembled prompt; **(d)** soft cap ~30
entries + dedup + supersede. The `.md` is a local debugging window, NOT a persistent
asset — cross-conversation reuse is Tier 3/6's job, not Tier 1's. **Upgrade path
(deferred, cheap because of the interface):** swap backend to a `ws.db` table keyed by
`(user_id, chat_id)`; Conductor code unchanged.

## D12 — Tier 2 episodic log v1: our own append-only JSONL store, dumb-capture, async-consumed
Tier 2 design LOCKED (2026-06-10, decisions (1)–(4) confirmed with user). Full spec:
`tier2-episodic-log-design.md`. Tier 2 = the
append-only **episodic state log** — the "messy raw-material warehouse" the Enhancer later
distills into the persistent tiers (3–6). In Bayesian terms: **Tier 2 is the likelihood
data; the Enhancer computes the posterior that becomes Tiers 4–6's priors** (which then
accelerate latent-intent convergence). Key points:

- **Character (vs Tier 1):** Tier 1 is LLM-*curated* (has a brain, online, consumed now by
  the Conductor). Tier 2 is **dumb capture** — records *everything* (incl. failures), and
  the write path uses **ZERO extra LLM calls** (hard constraint: Pneuma latency is already
  high from the long ReAct chain). The ReAct reasoning text already lives in
  `llm_messages`; Tier 2 just **serializes it before it's GC'd**. All "intelligence"
  (summarizing/condensing) is deferred to the async Enhancer. See [[tier-2-episodic-log]].
- **(1) Lifecycle:** **append-only**, must **survive the session** (session-purge is ruled
  out by definition — Tier 1 purges, Tier 2 is saved & consumed async). Schema carries a
  `processed_at` watermark (how far the Enhancer has consumed). **Cleanup policy is
  deferred** — it's a cron/ops concern that doesn't block the schema, and the interface
  wrapper lets us pick "keep-forever (event-sourcing replay) vs TTL (e.g. 24h floor, tied
  to Enhancer-processed) vs purge-after-distill" later without touching the Conductor.
- **(2) Backend:** our **own store** in `services/memory/_episodic/` (gitignored, mirrors
  Tier 1's `_notebooks/`), **NOT** in upstream's `ws.db`. v1 = **JSONL** behind a small
  `EpisodicLog` interface (`append` / `iter` / `mark_processed`). **Recorded upgrade path
  (per user request): swap the JSONL backend to a DuckDB table** — reuse the existing stack
  (ws.db is already DuckDB; DuckDB can even attach Postgres, `db/main.py:404`), Conductor
  code unchanged. SQLite (Hermes-style) is rejected: DuckDB already occupies that niche.
  Markdown (Kairos-style) is rejected: Tier 2 is high-volume machine-read, wrong shape.
- **Why NOT in ws.db (user's pollution concern, confirmed valid):** (i) ws.db schema is
  upstream-owned (🟡); (ii) per-conversation files force the Enhancer to crawl many files;
  (iii) decisive — `persist_session` is **delete-and-replace** (`DELETE` rows,
  `db/main.py:592-595`), which directly contradicts our **append-only** semantics. Reuse
  the DuckDB *technology*, not the ws.db *file*.
- **(3) Granularity:** **step-level full trajectory** (incl. failures + raw CoT). This is
  *free on the LLM axis* — the data already exists in memory; only cost is disk + a clean
  schema. Shape = **turn envelope** (`user_id`, prompt, final answer, user feedback,
  timing, tokens) + **step event stream** (`{turn_id, step_idx, phase[conductor/
  materializer], action, args, status, payload/error, sql?, retrieved_ids?, latency, ts}`).
  Raw CoT is stored as-is (cheap bytes); any summarization is the Enhancer's job. **Field
  set is decided by backward-reasoning from what each downstream tier needs** (Tier 3:
  `user_id`+question+role; Tier 5: per-join success/failure+error+SQL; Tier 6: full
  *successful* trajectories; Tier 4: question text+domain). (4) User OK'd storing failures
  + raw CoT — nothing excluded.
- **Provenance graph is NOT reused as Tier 2:** provenance is a success-only "what worked"
  DAG of runnable code that gets `reset_materialization_nodes()`'d; Tier 2 needs exactly the
  failures/reasoning/append-only it drops. Tier 2 may **reference** a provenance snapshot,
  but is not provenance.
- **Write path:** a hook inside the Conductor/Materializer ReAct loops (🟡 surgical,
  additive, behind `ENABLE_MEMORY_*`, default off) → a single call into our `EpisodicLog`.
- **Deferred (noted):** Enhancer trigger mechanism — explicitly out of scope for now, but
  flagged because *how/when it runs* feeds back into the retention policy + watermark
  semantics.

## D13 — Big-picture / boundary alignment across Tiers 3–6 (the persistent layer)
Boundary pass done 2026-06-10 (per-tier "Decided (direction)" blocks added to
`code-vs-6tier-mapping.md`). **Unifying frame:** Tiers 3–6 are all **persistent priors**,
**written only by the Enhancer**, read-only to frontline agents, all distilled from the
Tier 2 episodic log (Tier 2 = likelihood data; Enhancer = posterior → these tiers' priors).
What distinguishes them is **what they store / their scope key / which frontline decision
they feed** — NOT the mechanism (which is shared). Agreed points:

- **Scope key = the dimension a tier is indexed by** (T3: `user_id`; T4: org scope; T5: DB
  schema; T6: problem-type). Plain meaning: "this memory is about whom / about what."
- **MVP = single-user (T3).** Build single-user first; keep `user_id` as the scope key and
  wrap the store in an interface, so the company-DB / multi-user version is a **backend
  swap**, not a redesign. Same interface-first pattern as D11/D12.
- **Org (T4) is a SCOPE HIERARCHY, overlay-style — not flat:** `User → Department
  (local-org) → Institution (global-org)`, retrieved like Claude Code's CLAUDE.md (global
  base + project override/augment: broad layer is the base, narrower scope augments/
  overrides). Content filter = **actionability, not breadth** (store "in Admissions a
  'matriculant' means X", not "UChicago is a university"). Heterogeneous departments ⇒ the
  institution layer is naturally **thin**; actionable mass concentrates at the department
  layer automatically (this dissolves the "broad info can't help reasoning" worry).
- **Scalability — answers "must we redesign Org per department?": NO.** Separate **building
  the mechanism** (scope hierarchy + Enhancer promotion + overlay retrieval — built **once**,
  department-agnostic) from **filling the content** (each scope's content is **auto-learned**
  by the Enhancer from its users' Tier 2 logs). A new department = a new **auto-filled
  bucket**, zero redesign. Two-stage convergence: Enhancer finds commonality **within** a
  department (→ local-org), then promotes a lesson **across** departments (local-org →
  global-org) when it recurs; too-specific lessons stay local. This is also the user→org
  convergence that lets a brand-new user benefit from accumulated shared knowledge on day 1.
  (Tier 5 grows the same way — only join paths actually used/corrected get reinforced, so we
  never pre-map a giant schema.)
- **T4 vs T5 boundary:** T4 = **meaning / institutional rules**; T5 = **physical DB
  navigation**. Provenance-assisted; a user correction routes to T4 or T5 by its *subject*,
  not its source. (e.g. "pre-2000 vs post-2000 encoding differs" = physical ⇒ T5.)
- **T5 = property graph** (NetworkX/JSON v1 behind a `SchemaGraph` interface, D11/D12
  pattern; **nodes AND edges both carry payload** — node = column value/temporal caveats,
  edge = validated joins + utility + negative constraints), grown by **learn-by-correction**
  via Tier 2 → Enhancer. Not Neo4j yet (too heavy); graph DB = deferred backend swap.
- **T6 = method skeleton** (the *verb*: how to solve a *class* of problem, DB-agnostic) vs
  **T5's navigation** (the *noun*: how to read *this* DB); they compose. **v1 =
  trajectory-RAG** (retrieve most-similar past *successful* trajectory as a few-shot
  example); **v2 = abstracted parameterized templates**. Risk: un-abstracted T6 collapses
  into a SQL cache; v1 mitigates by being explicitly few-shot.

**OPEN (NOT locked):**
- (pt 2) Whether to **reuse the upstream author's `DocumentDB` / `Knowledge` (local/global)
  design and attach our memory interface there** vs build our own. **User will email the
  upstream author** to avoid rebuilding the wheel. Working assumption until then:
  `local ≈ Tier 3`, `global ≈ Tier 4`.
- Exact **number of scope levels** + **overlay precedence rules** — provisional; refine when
  we drill T3/T4 in detail and after the author's reply.

## D14 — Tier 3 (User Memory) internal design LOCKED
Drill-down done 2026-06-10. Full spec: `tier3-user-memory-design.md`. Anchored on D11/D12
(interface-first, gitignored local store, dumb-first) and D13 (persistent priors,
Enhancer-only-write, scope key = `user_id`, MVP single-user). Locked points:

- **Purpose:** a persistent prior *about a specific person* that accelerates latent intent
  convergence. Read-only to frontline; Enhancer-written (+ a manual provisioned file in v1).
- **Two content sources.** (A) **Provisioned** — declared identity (role, seniority/grade,
  department, clinical-or-not, location); NOT learned; v1 = a **manually-filled file** (MVP
  is for testing; HR-system feed deferred → BACKLOG). (B) **Learned** — Enhancer-distilled
  from this user's Tier 2: term/alias map, **focus range**, standing corrections, format
  prefs.
- **Focus range = derived, not typed.** Rejected the earlier hand-typed "focus" free-text
  line (too manual, won't scale; "where does that line come from at scale?"). Instead the
  Enhancer **tallies a frequency distribution over the schema elements / concepts the user
  actually touches** (tables/columns, default filters, time windows). This is the
  single-user **seed** of the BACKLOG "user-similarity space / emergent departments" idea.
- **Excludes:** raw trajectories (→T2/T6), org-wide facts (→T4), physical schema (→T5).
  Governance line on demographic attributes used to shape answers.
- **Authorization deferred.** T3 v1 stores where the user *focuses* (for convergence), NEVER
  what they're *permitted* to see; real enforcement stays at the execution layer; a T3 cache
  is never a security source of truth. → BACKLOG.
- **T3 ↔ T4 (corrects D13's "T3 is a leaf of T4 overlay").** They are **two distinct
  tiers**, differing in **owner / authority / subject** (T3 = about a person, heuristic,
  non-authoritative; T4 = shared, authoritative, often externally-authored institutional
  truth). They only **share the overlay *injection* mechanism** at read time (compose
  read-only priors `institution → department → user`, narrowest augments/overrides) — that
  is cross-tier prompt composition, **not** "T3 ⊂ T4". The T1→T3→T4 promotion ladder applies
  **only to the thin slice of generalizable learned conventions**, gated by content-kind (a
  personal preference never promotes to an org rule). Most of T3 and most of T4 never
  overlap.
- **Read path:** profile is small → inject the whole T3 block into the Conductor env-state
  prompt (mini per-user CLAUDE.md); compression at write time, **no runtime summarization**.
- **Write path:** async/off-peak Enhancer; recurrence threshold N before a pattern enters
  the Learned profile; **rewritable living doc** (last-write-wins + `last_seen`; Enhancer has
  Write/Delete, unlike T2 append-only). Decay deferred.
- **v1 backend:** one structured file per user behind a **`UserMemory` interface**;
  gitignored local store; vector backend + multi-user company DB = deferred backend swaps.

**Refines D13:** org scope may be **soft, overlapping, multi-membership clusters** (emergent
from behavior), not a clean hard hierarchy; Provisioned `department` is only a weak prior.
Recorded in `BACKLOG.md` (verify in the multi-user phase).

**Process note:** opened `docs_memory/BACKLOG.md` — a registry of intentionally-deferred
*design items* (distinct from TASKS.md's unapproved-work backlog), each with a back-pointer.

## D15 — Tier 4 (Organization Memory) internal design LOCKED
Drill-down done 2026-06-10. Full spec: `tier4-org-memory-design.md`. Anchored on D13
(scope hierarchy, actionability filter, auto-fill mechanism) and D14 (T3↔T4 boundary:
owner/authority/subject differ, shared overlay-injection mechanism only). Locked points
(Q1–Q5 confirmed with user):

- **Q1 — T4 is a TWO-HEADED tier.** (A) **Authored knowledge base** — real clinical
  definitions / official protocols / data dictionaries / guidelines; **externally authored,
  ingested by a pipeline (human/HR/file import), NOT distilled from Tier 2, NOT written by
  the Enhancer**; this is the heavy main body and the reason upstream's `DocumentDB` exists.
  (B) **Learned org conventions** — cross-user org habits the Enhancer distills from
  **aggregated** Tier 2 (scope key = org, not user). This mirrors T3's Provisioned/Learned
  split, but T4's authored side is the *main mass* (T3's provisioned was a thin stub).
  **Refines D13's unifying frame:** D13 said "Tiers 3–6 are all Enhancer-written, all
  distilled from Tier 2" — T4's (A) authored side **breaks that** by design: T4 = a layer of
  *external authoritative truth* + a layer of *internally-learned convention*.
- **Q2 — Authority / trust is the T4-unique dimension (T3 has none).** Authored (A) is
  **authoritative**; learned (B) is **heuristic / non-authoritative**. Conflict rule:
  **authored always wins; learned may only *supplement*, never *override* authored.** At read
  time both are injected **labelled with provenance + trust level** so the Conductor knows
  which is a *rule* vs an *observed habit*. Governance (versioning, who-authored, sign-off) =
  a **thin metadata tag in v1**; real version-control / approval workflow → BACKLOG.
- **Q3 — Promotion ladder: only (B) learned participates.** The T1→T3→T4-department→
  T4-institution promotion ladder applies **only to learned conventions**; **(A) authored
  never promotes** (it is already authoritatively placed at a scope). Gate = recurrence
  threshold N + content-kind filter (a generalizable convention may promote; a personal
  preference / PII may not — per D14). Two-stage convergence per D13 (within-department →
  local-org; recurs across departments → global-org).
- **Q4 — MVP scope = single institution + single department, but the NEAR-TERM target is
  single-institution + MULTI-department (≥ 2 departments), NOT far backlog.** Rationale (user):
  the multi-department setup is what actually tests the core claim — **different departments
  asking the *same* question each converge to the *correct* (different) latent intent**. So we
  build the scope-hierarchy mechanism in the single-dept MVP, then jump straight to ≥2
  departments to prove the convergence. (The soft-overlapping-cluster refinement from D14
  stays BACKLOG — this is still the hard-hierarchy mechanism.)
- **Q5 — Read paths split by head; one facade.** The two heads have **different read modes**:
  (B) learned conventions are **small → injected whole**, joining D14's overlay composition
  (`institution → department → user`, narrowest augments/overrides); (A) authored is a
  **large corpus → retrieved top-k by query** (the Retriever pulls relevant slices into the
  Tier 1 buffer — matches the spec's "RETRIEVER injects high-value facts into Conductor's
  Tier 1 buffer"). **This refines D13/D14:** T4 read is NOT a single overlay injection —
  learned = overlay, authored = retrieval. **Interface = one `OrgMemory` facade** (Q5-ii = A)
  with two methods: `get_org_overlay(scope)` (learned, inject-whole) + `search_authored(query,
  scope)` (authored top-k); `scope = (institution, department)`. One facade (not two split
  interfaces) because: (i) concept alignment — one tier = one interface, like T1/T2/T3; (ii)
  the Q3 promotion ladder needs both heads under one roof (a strongly-recurring learned
  convention may one day be promoted into an authored draft). The authored-side backend is
  **hidden behind the facade** — our own store vs reusing upstream `DocumentDB` is the still-
  OPEN email question (D13); interface-first means the choice doesn't block us, only swaps the
  authored backend later.
  - **Q5-i — MVP DOES seed a small real authored set** (option b), not an empty pipeline,
    because the Q4 cross-department convergence test very likely hinges on **differing
    authored definitions per department** (e.g. Admissions' "matriculant" vs another dept's
    term); with no authored content the convergence difference may be untestable.
- **v1 backend:** `OrgMemory` facade over two stores — authored = document store
  (`indices/kb/*`, BM25 → vector deferred; possibly the reused `DocumentDB`), learned =
  structured overlay file (gitignored local, D11/D12 pattern). Vector backend + DocumentDB-
  reuse = deferred backend swaps (BACKLOG).

## D16 — Tier 5 (Schema Routing Memory / Schema Graph) internal design LOCKED
Drill-down done 2026-06-11. Full spec: `tier5-schema-graph-design.md`. Anchored on D13
(T5 = property graph, NetworkX/JSON behind `SchemaGraph`, learn-by-correction, T4/T5 = meaning
vs physical-navigation boundary) and D11/D12 (interface-first, gitignored store, dumb-first).
Locked points (D5-1 … D5-6 confirmed with user):

- **D5-1 — Data model.** Two node types (`table`, `column`); `column` attaches to `table` via
  a `contains` edge; **join edges connect two `column` nodes** (joins are column-level). Node
  payload = value/temporal caveats; edge payload = join utility + failure lessons.
- **D5-2 — Payload + provenance.** Edge: `utility_score`, `success_count`/`fail_count`,
  `negative_constraints[]` (`{lesson, source_episode}`), `last_seen`. Column node:
  `value_caveats[]` / `temporal_caveats[]` (`{caveat, source_episode}`). Every learned item
  carries a **`source_episode` = a Tier 2 episode id** as a **SOFT back-pointer** (audit /
  explainability / reversibility), **not** a hard FK. Distilled lessons are self-contained
  ("Provenance referenced, not reused", D12) → T5 imposes **no retention lock on T2**; if T2
  GCs an episode the lesson still works, the id may dangle (acceptable). **This design is
  deliberately decoupled from the T2 retention decision** and holds either way.
  - **Lean (not locked) 2026-06-11:** user is now leaning toward **T2 = no-delete** (for
    traceability / explainability across tiers). If adopted, D12's `processed_at` downgrades
    from a GC watermark to a pure progress marker. Recorded as a lean; T5 unaffected either way.
- **D5-3 — `SchemaGraph` interface + permission model.** Read (frontline, read-only):
  `get_join_path(table_a, table_b)` → ranked paths w/ utility + negative constraints;
  `get_column_caveats(table, column)`. Write (**Enhancer only**): `reinforce_edge`,
  `penalize_edge(…, lesson, source_episode)`, `annotate_node(…, caveat, source_episode)`.
  Permission enforced by **handing out two different clients** (frontline read-only vs Enhancer
  write) — not self-discipline. Realises the mapping's "only Enhancer writes persistent memory".
- **D5-4 — Read path = graph-first, heuristic fallback.** Graph is a high-confidence empirical
  cache **in front of** the existing dumb `join_paths` heuristic. Graph hit → use validated
  edge + inject its caveats into the Materializer prompt. Graph miss / cold start → fall back to
  today's Damerau–Levenshtein heuristic string (**no regression, identical to today**). Used
  heuristic joins, once corrected, are written back → become graph hits next time.
- **D5-5 — Organic growth, no pre-build.** Do **NOT** auto-expand all declared foreign keys
  (FKs) from the schema — a declared FK is intent, not a guarantee, and in dirty EHR data
  declared joins routinely fail (type/format mismatch, FK constraints declared-but-disabled →
  referential drift, multi-source name collisions, time-encoding drift). Only joins **actually
  used / corrected** get an edge; never pre-map a giant schema; never trust schema claims over
  evidence. Negative constraints are distilled from **Tier 2 failure steps** (a primary payoff
  of T2 storing failures).
- **D5-6 — Node identity / keying.** v1 key = **fully-qualified name** `schema.table.column`;
  same key across sessions → same node grows (the basis of cross-session persistence). **Known
  limitation:** a table/column rename changes the key → the old node is **orphaned** (knowledge
  stranded, graph relearns from zero — degraded, never wrong). Schema-drift / table-rename
  aliasing deferred → BACKLOG (distinct from T3's *person* alias map; this is a *table* alias).

- **Refines D13's T4/T5 boundary (sharper).** Route a correction by its **subject**. T4's
  *authored* head holds only **authoritative org norms / definitions** (regulation-class, with a
  backer); **all empirical operational join knowledge is T5, evidence-first** — because authored
  content is human-uploaded, rarely cleaned, and goes stale. A declared FK in an authored data
  dictionary therefore **does NOT seed T5**.
- **Reaffirms T2 = shared substrate.** The same T2 trajectory (incl. failures) feeds multiple
  tiers; each tier's Enhancer pass takes its own slice (T5 = join/schema-navigation; T3 = format
  prefs; T4-learned = org conventions).
- **v1 backend:** NetworkX + JSON persistence behind the `SchemaGraph` interface; gitignored
  local store; Neo4j / graph DB = deferred backend swap (BACKLOG).
