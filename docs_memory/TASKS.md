# Task Ledger — Memory Layer

Single source of truth for what we are doing. One row per task.
**Statuses:** `todo` → `in-progress` → `needs-review` → `done` (or `blocked`).
Human gate: a task only moves past `todo` after the user approves the breakdown.

| ID | Task | Status | Agent | Commit | Notes |
|----|------|--------|-------|--------|-------|
| S0.1 | Apply PR-safety guardrails (disable upstream push, pushDefault=origin) | done | — | (local git config) | Guardrails live; `gh` default repo = fork done in S0.4 |
| S0.2 | Create root `CLAUDE.md` (ownership, PR-safety, workflow) | needs-review | — | — | Awaiting user review before commit |
| S0.3 | Create this task ledger | done | — | — | — |
| S0.4 | Install `gh` + set fork as default PR target | done | — | — | `gh` v2.93.0 installed, authed as RyanChenJung, default repo = fork ✅. PRs via `gh pr create --repo RyanChenJung/pneuma-seeker-memory --base prod`. |
| S0.5 | Move `codebase-map.md` → `docs_memory/`; update CLAUDE.md refs; leave `docs/` untouched | needs-review | — | — | Keeps upstream `docs/` clean |
| S0.6 | Write `docs_memory/code-vs-6tier-mapping.md` (honest gap analysis) | needs-review | — | — | For user to read; corrects earlier "high overlap" claim |

## Goal G1 — Finish `docs_understanding/` HTML (approved; path A)

Audience bar (locked): Traditional Chinese prose; reader is a **beginner** who wants
engineering depth — detailed but easy, heavy on analogies + worked examples; after
reading they can confidently explain the architecture/design and how our memory layer
will interact. Gold-standard template = the existing `modules/services_core_conductor/`
page. Agents produce only their HTML page; **I update `CHECKPOINT.md` centrally**.

| ID | Page | Status | Agent | Notes |
|----|------|--------|-------|-------|
| H1 | `modules/services_core_materializer/` | needs-review | bg-agent | plain-language spec v2 (1028 lines) — **gold standard**. User OK'd v2 style 2026-06-10 → batches 2–4 + retrofits fanned out. |
| H2 | `modules/services_core_ir_system/` | needs-review | bg-agent | retrofitted to v2 (656→943 lines) |
| H3 | `modules/services_core_action_set/` | needs-review | bg-agent | retrofitted to v2 (~580→888 lines) |
| H4 | `modules/services_db/` | needs-review | bg-agent | v2, 876 lines |
| H5 | `modules/services_indexing/` | needs-review | bg-agent | v2, 837 lines |
| H6 | `modules/services_language_model/` | needs-review | bg-agent | v2, 966 lines |
| H7 | `modules/shared/` | needs-review | bg-agent | v2, 757 lines (notes ENABLE_MEMORY_* home) |
| H8 | `modules/provenance/` | needs-review | bg-agent | v2, 1132 lines |
| H9 | `modules/tests/` | needs-review | bg-agent | v2, 847 lines |
| H10 | `modules/baselines/` | needs-review | bg-agent | v2, 844 lines (upstream — doc only) |
| H11 | `modules/openwebui_functions/` | needs-review | bg-agent | v2, 866 lines |
| H12 | `01_architecture_deep_dive.html` | needs-review | bg-agent | v2, 804 lines (three-service sequence diagrams / design patterns / DI), claims verified vs source |
| H13 | `02_flow_traces.html` | needs-review | bg-agent | v2, 835 lines (query / indexing / materialization / Semantic Join E2E), claims verified vs source |
| H14 | `03_concepts.html` | needs-review | bg-agent | v2, 805 lines (State/Prompt/Factory/Provenance/flags/allow-list), claims verified vs source |

Plan: batch 1 runs now → user eyeballs ONE page to lock tone/depth → fan out batches
2–4 unsupervised → batch 5 last (synthesis).

## Goal WS — Walking Skeleton (knowledge injection wired into Pneuma, flag-gated)

Approved 2026-06-12 (user: "do the walking skeleton first"). **Goal:** `POST /chat` with a known
persona `user_id` + flag ON → a dept/role + tribal-knowledge SYSTEM message is injected into
the prompt; flag OFF → byte-identical to baseline; plugin fully removable. De-risks the
project's #1 unknown (clean injection into Pneuma). **NOT in scope:** retrieval/embedding
(inject-whole), T2/Enhancer, Sola's real datasets, role-presentation logic, token tuning.
Design rationale: `DECISIONS.md` D19 (`user_id` persona) + `scenario-spec-v1.md` §4–6.
**Execution:** one inline focused pass (not parallel sub-agents — ~150 LOC, interdependent).

Surgical footprint (🟡, additive + flag-guarded, ~5 lines total): `shared/config.py`
(`ENABLE_MEMORY_INJECTION`, default off) + `services/core/conductor/main.py` (one block after
`self.llm_messages = [sys_prompt]`). Everything else is 🟢 in `services/memory/`.

| ID | Task | Status | Agent | Commit | Notes |
|----|------|--------|-------|--------|-------|
| WS1 | Scaffold `services/memory/` pkg + `ENABLE_MEMORY_INJECTION` flag in `shared/config.py` (default off, mirrors `ENABLE_MEMORY_PROFILING`) | done | — | — | SC-1; flag OFF = no-op (test `test_default_off`) |
| WS2 | T3 identity: `t3_identity.py` + `_config/identity_map.json` (4 personas, spec §5); `lookup(user_id) -> (dept, role) \| None` | done | — | — | unknown user → None ✓ |
| WS3 | T4-authored loader: `t4_authored.py` + `_config/tribal_knowledge.sample.json` (seed spec §B 4 entries, Juan's format); `get_dept_knowledge(dept) -> list[entry]` | done | — | — | swap sample for Juan's real JSON later ✓ |
| WS4 | `injector.py`: `MemoryInjector.get_injection(user_id, query) -> str \| None` — compose SYSTEM text from T3+T4 (inject-whole) | done | — | — | None when persona unknown ✓; output eyeballed |
| WS5 | Surgical hook in `conductor/main.py`: build `self.memory_injector` once + `_inject_memory()` helper called after sys prompt | done | — | — | SC-2; 3 edits, all flag-guarded |
| WS6 | Tests `tests/memory/`: OFF→no injection / ON+known persona→string present in `llm_messages` / ON+unknown→no injection | done | — | — | 8 pass; 3 conductor tests skip when full runtime absent — all 11 (incl. the 3 vs the real Conductor) confirmed passing in an isolated venv 2026-06-13 |

## Backlog (proposed — not yet approved)

These came up in discussion. They need the user's go-ahead (workflow step 3) before
moving to `todo`/`in-progress`:

- **B3** — superseded by **Goal WS** above (the package scaffold + flag is WS1).
- **B4** — (implied by gap analysis) Tier 2 append-only **episodic log** is the
  foundation the Enhancer + Tiers 3/5/6 depend on. Likely the next *coding* goal after WS.

> B2 (merge/cross-link system_architecture into the map) is resolved by
> `code-vs-6tier-mapping.md`, which documents where each tier attaches.

> When a goal is defined, expand it into S-prefixed tasks above, get approval, then execute.
