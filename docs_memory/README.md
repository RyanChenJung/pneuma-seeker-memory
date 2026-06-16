# docs_memory — file map

> One line per file: *what it is*, not what's in it. For **live state / where we are now**, read
> `RESUME.md` first (this map is the static "what each file is" axis; RESUME is the "current
> progress" axis). Maintenance rule: **new file = add one line here.**
>
> 👥 **Teammates (Sola / Juan / Lawrence): you want [`TEAM.md`](TEAM.md), not this file.** This map
> is the *internal* index; `TEAM.md` is the team-facing one. Only `scenario-spec.md` + `ROADMAP.md`
> are team-facing (and version-managed); everything else below is internal.

## Design specs (stable)
- `system_architecture.md` — the 6-tier north-star design target
- `level-tier-design.md` — Level × Tier architecture (LOCKED D20; Dept/Inst deferred)
- `tier1..tier6-*-design.md` — per-tier build specs (LOCKED v1)
- `enhancer-design.md` — the **WRITE** path: the Enhancer / background synthesizer (D20–D23)
- `injection-design.md` — the **READ** path *(planned, not yet written — see RESUME)*

## Decisions / deferred
- `DECISIONS.md` — chronological decision log (D1–D23); the authoritative lock for every choice
- `BACKLOG.md` — intentionally deferred *design items* (distinct from TASKS' deferred *work*)

## Understanding the existing (upstream) system
- `codebase-map.md` — how the EXISTING pneuma-seeker system works (source of truth for understanding)
- `code-vs-6tier-mapping.md` — existing code ↔ 6-tier design mapping + gap analysis + build order

## Process / live state
- `RESUME.md` — live state; **read FIRST on resume** *(gitignored, local-only)*
- `TASKS.md` — task ledger (`todo → in-progress → needs-review → done`)
- `ROADMAP.md` — milestones M1–M4 + team roles + weekly breakdown
- `surgical-changes.md` — log of surgical (additive, flag-gated) edits to upstream code

## Team-facing (👥 version-managed; see `TEAM.md`)
- `TEAM.md` — the teammate entry point: which doc is whose + every team-facing doc's current version
- `scenario-spec.md` — the campus validation scenario (2 depts, ambiguous terms, hidden rules) + the 3 contracts **[v2]**
- `ROADMAP.md` — milestones M1–M4 + team roles + weekly breakdown **[v1]** *(also listed under Process)*

> Local-only ephemera (gitignored, not part of the repo): `_*.md` handoff/draft files and the
> exported `*.docx` team contract.
