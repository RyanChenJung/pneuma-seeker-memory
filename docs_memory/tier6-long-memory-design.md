# Tier 6 — Long Memory (Procedural / Method Skeletons) — Build Spec (LOCKED v1)

> Status: **LOCKED 2026-06-11 (DECISIONS D17, refined by D18).** D18 simplified the v1 from an
> embedding/trajectory-RAG design to **inject-whole `.md`** (no embedding, no vector DB, no
> retrieval key). Background & boundary: `DECISIONS.md` D13 (verb-vs-noun split), D17 (first lock,
> reasoning trail), **D18 (what v1 actually builds)**; gap analysis: `code-vs-6tier-mapping.md`.
> Anchored on D11/D12 (interface-first, gitignored store, dumb-first), D16 (persistent priors,
> Enhancer-only-write, T2 = shared substrate), D14 (recurrence threshold).
> **This is the last tier — all six are locked.**

## Purpose (confirmed)
A persistent store of **reusable method skeletons** — *how to solve a class of problem*,
DB-agnostic (e.g. "cohort → index date → outcome window → aggregate"). T6 is the **verb**;
Tier 5 is the **noun** (how to read *this* DB). They compose at planning time: T6 supplies the
plan shape, T5 grounds it to physical tables. Read-only to frontline agents; written only by the
Enhancer, offline, distilled from the Tier 2 episodic log. T6 is one home of **tribal knowledge**
(how a *class* of problem should / should not be solved) — see the three north-star goals
(DECISIONS Glossary). **T6 does NOT solve latent intent** (that is T3/T4 context's job).

## The v1 = inject-whole md decision (D18-4) — the spine of this spec
**MVP T6 injects the method skeletons as `.md` straight into the planning prompt** (whole, or
coarse-tag-selected), exactly like the T3/T4-*learned* overlays. **No embedding, no vector DB, no
retrieval key, no operator-sequence, no problem-type classifier.**

Why: *"inject-whole vs retrieve"* depends **only** on whether the store is too big to inject and
not all of it relevant each time. At MVP T6 holds few skeletons → just inject them all. Crucially,
the embedding flaw that worried us — same surface words → different latent intent → a
**misleading** exemplar gets injected — **only exists when you select a subset by fuzzy
similarity. Inject-whole performs no selection, so the flaw does not exist at MVP.** The planner
sees the available method patterns and chooses; a wrong-fit skeleton is advisory, not binding.

The layering (only Layer 0 is built now):

| Layer | What | When | Status |
|-------|------|------|--------|
| **Layer 0 (MVP / real v1)** | inject-whole md (or coarse tag-filter) into the planning prompt | now | **BUILD** |
| **Layer 1** | add retrieval: key = embedding + operator-sequence, **conditioned on T3/T4 context** to disambiguate latent intent | only when the store outgrows the context budget | BACKLOG |
| **Layer 2 (v2)** | retrieval key = structured `problem_type` taxonomy (the user's true north) | taxonomy must be *discovered from accumulated T2* → cannot be first | BACKLOG |

Note Layer 1's embedding flaw is fixed by **conditioning the retrieval key on T3/T4 context**
(who's asking, which dept) — **not** by jumping to Layer 2. A `problem_type` classifier sees only
the question text and would face the *same* ambiguity; latent-intent disambiguation always comes
from T3/T4 context, regardless of layer.

## Entry shape — the explicit sextuple (D18-2)
The `system_architecture.md` §5 triplet/quadruplet is made explicit:

```
(intent, associated_experience, support, last_seen, type, source_episode)
```

| Element | Meaning | Notes |
|---------|---------|-------|
| `intent` | the deeper problem this memory addresses | renamed from `clinical_intent`; **v1 physical encoding = just the md text** (no embedding); Layer 1+ encodes it for matching |
| `associated_experience` | the worked example / anti-pattern body | the actual method skeleton or "don't do this" lesson |
| `support` | recurrence-weighted evidential weight | magnitude; see below + Glossary |
| `last_seen` | timestamp | **v1 writes it but does not read it**; the hook a future dormancy-decay / capacity-purge uses (BACKLOG) |
| `type` | **sign**: `positive exemplar` / `negative anti-pattern` | emulate vs avoid; **orthogonal to `support`, never fused** |
| `source_episode` | a Tier 2 episode id | **soft** back-pointer (audit), not a hard FK → **no retention lock on T2** |

- **`positive exemplar`** — a cleaned successful worked example, for few-shot *imitation*.
- **`negative anti-pattern`** — a distilled "don't do this" calibration lesson (mirrors T5's
  `negative_constraints[]`), e.g. *"for cohort-outcome questions, do not merge Admissions + IT
  scope — it over-broadens and gets rejected."*

`intent`, `associated_experience`, `support`, `last_seen`, `type`, `source_episode` are the
**shared sextuple** also used (in part) by T3/T4-learned and T5 edges — see D18-7 below.

## `support` (D6-2, refined by D18-5)
**`support` = recurrence-weighted importance** (NOT causal utility):
- Computed by the Enhancer **at distillation time**, from how often the lesson recurs across Tier
  2. Measured **source-side (T2)**, so free of the read-side feedback loop that poisons a usage
  count.
- **Causal credit-attribution deliberately dropped** — crediting one exemplar among several
  co-injected items is not cleanly solvable; a fake score is worse than none. `support` is a
  recurrence prior, not a measured utility. Revisit only with a clean attribution method → BACKLOG.
- **Known blind spot:** recurrence under-weights the **rare-but-critical** entry → BACKLOG.

### A/B validation is separate from `support` (D18-5)
`support` answers *"how much evidence / how important."* It does **not** decide conflicts. When the
Enhancer finds a new candidate that **partially overlaps** or **directly contradicts** a stored
record, it runs **A/B validation**: replay both versions against the **never-deleted Tier 2 log**
(the ground-truth corpus) and keep the winner — never blind-trusting the newer lesson. The
Enhancer's update logic is a 4-branch match of candidate vs stored record:

| Candidate vs stored | Action |
|---|---|
| no match | **INSERT** |
| exact same | **`support`++** |
| partial overlap | LLM **merge / split** → then **A/B** the merged result vs old |
| direct contradiction | **A/B** to pick the winner |

This is why **T2 is no-delete** (D18-6): it is the replay corpus A/B depends on. A/B cost: Enhancer
runs offline, so volume is tolerable; a future **sampled replay** (a few past episodes only) is the
reserved fallback if it gets too large (cost to be measured → BACKLOG).

## Success gate (D6-3) — two stages (unchanged by D18)
**Stage 1 — per-trajectory eligibility (cheap heuristics, from T2 fields, no "judge correctness"
LLM):**
- **Positive candidate:** trajectory terminated with a validated result (executed, returned, no
  error), clean path (few / no self-overturns).
- **Negative candidate:** a **ReAct self-overturn** event (went down X, abandoned it for Y — a
  localized self-correction inside one trajectory), OR terminal error / dead-end, OR **implicit
  user pushback** (see below).

**Stage 2 — aggregation + distillation:**
- Cluster candidates by problem-shape; apply a **recurrence threshold** (same as Tier 3's, D14) —
  singletons wait, only recurrent lessons promote. **Symmetric in v1** (asymmetry → BACKLOG).
- Then the **LLM distills** the cluster into one clean `positive exemplar` or
  `negative anti-pattern`.
- **LLM budget is bounded to "reaction-reading + distillation", never "judge correctness from
  scratch."**

### Implicit feedback — no explicit channel (D6-3)
Pneuma has **no accept/reject button**. The Enhancer reads the **next user turn's semantics / tone**
in Tier 2 as a soft signal (rejection: *"不對 / 不是這個 / 我是說…"*, an immediate re-ask, a
corrected parameter; acceptance: building on the result, drilling deeper, moving on).
- **Cheap and honest:** we never ask the LLM *"is the answer correct?"* (no ground truth). We ask
  *"did the human seem satisfied?"* — **the human is the ground truth, the LLM only parses the
  reaction.**
- **Soft probabilistic evidence into `support`, NOT a hard label.** Stage-2 recurrence washes out
  one-off misreads; only a *pattern* of pushback on the same reasoning accrues `support`.
- Shrinks the silent-error gap to "system AND user both missed it" → BACKLOG.

## Cross-tier routing of a correction (D6-4) — shared principle (unchanged)
The Enhancer is **one shared distiller** that routes each lesson to the tier matching its
**subject**: format/presentation → **T3** (user prefs) or **T4** (org conventions); reasoning-path
→ **T6**; physical-join → **T5**; a project-specific one-off never recurs → washed out.
**Recurrence is the universal noise filter** shared by T3 / T4 / T5 / T6.

## `LongMemory` interface (D6-5) — unchanged seam
Permission enforced by **two different clients**: frontline agents get a read-only client; the
Enhancer gets the only writable one.

**Read (frontline, read-only):**
- `get_exemplars(query, k)` → **positive** worked examples.
- `get_anti_patterns(query, k)` → **negative** constraints.
- v1 both return the inject-whole md set (filtered only by coarse tag if needed); `query`/k are the
  seam Layer 1 retrieval plugs into later. The `problem_type` arg is reserved (empty) for Layer 2.
- Both inject into the Conductor / Materializer planning prompt (T6 verb composes with T5 noun).

**Write (Enhancer only):**
- `distill(...)` — add / update an entry from a Tier 2 cluster (the 4-branch logic above).
- `reinforce_support(...)` — bump an entry's recurrence weight.

**Read path — inject-or-skip, no regression.** On a hit, inject the skeletons as few-shot context.
On a **miss / cold start** (empty store), inject nothing → planning proceeds on today's **static**
prompt factory, **identical to current behaviour, no regression.**

## Shared base record across T3–T6 (D18-7)
Reusing the T2 turn-envelope + step-event pattern (a common outer envelope carrying typed inner
payload):
```
BaseMemoryRecord = { support, last_seen, source_episode, type }     # all LEARNED records
  + experiential payload = { intent, associated_experience }        # T6 / T3-learned / T4-learned
  + T5 edge: shares the base, NOT intent; keeps its graph topology  # connection point is a fact
  ( T4-authored / T3-provisioned do NOT inherit the base — declarative, not experiential )
```
One Enhancer write path, one support/last_seen/decay/audit logic for everything learned; tier-
specific structure stays in the payload. **Not** one flat schema forced onto declarative or graph
memory.

## T6 ↔ T5 and T6 ↔ T2 boundaries (unchanged)
- **T6 vs T5:** verb vs noun. T6 = method skeleton (how to solve a *class*); T5 = navigation (how
  to read *this* DB). They compose, not overlap.
- **T6 vs T2:** T2 = the raw journal (every trajectory incl. failures + raw CoT); T6 = the
  **distilled, recurrence-gated, cleaned** exemplars / anti-patterns. T6 references T2 by soft
  `source_episode`; it never stores raw traces verbatim.

## v1 spec (minimal — simplicity first)
| Aspect | Design |
|--------|--------|
| Unit | sextuple `(intent, associated_experience, support, last_seen, type, source_episode)`; type ∈ {`positive exemplar`, `negative anti-pattern`} |
| **Read mechanism** | **inject-whole `.md`** into the planning prompt (Layer 0) — **no embedding, no retrieval key, no vector DB** |
| Score | **`support`** = recurrence-weighted evidential weight (Enhancer, source-side); no causal attribution; `last_seen` written-not-read (decay hook) |
| Sign vs magnitude | `type` = emulate/avoid; `support` = importance — never fused |
| Conflict resolution | Enhancer 4-branch (insert / `support`++ / merge-split / contradiction); partial-overlap + contradiction → **A/B replay against T2** |
| Backend | JSON/JSONL + md behind a **`LongMemory` interface**; gitignored local store; **embedding/vector store = Layer 1 deferred swap** |
| Write | Enhancer only (`distill` / `reinforce_support`); two-stage success gate; symmetric recurrence threshold |
| Success gate | Stage 1 heuristic eligibility (terminal state / ReAct self-overturn / implicit user pushback) → Stage 2 recurrence aggregation + LLM **distill** (never "judge correctness") |
| Permission | two clients: frontline read-only, Enhancer write-only seam |
| Provenance | soft `source_episode` → Tier 2; **no retention lock on T2** |

## Implementation notes for v1
- Store lives under the gitignored memory scratch dir (same pattern as D11/D12/D16); never
  committed/pushed.
- `LongMemory` is the single seam for the future Layer 1 embedding/retrieval swap — keep all I/O
  inside it; the `query`/`k`/`problem_type` args exist now but Layer 0 ignores them (returns the
  whole set / tag-filtered).
- The static prompt factories (`*/prompt_factory*.py`) are **not** T6 — T6 is a new, separate,
  persistent store that *feeds* skeletons into those prompts.

## Deferred to later versions (→ BACKLOG.md)
Layer 1 (embedding + operator-sequence retrieval, conditioned on T3/T4 context) once the store
outgrows the prompt budget; Layer 2 = v2 abstracted/parameterized plan templates keyed by a
structured `problem_type` taxonomy (discovered from T2); operator-sequence-skeleton generality
(unproven); rare-but-critical under-weighting by recurrence; silent semantic errors; asymmetric
recurrence threshold; causal credit attribution; A/B sampled-replay cost limit; vector/embedding
backend.
