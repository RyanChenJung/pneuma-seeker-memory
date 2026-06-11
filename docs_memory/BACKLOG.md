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
- **Episodic-log cleanup / retention** — `processed_at` watermark exists but actual GC of
  consumed episodes is deferred. *(D12)*

## Tier 3 — User Memory

- **Authorization / data-visibility in T3** — whether T3 carries a "what this user is
  allowed to see" hint (PII / department / row-column scope). Important, but a separate
  governance system and NOT what the MVP tests. v1 stores only "where the user *focuses*"
  (for intent convergence), never "what they're *permitted* to see" (stays at the execution
  layer). Revisit in the multi-user phase. *(D14)*
- **Multi-user T3 backend** — v1 is single-user (one profile file). Multi-user = a company
  DB keyed by `user_id`; pure backend swap behind the `UserMemory` interface. *(D13, D14)*
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

## Tier 6 (noted, drill later)
- (none beyond the cross-tier vector/graph backend item above — drill T6 to populate)

## Cross-tier — open lean

- **Tier 2 = no-delete (retention policy)** — as of 2026-06-11 the user is *leaning* toward
  making the episodic log **never delete** (traceability / explainability matter across many
  tiers), which would downgrade D12's `processed_at` from a GC watermark to a pure progress
  marker. **Lean, not locked** — revisit when finalising T2 retention. (Supersedes, if
  adopted, the "Episodic-log cleanup / retention" item above.) *(D16; touches D12)*
