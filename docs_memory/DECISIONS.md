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
Tier 2 design LOCKED (2026-06-10, decisions (1)–(4) confirmed with user). Tier 2 = the
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
