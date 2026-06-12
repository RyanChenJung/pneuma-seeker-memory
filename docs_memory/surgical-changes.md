# Surgical Changes Ledger — Upstream (🟡) Touchpoints

> **The single record of every edit we make to upstream Pneuma code.** We are a *plugin*; our
> goal is a near-zero, auditable, reversible footprint on code we do not own. Every 🟡 edit gets
> one entry here, so an upstream merge (or a clean removal of our plugin) is mechanical.
>
> Cross-refs: [`CLAUDE.md`](../CLAUDE.md) (ownership boundaries), [`DECISIONS.md`](DECISIONS.md)
> (D2 plugin discipline), [`TASKS.md`](TASKS.md) (the tasks that produce these edits).

## The 🟡 "surgical-only" files (from `CLAUDE.md`)

Edits are permitted **only** to these upstream files, and only under the discipline below:
`services/core/conductor/` (+ prompt factories) · `services/core/ir_system/` ·
`services/db/main.py` · `shared/config.py` · `main.py`.
Everything in `services/memory/`, `tests/memory/`, `docs_memory/` is 🟢 ours (not logged here).
`docs/`, `README.md`, `LICENSE`, `baselines/`, upstream `data_src/` are 🔴 never touched.

## Discipline — every entry MUST satisfy all of these

1. **Additive** — we add code paths, never rewrite or delete upstream logic.
2. **Flag-guarded** — gated by an `ENABLE_MEMORY_*` config flag (default **off**).
3. **Tiny** — a few lines; if it grows, push the logic into `services/memory/` and leave only a
   single call here.
4. **Single call into our module** — the 🟡 file should call **one** entry point in
   `services/memory/`, nothing more.
5. **Flag OFF ⇒ byte-identical to upstream** — with the flag default off, the plugin is already a
   no-op; reverting the entries below returns the tree to pristine upstream.

## Ledger

Status values: `planned` → `applied` (with commit) → `reverted`.

### SC-1 — `shared/config.py` — add `ENABLE_MEMORY_INJECTION` flag
- **Status:** planned (Goal WS / WS1).
- **What:** add one `Config` attribute reading an env var, default `"false"` → `False`, **exactly
  mirroring the existing `ENABLE_MEMORY_PROFILING`** pattern in the same file.
- **Flag:** this entry *defines* the flag (`ENABLE_MEMORY_INJECTION`). It is the A/B master switch
  the benchmark (Lawrence) toggles by launching the server with the env var on vs off.
- **Why unavoidable:** `Config` is Pneuma's only configuration entry point; the conductor reads the
  flag via `self.config.ENABLE_MEMORY_INJECTION`.
- **Footprint:** ~3 added lines. No existing line changed.
- **Removal:** delete the added attribute.
- **Refs:** D19; `scenario-spec-v1.md` §6.3 (Lawrence A/B contract); TASKS WS1.

### SC-2 — `services/core/conductor/main.py` — prompt-injection hook
- **Status:** planned (Goal WS / WS5).
- **What:** two flag-guarded additions —
  - **(a)** in `Conductor.__init__`: construct `self.memory_injector` once
    (`MemoryInjector(...) if self.config.ENABLE_MEMORY_INJECTION else None`).
  - **(b)** in `Conductor.chat()`, immediately **after** the initial
    `self.llm_messages = [LLMMessage(role=SYSTEM, content=get_sys_prompt())]` assignment: if the
    flag is on, call `self.memory_injector.get_injection(self.user_id, user_input)` and, when it
    returns a non-empty string, `append` it as one additional SYSTEM `LLMMessage`.
- **Flag:** `ENABLE_MEMORY_INJECTION` (SC-1).
- **Why unavoidable:** the prompt is assembled **only** here; this is the irreducible seam for any
  prompt-level injection. `self.user_id` and `user_input` are already in scope (no plumbing).
- **Footprint:** ~5 added lines across the two blocks; **single call** into `services/memory`
  (`get_injection`). No existing line changed.
- **Removal:** delete the two guarded blocks → conductor identical to upstream.
- **Refs:** D19; anchor = the `self.llm_messages = [sys_prompt]` line in `chat()`; TASKS WS5.

## Removability checklist (run before claiming "plugin removed")

- `git rm -r src/pneuma_seeker/services/memory` and `tests/memory`.
- Revert each `applied` entry above (SC-1, SC-2, …).
- `git diff` against the upstream base for the 🟡 files shows **no remaining changes**.
- (With the flag default off, an un-reverted plugin is already inert — removal is for cleanliness,
  not correctness.)

## When you add a new surgical edit

Add a new `SC-N` entry **before** writing the code, satisfying all five discipline rules. If an
edit cannot meet them (e.g. it must change an existing line, or needs more than a single call),
**stop and raise it with Ryan** — that is a sign the logic belongs in `services/memory/` instead.
