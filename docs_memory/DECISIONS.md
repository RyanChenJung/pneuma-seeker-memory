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
