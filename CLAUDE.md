# Project Operating Guide — Pneuma-Seeker Memory Layer

> Auto-loaded each session. Layers on top of (does not override) the global
> `~/.claude/CLAUDE.md`. Keep this file short.

## Context

This repository is a **fork** of `TheDataStation/pneuma-seeker` (upstream). Our work
is a **memory-layer plugin** for Pneuma-Seeker. The design target is
[`docs_memory/system_architecture.md`](docs_memory/system_architecture.md) (a 6-tier
hierarchical memory system). For how the existing system works, see
[`docs_memory/codebase-map.md`](docs_memory/codebase-map.md). For how the existing
code maps onto the 6-tier design (and where it falls short), see
[`docs_memory/code-vs-6tier-mapping.md`](docs_memory/code-vs-6tier-mapping.md).

## ⚠️ PR / Push Safety (non-negotiable)

- **NEVER push or open a PR to `upstream` (`TheDataStation/...`).** A PR was once sent
  there by accident. All work goes to `origin` (`RyanChenJung/pneuma-seeker-memory`).
- Guardrails are configured: `upstream` push URL = `DISABLE`, `remote.pushDefault = origin`.
- `gh` is installed. **Preferred PR path:** `gh pr create --repo RyanChenJung/pneuma-seeker-memory
  --base prod ...` — the explicit `--repo` can never hit upstream. Needs a one-time
  `gh auth login`. For any GUI/web PR, **verify the base repo reads
  `RyanChenJung/pneuma-seeker-memory`** first. (See `docs_memory/DECISIONS.md` D1.)
- `git fetch upstream` (read-only sync) is fine. `git push upstream` / `gh pr create`
  targeting upstream is forbidden.
- The base branch for our PRs is `prod` on **origin**, never upstream.

## Ownership Boundaries (we are a plugin — minimize changes to upstream code)

- 🟢 **Fully ours** (free to change): `docs_memory/`, `src/pneuma_seeker/services/memory/`
  (our memory package), `tests/memory/`, and the hospital experiment files we added.
- 🟡 **Surgical only** (upstream's; additive + feature-flagged + tiny diffs):
  `services/core/conductor/` (+ prompt factories), `services/core/ir_system/`,
  `services/db/main.py`, `shared/config.py`, `main.py`. Every edit must be additive,
  guarded by an `ENABLE_MEMORY_*` config flag (default off), and ideally a single call
  into our own module — so upstream merges stay clean and the plugin is removable.
- 🔴 **Do not touch**: `docs/architecture.md`, `docs/figures/`, `README.md`, `LICENSE`,
  `CONTRIBUTING.md`, `baselines/`, upstream's original `data_src/`.

## Workflow

1. User defines a goal.
2. I decompose it into small tasks and record them in
   [`docs_memory/TASKS.md`](docs_memory/TASKS.md).
3. **User approves the breakdown** — the single human gate.
4. I dispatch sub-agents (parallel, isolated git worktrees) to implement + test each task.
5. I aggregate: run the full test suite, summarize what was done, and surface only the
   decisions/problems that need the user. The user does not supervise coding details.
6. One small commit per task, on the fork branch only.

Task ledger is the single source of truth (`docs_memory/TASKS.md`). Statuses:
`todo → in-progress → needs-review → done` (or `blocked`).

## Resuming after /clear
On `resume` / `繼續` (or any "pick up where we left off" cue), read
`docs_memory/RESUME.md` first (live state + the exact Next action), then `DECISIONS.md`
and `TASKS.md` as needed. Continue from RESUME's "Next action"; do not re-derive settled
facts. At the end of a working session, update `RESUME.md` so the next resume is clean.

## Docs management

- Global `~/.claude/CLAUDE.md`: untouched (language + coding philosophy).
- This file: agent operating rules for this repo.
- `docs_memory/`: our design + specs (treat as "our `docs/`"; upstream's `docs/` is theirs).
- `docs_memory/codebase-map.md`: single source of truth for understanding the existing
  system (md is the source; `docs_understanding/` HTML is generated from it for the user).
- `docs/` is upstream's — we never modify it.
