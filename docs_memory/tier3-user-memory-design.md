# Tier 3 — User Memory — Build Spec (LOCKED v1)

> Status: **LOCKED 2026-06-10 (DECISIONS D14).** Background & boundary: `DECISIONS.md` D13;
> gap analysis: `code-vs-6tier-mapping.md` (Tier 3). Anchored on D11/D12 (interface-first,
> gitignored local store, dumb-first) and D13 (persistent priors, Enhancer-only-write).

## Purpose (confirmed)
A persistent **prior about a specific person** that accelerates *latent intent
convergence*: by knowing how this user tends to ask and where they focus, the Conductor
skips clarification rounds and guesses intent right sooner. Read-only to frontline agents;
written only by the Enhancer (+ a manual provisioned file in v1). Scope key = `user_id`
(already flows through every layer).

## What T3 holds — two sources

**(A) Provisioned profile** — declared identity, NOT learned. v1 = a **manually-filled
file** (MVP is for testing; the HR/identity-system feed is deferred → BACKLOG). Holds:
- role / job title, seniority/grade, department, whether clinical staff, location.
- Why it matters: predicts query *style* (clinician vs exec), gives a **weak** default
  scope (a `department` *label* — only a weak prior, see Focus range), and gives day-1
  personalization before any behavior is learned (cold-start).

**(B) Learned profile** — distilled by the **Enhancer from this user's Tier 2 log**. Holds:
- **Term/alias map** — this user's idiolect ("he says 'cases' meaning the Patient table").
- **Focus range** — *derived, not typed*: a **frequency distribution over schema
  elements / concepts** the user actually touches (which tables/columns/concepts, default
  filters, time windows). Replaces the rejected hand-typed "focus" line. Single-user seed
  of the BACKLOG "user-similarity space / emergent departments" idea.
- **Standing corrections** — corrections that recur across conversations ("'recent' = last 90
  days").
- **Format preferences** — show SQL? de-identified output? table vs prose.

## What T3 does NOT hold (boundaries)
- ❌ Raw trajectories / full history → Tier 2 (and reusable templates → Tier 6).
- ❌ Facts true for the whole org (clinical definitions, protocols) → Tier 4.
- ❌ Physical schema/join knowledge → Tier 5.
- ⚠️ **Demographic attributes used to shape answers** — governance line; store
  role/dept/grade (operationally useful), be cautious with pure demographics.
- ⚠️ **Authorization / "what the user may see"** — NOT in v1. T3 stores where the user
  *focuses* (for convergence), never what they're *permitted* to see. Real enforcement
  stays at the execution layer; never treat a T3 cache as a security source of truth.
  Deferred → BACKLOG.

## T3 ↔ T4 relationship (corrects "T3 is a leaf of T4")
T3 and T4 are **two distinct tiers**, differing in **owner / authority / subject**:
- **T3** = about a *person*; personal, heuristic, never authoritative for others.
- **T4** = shared, authoritative, often externally-authored *institutional* truth.

They are **not** a single scope ladder. They only **share the overlay *injection*
mechanism** at read time: multiple read-only priors are composed into the prompt in the
order `institution → department → user`, narrowest augments/overrides (CLAUDE.md model).
The overlay is *cross-tier prompt composition*, not "T3 ⊂ T4". The promotion ladder
(T1 → T3 → T4) applies **only to the thin slice of generalizable learned conventions** and
is gated by content-kind (a personal preference like "likes SQL shown" never promotes to an
org rule; a convention like "'recent' = 90 days" may). Most of T3 (identity + personal prefs)
and most of T4 (authoritative definitions/protocols) never overlap.

## Read path (injection)
Profile is small (distilled) → **inject the whole T3 block** into the Conductor env-state
prompt as a short structured "this-user" section (a mini per-user CLAUDE.md). Compression
happens at **write** time (Enhancer), not read time — **no runtime LLM summarization**. The
T3 block is the user layer of the overlay composition above.

## Write path (Enhancer)
- **Async / off-peak**, decoupled from live sessions (D13 principle).
- Reads this user's Tier 2 log (keyed by `user_id`), tallies the focus-range frequency
  distribution, mines recurring aliases/corrections/format prefs.
- **Promotion threshold** — a pattern must recur ≥ N times (or a correction that "stuck")
  before it enters the Learned profile; avoids one-off noise becoming a "habit". N tunable.
- **Rewritable living doc** — T3 is overwrite-style (Enhancer has Write/**Delete**, unlike
  Tier 2's append-only): last-write-wins + a `last_seen` timestamp per slot. Decay =
  deferred (BACKLOG).

## v1 spec (minimal — simplicity first)
| Aspect | Design |
|--------|--------|
| Scope key | `user_id` — **post-2026-06-15 sync this is a real authenticated `UserRecord` id** (Postgres `UserDB`), no longer a free request param; the same record also exposes `group_id`/`parent_group_id` (the user's org placement, useful for the T3→T4 promotion path) |
| Sources | Provisioned (manual file) + Learned (Enhancer from Tier 2) |
| Backend | one structured file per user (JSON/Markdown) behind a **`UserMemory` interface** (`read` / `write` / `update_slot`); gitignored local store, **vector backend deferred** |
| Mode | single-user MVP (multi-user company DB = backend swap → BACKLOG) |
| Read | inject whole block into Conductor env-state; no runtime summarization |
| Write | Enhancer only (+ manual provisioned file); rewritable; recurrence threshold |

## Implementation notes for v1
- Store lives under the gitignored memory scratch dir (same pattern as D11/D12); never
  committed/pushed.
- `UserMemory` is the single seam for the future multi-user / vector swap — keep all
  storage I/O inside it.
- Focus range is the seed of the multi-user "user-similarity space" (BACKLOG) — keep it as
  a clean per-user frequency profile so it can later be embedded/clustered.

## Deferred to later versions (→ BACKLOG.md)
Authorization/visibility, HR-system provisioned feed, multi-user backend, vector store,
user-similarity space + emergent departments, slot decay.
