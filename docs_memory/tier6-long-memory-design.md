# Tier 6 — Long Memory (Procedural / Method Skeletons) — Build Spec (LOCKED v1)

> Status: **LOCKED 2026-06-11 (DECISIONS D17).** Background & boundary: `DECISIONS.md` D13
> (T6 direction: verb-vs-noun split, v1 trajectory-RAG, v2 templates) + D17 (this lock); gap
> analysis: `code-vs-6tier-mapping.md` (Tier 6). Anchored on D11/D12 (interface-first,
> gitignored local store, dumb-first), D13/D16 (persistent priors, Enhancer-only-write, T2 =
> shared substrate, recurrence-gated) and D14 (recurrence threshold).
> **This is the last tier — all six are now locked.**

## Purpose (confirmed)
A persistent store of **reusable method skeletons** — *how to solve a class of problem*,
DB-agnostic (e.g. "cohort → index date → outcome window → aggregate"). T6 is the **verb**;
Tier 5 is the **noun** (how to read *this* DB). They compose at planning time: T6 supplies
the plan shape, T5 grounds it to physical tables. Read-only to frontline agents; written only
by the Enhancer, offline, distilled from the Tier 2 episodic log.

- **v1 = trajectory-RAG**: retrieve the most-similar past *successful* trajectory and inject it
  as a few-shot worked example. Concrete, needs no perfect abstraction.
- **v2 = abstracted, parameterized plan templates** keyed by a structured problem-type (the
  spec's "abstract procedural skills"). The abstraction is the Enhancer's hardest LLM job →
  deferred so T6 does not stall on it (D13). **This is the user's true-north direction.**

## Retrieval key (D6-1) — Option C for v1, Option B is the target
What we match the incoming NL question against to fetch exemplars.

- **v1 = hybrid (Option C):** embed the incoming **NL question** + match on a cheap
  **operator-sequence skeleton** read *directly* from the T2 trajectory (e.g.
  `join → filter-by-date → group-by → aggregate`). The skeleton is the ReAct step sequence —
  **no LLM abstraction needed**, so it does not pull the v2 work into v1, yet it describes the
  *method shape* (verb) rather than just the *surface nouns* of the question.
- **Reserved for v2:** a `problem_type` field on each entry, **empty in v1**, to be filled by a
  structured problem-type classifier and used to re-rank. Filling it is the v2 Enhancer job.
- **Why not pure NL embedding:** semantic similarity ≈ same *topic*, not same *method*; it is
  the design that collapses T6 into "a cache of past SQL by question similarity" (the D13 risk).
  The operator-sequence component is the cheap hedge against that collapse.
- **Why not full structured signature now:** it needs a problem-type classifier = the v2
  abstraction, which would stall v1 (and adds a runtime LLM classification, hurting the latency
  T6 exists to reduce).
- **Provisional:** the operator-sequence skeleton is kept but its **generality is unproven** —
  whether it is worth storing / general enough is an open question (BACKLOG). v1 uses it; v2
  may drop it in favour of the structured `problem_type`.

## Entry shape + `support` (D6-2)
Two entry **types** (sign), each carrying a `support` **score** (magnitude). Sign and magnitude
are **never fused** — the score says *how important / confident*, the type says *emulate vs
avoid*.

- **`positive exemplar`** — a cleaned successful worked example, for few-shot *imitation*.
- **`negative anti-pattern`** — a distilled "don't do this" calibration lesson (mirrors T5's
  `negative_constraints[]`), e.g. *"for cohort-outcome questions, do not merge Admissions + IT
  scope — it over-broadens and gets rejected."*

**`support` = recurrence-weighted importance** (NOT causal utility):
- Computed by the Enhancer **at distillation time**, from how often the lesson recurs across
  Tier 2. Measured on the **source side (T2)**, so it is free of the retrieval feedback loop
  that poisons a read-side usage-count (the retriever inflating its own favourites).
- **Causal `utility_score` is deliberately dropped:** crediting one exemplar among several
  co-injected items (+ T5 caveats + T4 facts) for a success is not cleanly solvable, and a fake
  score is worse than none. Revisit only if a clean attribution method appears (single-template
  injection / A-B) → BACKLOG.
- **Known blind spot:** frequency under-weights the **rare-but-critical** entry (a method used
  once that averted a disaster scores low). Same long-tail blind spot family as a usage-count,
  moved to the distillation side; accepted for v1 → BACKLOG.
- Every entry carries `source_episode` = a **Tier 2 episode id** as a **soft back-pointer**
  (audit / explainability), **not** a hard FK — distilled lessons are self-contained, so T6
  imposes **no retention lock on T2** (same decoupling as T5 / D16).

## Success gate (D6-3) — two stages
The gate is not a per-trajectory snap judgment; because `support` is a recurrence signal, it is
naturally two-stage.

**Stage 1 — per-trajectory eligibility (cheap heuristics, from T2 fields, no "judge correctness"
LLM):**
- **Positive candidate:** trajectory terminated with a validated result (executed, returned, no
  error), clean path (few / no self-overturns).
- **Negative candidate:** a **ReAct self-overturn** event (went down X, abandoned it for Y — a
  localized self-correction inside one trajectory, cheaper than waiting for a whole failed run),
  OR terminal error / dead-end, OR **implicit user pushback** (see below).

**Stage 2 — aggregation + distillation:**
- Cluster candidates by problem-shape; apply a **recurrence threshold** (same as Tier 3's,
  D14) — singletons wait, only recurrent lessons promote. **Symmetric in v1** (positive and
  negative use the same threshold; asymmetry deferred → BACKLOG).
- Then the **LLM distills** the cluster into one clean `positive exemplar` or
  `negative anti-pattern`.
- **LLM budget is bounded to "reaction-reading + distillation", never "judge correctness from
  scratch"** (the latter is D13's hardest job, avoided in v1).

### Implicit feedback — no explicit channel (D6-3)
Pneuma has **no accept/reject button**. Instead the Enhancer reads the **next user turn's
semantics / tone** in Tier 2 as a soft signal (rejection: *"不對 / 不是這個 / 我是說…"*, an
immediate re-ask, a corrected parameter, frustrated tone; acceptance: building on the result,
drilling deeper, moving on).

- **Why this is cheap and honest:** we do **not** ask the LLM *"is the answer correct?"* (no
  ground truth — the unreliable, expensive job). We ask *"did the human seem satisfied?"* — the
  **human is the ground truth**, the LLM only parses their reaction. A fundamentally more
  reliable LLM use.
- **Use it as soft, probabilistic evidence into `support`, NOT a hard label** — it is noisier
  than a button (silence is ambiguous; tone varies; a re-ask may be a new question). The Stage 2
  recurrence aggregation washes out one-off misreads; only a *pattern* of users pushing back on
  the same reasoning accrues `support`.
- **Shrinks the silent-semantic-error gap:** an answer that is silently wrong but that the user
  pushes back on in natural language is now caught. Only "system AND user both missed it"
  remains silent → BACKLOG.

## Cross-tier routing of a correction (D6-4) — shared principle
The Enhancer is **one shared distiller** that routes each lesson to the tier matching its
**subject** (generalises D16's "T2 = shared substrate"):

- dissatisfaction about **format / presentation** → **Tier 3** (user format prefs, D14) or
  **Tier 4** (learned org conventions, D15) — *not* T6.
- a **reasoning-path** lesson → **Tier 6**.
- a **physical-join** lesson → **Tier 5**.
- a purely **project-specific one-off** never recurs → never aggregates → washed out.

**Recurrence is the universal noise filter** shared by T3 / T4 / T5 / T6. This is what cleanly
keeps format gripes out of T6 (they route elsewhere) and keeps one-off noise out of every tier.

## `LongMemory` interface (D6-5)
The plugin seam. Permission enforced by **two different clients** (same as T5): frontline agents
get a read-only client; the Enhancer gets the only writable one.

**Read (frontline, read-only):**
- `get_exemplars(query, problem_type=None, k)` → ranked **positive** worked examples.
- `get_anti_patterns(query, problem_type=None, k)` → ranked **negative** constraints.
- Both inject into the Conductor / Materializer planning prompt (T6 verb composes with T5 noun).

**Write (Enhancer only):**
- `distill(...)` — add / update an entry from a Tier 2 cluster (positive or negative).
- `reinforce_support(...)` — bump an entry's recurrence weight.

**Read path — inject-or-skip, no regression.** On a hit, inject top-k exemplars + anti-patterns
as few-shot context. On a **miss / cold start**, inject nothing → planning proceeds on today's
**static** prompt factory, **identical to current behaviour, no regression** (same no-regression
principle as T5's heuristic fallback).

## T6 ↔ T5 and T6 ↔ T2 boundaries
- **T6 vs T5:** verb vs noun. T6 = method skeleton (DB-agnostic, how to solve a *class*); T5 =
  navigation (how to read *this* DB). They compose, not overlap.
- **T6 vs T2:** T2 = the raw journal (every trajectory incl. failures + raw CoT); T6 = the
  **distilled, recurrence-gated, cleaned** exemplars / anti-patterns derived from it. T6
  references T2 by soft `source_episode` pointer; it never stores raw traces verbatim.

## v1 spec (minimal — simplicity first)
| Aspect | Design |
|--------|--------|
| Unit | a method skeleton: `positive exemplar` or `negative anti-pattern` |
| Retrieval key | **v1 = Option C**: NL-question embedding + cheap operator-sequence skeleton from T2; `problem_type` field reserved (empty) for **v2 = Option B** (structured signature) |
| Score | **`support`** = recurrence-weighted importance (Enhancer, source-side); **no** causal `utility_score` |
| Sign vs magnitude | type = emulate/avoid; `support` = importance — never fused |
| Backend | JSON/JSONL behind a **`LongMemory` interface**; gitignored local store; **vector/embedding store = deferred backend swap** |
| Read | `get_exemplars` / `get_anti_patterns`; inject-or-skip into planning prompt; **no regression on miss** |
| Write | Enhancer only (`distill` / `reinforce_support`); two-stage success gate; symmetric recurrence threshold |
| Success gate | Stage 1 heuristic eligibility (terminal state / ReAct self-overturn / implicit user pushback) → Stage 2 recurrence aggregation + LLM **distill** (never "judge correctness") |
| Permission | two clients: frontline read-only, Enhancer write-only seam |
| Provenance | soft `source_episode` → Tier 2; **no retention lock on T2** |

## Implementation notes for v1
- Store lives under the gitignored memory scratch dir (same pattern as D11/D12/D16); never
  committed/pushed.
- `LongMemory` is the single seam for the future vector/embedding-store swap — keep all I/O
  inside it.
- Reserve the `problem_type` field in the entry schema now so the v2 structured-retrieval
  upgrade is a fill-in + re-rank, not a schema migration.
- The static prompt factories (`*/prompt_factory*.py`) are **not** T6 — T6 is a new, separate,
  persistent store that *feeds* exemplars into those prompts (per `code-vs-6tier-mapping.md`).

## Deferred to later versions (→ BACKLOG.md)
v2 abstracted/parameterized plan templates keyed by structured problem-type (Option B; the
hardest Enhancer LLM job); operator-sequence-skeleton generality (unproven); rare-but-critical
under-weighting by recurrence-based `support`; silent semantic errors (system AND user both
miss); asymmetric recurrence threshold (lower for negative anti-patterns); causal credit
attribution among co-injected exemplars; vector/embedding backend.
