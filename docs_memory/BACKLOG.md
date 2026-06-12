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

## Cross-tier

- **A/B-validation replay cost / sampled replay** — the Enhancer validates a conflicting new
  lesson by **replaying it (and the stored one) against the never-deleted Tier 2** (D18-5/6). This
  can re-run historical episodes (incl. EHR DB). Runs offline so volume is tolerable, but if it
  gets too large the reserved fallback is **sampled replay** (only a few past episodes, not full).
  Cost to be measured before adding the limit. *(D18)*

> **Resolved (no longer deferred):** *Tier 2 = no-delete* was a lean here; **LOCKED in D18-6**
> (T2 is the A/B replay corpus). `processed_at` → pure progress marker. The old "Episodic-log
> cleanup / retention" GC item is therefore dropped.
