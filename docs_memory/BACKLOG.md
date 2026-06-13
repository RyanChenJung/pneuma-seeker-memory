# Backlog — Intentionally Deferred Design Items

> Things we **decided NOT to build now but may build later**. This is distinct from
> `TASKS.md` "Backlog" (= unapproved *to-do work*). Here we park *design ideas / future
> features* so they are not lost and not re-litigated. Each item carries a back-pointer to
> where it was deferred. Promote an item by turning it into a TASKS.md entry when ready.

## Memory-layer (cross-tier)

- **Vector / semantic backends** — every tier ships v1 behind a plain interface (JSONL /
  JSON / Markdown / NetworkX); swapping to a vector store (Qdrant/Chroma) or graph DB
  (Neo4j) is a deferred backend swap, no redesign. Earns its keep only at scale (store too
  big to inject wholesale, or fuzzy semantic match needed). *(D11, D12, D13, D14)*
- **DuckDB upgrade for the episodic log** — Tier 2 v1 = JSONL behind `EpisodicLog`;
  upgrade path = a DuckDB table. *(D12)*
- ~~**Episodic-log cleanup / retention**~~ — **DROPPED (D18-6):** T2 is no-delete (it is the A/B
  replay corpus), so there is no GC of consumed episodes; `processed_at` is a pure progress marker.
- **Persistent-tier retention (dormancy-decay + capacity-purge)** — `system_architecture.md`
  §5.5's "decay Utility Score / purge idle". A maintenance job over the **persistent** tiers
  (T3–T6): lower an item's `support` as its `last_seen` ages (dormancy decay), and evict the
  lowest-`support` items when an inject-whole tier exceeds its token budget (capacity purge).
  The fields (`support` + `last_seen`) are in place; the policy is deferred. **Distinct from the
  Tier 2 no-delete rule** (LOCKED D18-6 — that is the raw log; this is the distilled priors). *(D17;
  touches system_architecture §5.5)*

## Tier 3 — User Memory

- **Authorization / data-visibility in T3** — whether T3 carries a "what this user is
  allowed to see" hint (PII / department / row-column scope). Important, but a separate
  governance system and NOT what the MVP tests. v1 stores only "where the user *focuses*"
  (for intent convergence), never "what they're *permitted* to see" (stays at the execution
  layer). Revisit in the multi-user phase. *(D14)*
- **Multi-user T3 backend** — v1 is single-user (one profile file). Multi-user = a company
  DB keyed by `user_id`; pure backend swap behind the `UserMemory` interface. *(D13, D14)*
- **Real-user vs (dept, role) separation** — M1 collapses persona = `user_id` (one `user_id`
  = one fixed `(dept, role)`; D19). This models the logged-in-principal→profile pattern fine,
  but cannot represent **one real human switching department/role within a session** (that
  reads as a different user → different workspace namespace). When a genuine multi-role user
  appears, split the principal (`user_id`) from the profile: a `user → roles[]` map with an
  active-role selector, or a session-level `(dept, role)` override. *(D19)*
- **User-similarity space + emergent departments (the "circles" idea)** — embed each user's
  derived focus-profile as a vector → users become points in a space → cluster by behavioral
  proximity → **departments emerge from behavior, not the HR `department` label** (a user in
  Cardiology doing unusual work may sit nearer another department's people). Feeds D13's
  org-overlay/promotion and gives day-1 cold-start (place a new user near similar users,
  inherit their cluster's defaults). Implies a refinement to D13: **org scope may be soft,
  overlapping, multi-membership clusters — not a clean hard hierarchy**; Provisioned
  `department` becomes a weak prior only. Algorithmically standard (k-means / community
  detection); the real prerequisites are many users + accumulated Tier 2 + a chosen
  concept/schema vocabulary to embed over. Intrinsically a multi-user feature; single-user
  MVP only builds the *seed* (the per-user derived focus profile). *(D14; refines D13)*

## Tier 4 — Organization Memory

- **Reuse upstream `DocumentDB` / `Knowledge` (local/global) vs build our own** — pending
  the user's email to the upstream author. Working assumption: `local ≈ T3`, `global ≈ T4`.
  Authored backend is hidden behind the `OrgMemory` facade, so this is a deferred backend
  swap. *(D13, D15)*
- **Exact scope-level count + overlay precedence rules** — provisional until the author
  replies. v1 = hard 2-level `(institution, department)` hierarchy. *(D13, D15)*
- **Full org-memory governance** — v1 only tags authored content with thin metadata (source,
  trust, scope). Real version-control / who-authored / approval (sign-off) workflow deferred.
  *(D15)*
- **HR / identity-system authored feed** — v1 ingests authored docs via manual/file import;
  an automated org-knowledge feed is deferred. *(D15)*
- **Authored dynamic-trust formula** — v1's "authored always wins" is static. Later: authored
  trust = f(base authority, the `negative`-`support` the *learned* side accumulates against it),
  so repeated empirical contradiction erodes a stale authored fact ("learned > authored" made
  operational). Needs the conflict-resolution weighting formula. *(D18-8; refines D15)*
- **Soft, overlapping, multi-membership org clusters** — v1 = hard hierarchy; behavior-
  emergent soft clusters (shared with the T3 "user-similarity space" idea) deferred to the
  multi-department / multi-user phase. *(D14, D15)*

## Tier 5 — Schema Routing Memory (Schema Graph)

- **Schema-drift / table-rename node aliasing** — v1 keys nodes by fully-qualified
  `schema.table.column`; a rename changes the key and **orphans** the old node (accumulated
  join knowledge stranded; graph relearns from zero). Re-keying / alias migration for renamed
  tables/columns deferred. Distinct from T3's *person* alias map — this is a *table* alias.
  *(D16)*
- **Neo4j / graph-DB backend** — v1 = NetworkX + JSON behind the `SchemaGraph` interface;
  swap to a real graph DB is a deferred backend swap (also covered by the cross-tier vector/
  graph item above). *(D13, D16)*
- **Authored-FK seeding — rejected by design, not deferred:** T5 is evidence-first; a declared
  FK in an authored data dictionary never auto-seeds T5. Listed here only so it is not
  re-litigated. *(D16)*

## Tier 6 — Long Memory (Procedural / Method Skeletons)

> **D18 reframed T6 v1.** v1 (= Layer 0) is now **inject-whole md, no embedding / no retrieval
> key**. Everything about retrieval below is therefore a *Layer 1+* future, not "v1 vs v2".

- **Layer 1 — embedding/retrieval when the store outgrows the prompt budget** — add a retrieval
  key = NL-embedding + operator-sequence, **conditioned on T3/T4 context** to disambiguate latent
  intent (this, not Layer 2, is what fixes the same-words-different-intent collision). Built only
  once inject-whole no longer fits. *(D18-4; supersedes D17 D6-1 as a layer)*
- **Layer 2 (v2) = abstracted, parameterized plan templates keyed by a structured `problem_type`
  taxonomy (Option B)** — the user's true-north retrieval design. The taxonomy must be
  **discovered from accumulated Tier 2 data** (so it cannot be built first); the abstraction is the
  Enhancer's hardest LLM job. *(D13, D17, D18-4)*
- **Operator-sequence-skeleton generality** — the ReAct operator sequence
  (`join→filter→group-by→aggregate`) is a candidate Layer 1 retrieval component, but whether it is
  general / worth storing is **unproven**; Layer 2 may drop it for `problem_type`. *(D17, D18)*
- **Causal credit attribution among co-injected exemplars** — v1's `support` is a recurrence
  prior, not a causal utility (cannot cleanly credit one exemplar among several co-injected
  items + T5 caveats + T4 facts). Revisit a causal score only with a clean method
  (single-template injection / A-B). *(D17)*
- **Rare-but-critical under-weighting** — `support` is recurrence-weighted, so a method used
  once that averted a disaster scores low (same long-tail blind spot as a usage-count, moved
  to the distillation side). *(D17)*
- **Silent semantic errors** — the v1 success gate catches explicit signals (terminal state,
  ReAct self-overturn, implicit user pushback) but not an answer that is silently wrong *and*
  that the user also never pushes back on. Needs a v2 LLM semantic judge or accumulated later
  corrections. *(D17)*
- **Asymmetric recurrence threshold** — v1 uses one symmetric threshold for positive and
  negative entries; a lower bar for negative anti-patterns (a repeatedly-made mistake should
  promote faster) is a noted future direction. *(D17)*

## Enhancer (background synthesizer)

> Full build spec: `enhancer-design.md`. These are the cost/scale optimisations deliberately
> cut from v1 because the current stage is **effectiveness-first** (prove it works, optimise later).

- **Cheap no-LLM implicit-pushback detection** — v1 uses an LLM in the Stage-1 eligibility gate to
  read implicit pushback (D23 amends D21's "Stage-1 = no LLM"). The cost-optimised path: behavioural
  signals ("no positive ack + immediate near-duplicate re-ask"), a negation/correction lexicon, and
  optionally a small **local** classifier (not a generative LLM call). Add when cost matters. *(D23)*
- **Per-run cost cap** — limit the number of LLM calls per Enhancer run to bound spend. Deferred
  (effectiveness-first); distinct from the *input* (context) cap, which is physical. *(D23)*
- **Context-cap chunking (embedding pre-bucketing)** — when candidates exceed the cluster pass's
  context window, pre-bucket likely-same fragments cheaply (embedding) → LLM does the **final**
  clustering within each bucket. Does NOT violate D21 (embedding only pre-buckets, never *replaces*
  LLM clustering). MVP never hits this (User-level volume small). *(D23)*
- **Near-exact-text REINFORCE shortcut** — v1 routes even REINFORCE through the LLM (embedding can't
  separate same-lesson from contradiction). A strict near-exact-text match on `intent` could shortcut
  the high-frequency duplicate case without an LLM call. *(D23)*
- **Conditional-skip of the additive-merge A/B** — v1 always runs the A/B validation after a MERGE
  (it harmlessly abstains for an additive merge). Detecting "this is purely additive → skip A/B"
  saves calls but adds branching logic. *(D23)*
- **Deterministic A/B discrimination pre-filter** — for *operationalisable* (executable) meaning,
  cheaply drop episodes where A and B compute the same result before the LLM reads them. CUT from MVP
  (only works for executable meaning, never pure-text, and the LLM's `abstain` already covers it).
  *(D22, D23)*

## Cross-tier

- **A/B-validation replay cost / sampled replay** — the Enhancer resolves a conflicting new
  lesson against the never-deleted Tier 2 (D18-5/6, mechanism in **D22**). For meaning tiers
  (T3/T4/T6) v1 only **re-reads** a relevant T2 slice (cheap); for T5 it objectively **re-tests**
  joins against the DB. Runs offline so volume is tolerable, but if the relevant slice gets too
  large the reserved fallback is **sampled replay** (a few past/recent episodes, not the full
  slice). Cost to be measured before adding the limit. *(D18, D22)*
- **Full agent re-execution for meaning conflicts — rejected by design, not deferred (D22):**
  re-running the whole Conductor with version A vs B injected (Option C) produces *new* answers
  no human ever reacted to, so picking a winner needs a from-scratch correctness judge with no
  oracle. Listed here so it is not re-litigated; the objective DB re-test for T5 is the only
  legitimate re-execution. *(D22)*
- **Memory transparency / alignment surface (surface operative assumptions to the user)** —
  original Pneuma already shows, in the sidebar, the actual tables it ended up retrieving — a
  human↔LLM alignment point. Extend this: surface the **memory-injected operative assumptions**
  (e.g. "assumed yield = enrolled/admitted, per Admissions convention"; which join; which
  definition), fed largely from the curated **Tier 1** notebook (D9/D11), into the UI sidebar.
  Two payoffs: (1) it lets the human catch the **silent collective error** that Option B
  structurally cannot (an org-wide wrong-but-operative definition) — shrinking that gap; (2) it
  **shifts responsibility** — once an assumption is shown and not challenged, the user owns the
  outcome, not the system. Connects: T1 (the surface), B's blind spot (D22), the "human is the
  ground truth" principle. Future UI work (touches `pneuma-seeker-ui`). *(D22; mitigates the B
  blind spot)*

> **Resolved (no longer deferred):** *Tier 2 = no-delete* was a lean here; **LOCKED in D18-6**
> (T2 is the A/B replay corpus). `processed_at` → pure progress marker. The old "Episodic-log
> cleanup / retention" GC item is therefore dropped.
