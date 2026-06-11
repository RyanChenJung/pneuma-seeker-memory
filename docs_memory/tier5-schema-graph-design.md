# Tier 5 — Schema Routing Memory (Schema Graph) — Build Spec (LOCKED v1)

> Status: **LOCKED 2026-06-11 (DECISIONS D16).** Background & boundary: `DECISIONS.md` D13
> (T5 direction) + D16 (this lock); gap analysis: `code-vs-6tier-mapping.md` (Tier 5).
> Anchored on D11/D12 (interface-first, gitignored local store, dumb-first) and D13
> (persistent priors, Enhancer-only-write, grown by learn-by-correction).

## Purpose (confirmed)
A persistent **property graph that patches messy EHR schemas**. It turns blind, per-query
schema inference into high-confidence, empirically-grounded graph retrieval: which columns
actually join, how reliable each join is, and the human-readable failure lessons that come
with them. Read-only to frontline agents; written only by the Enhancer. Scope key = the DB
schema. This is the highest-value, highest-effort tier.

## Data model (D5-1) — nodes & edges
Two node types; join edges live at the **column** level (joins always happen on columns):

- **`table` node** — a physical table.
- **`column` node** — a physical column; attached to its table via a `contains` edge.
- **`join` edge** — connects **two `column` nodes** (`A.patient_id = B.patient_id`). This is
  the validated join path.

Column-level value/temporal caveats live on **nodes**; join utility + failure lessons live on
**edges** (D13: nodes AND edges both carry payload).

## Payload schema (D5-2)
Every learned item carries a **provenance back-pointer** = the **Tier 2 episode id** it was
distilled from (see "Provenance" below).

**`join` edge payload:**
- `support` — accumulated empirical evidential weight (the cross-tier term, see DECISIONS
  Glossary). **In T5 it is computed from per-edge success/failure**: reinforced on a
  successful join, penalized on a failed one. (Cf. T6, where `support` is computed from
  recurrence — same name, same meaning "evidence backing this learned item", different
  per-tier computation.)
- `success_count` / `fail_count` — the inputs T5's `support` is computed from.
- `negative_constraints[]` — human-readable failure lessons, each `{lesson, source_episode}`
  (e.g. *"join on patient_id duplicates rows; use encounter_id"*).
- `last_seen`.

**`column` node payload:**
- `value_caveats[]` — each `{caveat, source_episode}` (e.g. *"pre-2010 stored as text,
  post-2010 numeric"*).
- `temporal_caveats[]` — same shape.

## `SchemaGraph` interface (D5-3)
The plugin seam. Permission model is enforced by **handing out two different clients**:
frontline agents get a read-only client (only `get_*`); the Enhancer gets the only client
with write methods. Nothing relies on self-discipline.

**Read (frontline, read-only):**
- `get_join_path(table_a, table_b)` → ranked join paths, each with `support` +
  `negative_constraints`. Used by the Materializer before it picks a join.
- `get_column_caveats(table, column)` → that column's value/temporal caveats.

**Write (Enhancer only):**
- `reinforce_edge(col_a, col_b)` — a join that worked.
- `penalize_edge(col_a, col_b, lesson, source_episode)` — a join that failed + the lesson.
- `annotate_node(table, column, caveat, source_episode)` — a value/temporal caveat.

## Read path — graph-first, heuristic fallback (D5-4)
The graph is a **high-confidence empirical cache in front of the existing dumb heuristic**:

- The Materializer first calls `get_join_path`.
- **Graph hit** → use the validated edge; inject its `negative_constraints`/caveats into the
  prompt so the agent does not repeat a known mistake. (Beats name-similarity because it is
  empirical.)
- **Graph miss / cold start** → fall back to the **existing** `join_paths` heuristic string
  (Damerau–Levenshtein name/value similarity). **Behaviour identical to today; no
  regression.**
- That heuristic join, once used and corrected, is written back by the Enhancer → next time
  the same question becomes a graph hit. The graph only ever gets smarter.

## Write path — learn-by-correction (D5-5)
- **Async / off-peak Enhancer**, distilling from the Tier 2 episodic log (T5 takes the
  *join / schema-navigation* slice of each trajectory; other tiers take other slices of the
  same log — T2 is the shared substrate).
- **Negative constraints come from T2 failure steps** — this is a primary payoff of T2
  storing failed trajectories, not only successful ones.
- **Purely organic growth — no pre-build.** We do **NOT** auto-expand all declared foreign
  keys (FKs) from the schema. A *declared* FK is only intent, not a guarantee: in dirty EHR
  data, declared joins routinely fail (type/format mismatch like `"00042"` vs `42`,
  FK constraints declared in docs but disabled in the DB so referential integrity drifts,
  multi-source merges reusing a column name for different meanings, time-based encoding
  drift). So only joins **actually used / corrected** get an edge — we never pre-map a giant
  schema, and we never trust the schema's claims over evidence.

## Node identity / keying (D5-6)
- v1 key = **fully-qualified name** `schema.table.column` (e.g. `public.labs.encounter_id`).
  Same key across sessions → the same node grows; this is what makes the graph cross-session
  persistent.
- **Known v1 limitation:** if a table/column is renamed (`labs` → `lab_results`), the key
  changes → the old node is **orphaned** (its accumulated knowledge is stranded; the graph
  just relearns from zero — degraded, never wrong). Schema-drift / table-rename aliasing is
  deferred → BACKLOG. (Distinct from T3's *person* alias map; this is a *table* alias.)

## Provenance & Tier 2 retention (D5-2)
- The `source_episode` on every learned item is a **soft back-pointer** into Tier 2 (for
  audit / explainability / reversibility), **not** a hard foreign key.
- Distilled lessons are **self-contained** — readable and usable without re-reading the raw
  trace ("Provenance referenced, not reused", D12). If Tier 2 ever GCs that episode, the T5
  lesson still works; the id may dangle, which is acceptable.
- **Deliberately decoupled from the T2 retention decision:** the soft-pointer design holds
  whether T2 deletes or never deletes, so T5 imposes **no retention lock** on T2. (As of
  2026-06-11 the user is *leaning* toward T2 = no-delete for traceability/explainability, but
  that is not yet locked and does not change this spec — see DECISIONS D16 lean note.)

## T4 ↔ T5 boundary (refines D13)
Route a correction by its **subject**: T5 = **physical DB navigation** (how to read *this*
DB — which columns join, value/temporal caveats). T4 = **meaning / institutional rules**.
Sharper than D13: T4's *authored* head holds only **authoritative org norms / definitions**
(regulation-class content with a backer); **all empirical operational join knowledge is
T5**, and **evidence-first** — because authored content is human-uploaded, rarely cleaned,
and goes stale. A *declared* FK in an authored data dictionary therefore **does NOT seed
T5**; T5 only stores joins it has empirically validated.

## v1 spec (minimal — simplicity first)
| Aspect | Design |
|--------|--------|
| Scope key | DB schema |
| Backbone | property graph (nodes = tables/columns, edges = validated joins) |
| Backend | **NetworkX + JSON persistence** behind a **`SchemaGraph` interface**; gitignored local store; **Neo4j / graph DB = deferred backend swap** |
| Payload | edges: `support` (from `success/fail_count`), `negative_constraints[]`, `last_seen`; nodes: `value_caveats[]`, `temporal_caveats[]`; every item carries `source_episode` |
| Read | `get_join_path` / `get_column_caveats`; **graph-first, heuristic fallback**; inject caveats into Materializer prompt; no runtime summarization |
| Write | Enhancer only (`reinforce`/`penalize`/`annotate`); learn-by-correction from Tier 2; organic growth, no pre-built FK expansion |
| Permission | two clients: frontline read-only, Enhancer write-only seam |

## Implementation notes for v1
- Store lives under the gitignored memory scratch dir (same pattern as D11/D12); never
  committed/pushed.
- `SchemaGraph` is the single seam for the future Neo4j / graph-DB swap — keep all graph I/O
  inside it.
- Keep nodes keyed by fully-qualified name so a future rename/alias migration (BACKLOG) can
  re-key without touching callers.
- The existing `join_paths` heuristic and `ProvenanceGraph` are **not** T5 (per
  `code-vs-6tier-mapping.md` Tier 5): one is throwaway heuristic text, the other a
  per-session operation-level lineage DAG. T5 is a new, separate, persistent graph.

## Deferred to later versions (→ BACKLOG.md)
Neo4j / graph-DB backend, schema-drift / table-rename node aliasing, vector/semantic node
matching, authored-FK seeding (rejected by design — evidence-first).
