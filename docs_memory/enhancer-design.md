# Enhancer — Background Synthesizer — Build Spec (LOCKED v1)

> Status: **LOCKED 2026-06-13.** Trail: `DECISIONS.md` **D20** (Level × Tier architecture, the
> Enhancer's place in it) → **D21** (success gate, recurrence = `support`, self-correction) →
> **D22** (A/B conflict resolution, the honesty criterion) → **D23** (LLM budget + pipeline). Big
> picture & diagram: `level-tier-design.md`. Per-tier specs it writes into:
> `tier3..tier6-*-design.md`; its input log: `tier2-episodic-log-design.md`. Deferred items:
> `BACKLOG.md`.
>
> The Enhancer is the **verb** of the memory layer. The tiers (T1–T6) are the *nouns* (stores);
> the Enhancer is the single **writer** that reads raw experience and synthesises the persistent
> priors. Keeping noun and verb separate is what dissolved the early "memory vs Enhancer got mixed
> up" confusion (D20). Frontline agents (Conductor/Materializer) stay **read-only**; only the
> Enhancer writes T3–T6.

## Purpose (confirmed)
Turn the raw, messy **Tier 2 episodic log** into clean, reusable, persistent memory (T3–T6),
**offline** and **incrementally**. It is where learning happens: `conversation → T2 capture →
Enhancer → a persistent record → next conversation injects it → observable behaviour change`.
It must do this **without ever judging whether an answer was correct** — the human's recorded
reaction is the ground truth (D22).

## Position in the architecture (D20)
The Enhancer is **one algorithm with two modes**; each memory holder (User / Department /
Institution) owns its own Enhancer:

- **DISTILL mode (User-Enhancer)** — reads **raw T2** → needs the full eligibility gate + LLM
  distillation → writes the user's own T3–T6. **This spec is the DISTILL mode.**
- **AGGREGATE/PROMOTE mode (Dept- & Inst-Enhancer)** — reads the level-below's **already-distilled**
  memory → **no eligibility gate** → promotes what enough members share. Counting unit changes per
  level (User = one person repeats; Dept = how many users share; Inst = how many depts share).
  **Deferred** — its input is user memory, which does not exist until the User level works.

**MVP = User level only, DISTILL mode, T3 meaning first** (D20/D22). Close the smallest learning
loop end-to-end for one persona before any aggregation.

---

## The pipeline (the spine)
One User-Enhancer run, processing only episodes newer than `processed_at` (incremental, never
re-scans consumed T2 — D21; the lone exception is A/B replay, which re-reads a T2 slice):

```
T2 raw episodes (since processed_at)
   │
 ① STAGE 1 — eligibility gate        (per trajectory; keep/drop + polarity)
   │
 ② STAGE 2a — cluster                (one batched LLM pass: form the groups)
   │
 ② STAGE 2b — distill                (one focused LLM call per cluster → a candidate record)
   │
 ③ 4-BRANCH UPDATE                   (cheap neighbour detect → LLM relation judge → resolve)
   │
 ④ WRITE                             (program writes the record(s); advance processed_at)
```

### The unifying principle (D23) — who does what
> **The LLM only does language understanding** (cluster, distill, judge a relation, read reactions,
> restructure). **The program does everything mechanical** (count, look up neighbours, gather a
> slice, tally votes, write). **The final verdict of any conflict is always a program tally**, so
> the LLM can never sneak a from-scratch correctness judgement — the **D22 honesty red line, made
> mechanical**.

---

## ① Stage 1 — eligibility gate (D21)
Decides *worth-learning + which polarity* — **never** answer-correctness. Per trajectory, reads
existing T2 fields:

- **Positive** = clean terminal success (executed, returned, no error, few/no self-overturns).
- **Negative** = an **SQL/exec error** OR a **ReAct self-overturn** OR **implicit user pushback**
  (next-turn reaction). All three negative sources kept.
- Drops: no terminal state (interrupted mid-trajectory), pure chit-chat, knowledge-irrelevant.

**Stage 1 need not be precise.** The real filters are the Stage-2 LLM + the recurrence
threshold; and implicit pushback **alone** never mints a negative record (that needs an objective
failure signal — see self-correction below), so a false positive merely down-weights a good lesson,
which recurrence then recovers.

**Implicit-pushback detection uses an LLM for now (D23 amends D21).** At this validation stage,
efficacy beats cost; the cheap no-LLM path (behavioural signals — "no positive ack + immediate
near-duplicate re-ask" — + a negation/correction lexicon + an optional small local classifier) is
the cost-optimisation BACKLOG.

---

## ② Stage 2 — cluster + recurrence + distill (D21, D23)

### 2a. Cluster — one batched LLM pass (D21, D23 #1)
The **LLM forms the groups** (this replaces the earlier hand-tuned structural-fingerprint idea,
which over-baked `department` and over-engineered a per-user job). Clustering is inherently a
**global view** — you cannot group fragments you see one at a time — so it is one batched pass.
Affordable because per-user candidate volume is small. Bounded by the context cap (§ Context cap).

### 2b. Distill — one focused call per cluster, **pure** (D23 #1/#2/#3)
One LLM call per cluster keeps each call focused on a single lesson (cleanest output). The call is
**pure**: it sees only the new cluster and emits one **candidate** record; it does **not** look at
stored records (that is the separate 4-branch step).

**Field ownership** — the record is the sextuple (D18-2), reused as a shared base record across
tiers (D18-7), + `tier`:

| field | filled by | how |
|---|---|---|
| `tier` | **LLM** | routing **folded into distill** as an output field (D23 #2) — no separate routing step |
| `intent` | **LLM** | the operative intent (needs language understanding) |
| `associated_experience` | **LLM** | the experience/approach tied to that intent |
| `type` | **inherited** | from the Stage-1 polarity tag (not re-judged) |
| `support` | **program** | = cluster size (the recurrence count itself) |
| `last_seen` | **program** | = max timestamp in the cluster |
| `source_episode` | **program** | = the cluster's member episode ids (the soft back-pointer) |

**The distill verb (the D22 red line):** *"Summarise the recurring lesson from these episodes,
grounded in what actually happened and how the human reacted. The human reaction is the ground
truth. Do NOT judge whether the answer was correct."*

**Why tier-as-output-field is safe (D23 #2):** the cross-tier association (a T3 meaning, a T5 join,
a T6 method born from the same conversation) is preserved by all three records carrying the same
`source_episode` into the **no-delete T2** (D18-6/7) — not by holding tiers in one LLM call. Mixing
tiers in one call would also risk bleeding *meaning* into a T5 join record, violating the D16
boundary (T5 = evidence-first joins; meaning lives in T3/T4).

### Recurrence threshold (D21)
`support` **is** the recurrence count; the **REINFORCE** branch's `support`++ **is** the increment.
A record **solidifies (becomes injectable) at `support` ≥ N = 3**; below that it is pending/observing
(not yet injected). (Exact N and positive/negative asymmetry are tunable → BACKLOG.)

### Self-correction → two records (D21)
A ReAct self-overturn yields the abandoned path → **negative anti-pattern** and the recovery path →
**positive exemplar** (the *capability* to self-correct is not stored). **Mint the negative ONLY
when there is an objective failure signal** (error / empty result / validation fail); a pure
preference-switch with no objective failure → a **weak positive only, no negative**.

---

## ③ 4-branch update (D22 names, D23 placement)
The pure candidate from 2b is reconciled against stored records. **Cheap similarity is only a
neighbour detector**; all relation judgements are the LLM's.

```
candidate record
   │  cheap similarity = neighbour detector
   ├─ no neighbour ───────────→ INSERT      add it                              [program, no LLM]
   └─ has neighbour → LLM judges the relation:
        ├─ exact same lesson ──→ REINFORCE  support++                           [program writes]
        ├─ partial overlap ───→ MERGE       (see below)
        └─ direct contradiction → ARBITRATE (D25 authority pre-filter → A/B; see below)
```

**REINFORCE is an LLM verdict, not a similarity threshold (D23 #4).** Embedding measures *topical*
closeness, so a contradiction ("retention = fall-to-fall" vs "= spring-to-spring") scores ~0.95;
a similarity gate would mis-fire it as REINFORCE and reinforce a stale definition instead of
arbitrating the correction — the worst error for the T3 meaning loop. So once there is *any*
neighbour, even REINFORCE goes through the LLM. (A cheap near-exact-text REINFORCE shortcut →
BACKLOG.)

### ARBITRATE — authority pre-filter (D25): route by record type *before* any replay
**Generating principle:** authority governs **declarations** (authored records) only; the moment both
sides are **operative** (learned), authority steps out and recorded reactions decide. Authority = a
**prior** ("whose declaration to trust with no behavioural oracle"); reactions = the **evidence** — two
halves of one update, not competing judges. Authority only *weights a declaration source*, it **never**
emits a "which answer is correct" verdict (the D22 honesty line, kept). At ARBITRATE entry (contradiction
already confirmed by the relation-judge LLM), branch on the two records' type — **all program, no new LLM:**

```
ARBITRATE (contradiction confirmed)
   ├─ authored × authored → program compares `authority`; higher wins;          [no replay]
   │                         equal/unclear → `contested` → surface ("consult users")
   │                         (loser marked superseded w/ provenance, not hard-deleted)
   ├─ authored × learned  → do NOT auto-resolve. Tally the contradiction as       [no replay]
   │   (= divergence, C)     negative-`support` vs the authored record (D18-8 trust erosion);
   │                         surface as a DIVERGENCE only at recurrence N=3 (D21), not on
   │                         the first counter-example. "learned > authored" made observable.
   └─ learned × learned   → authority does NOT intervene → run the full reaction   [replay]
                            A/B replay below. (This is the only route that pays the replay.)
```

**Cost is a side effect, not the motive (effectiveness-first):** this pre-filter is primarily *routing*
(it *is* how option C is implemented); that the batched-LLM replay now runs only for `learned × learned`
falls out for free — it **adds no LLM calls, only removes them** (consistent with D23's deferred cost
cap). Authority data = the authored record's metadata tag (D15-Q2), derivable from the author's
T3-provisioned `role/grade` (D14); hierarchy = the Level structure (D20). Senior-user weighting inside
`learned × learned` + finer authority-gap tuning → BACKLOG.

### ARBITRATE — contradiction → A/B (Option B, D22) — for meaning (T3/T4/T6), `learned × learned`
**Re-READ, never re-run.** Grade against an **already-recorded human reaction** (the honesty
criterion: a winner is honest iff decided by recorded reaction or an objective oracle, never by a
model's from-scratch "which is correct").

1. **Program** gathers the T2 slice = both records' `source_episode` ∪ recent same-feature episodes.
2. **One batched LLM call** reads each episode's `(method actually used → human reaction)` and votes
   `favours-A / favours-B / abstain`. Batched because the per-episode task is identical and simple,
   and seeing them together helps read the time trend.
3. **Program** does the **time-weighted tally** (recent-dominant evidence can win on less volume →
   handles a genuine regime change vs noise; `support`-volume alone is *not* A/B, D22) → verdict:
   `replace` / `keep-old` / `contested` (mark and wait).
4. If both versions were **independently accepted in different contexts**, that is a **hidden context
   split** → route to MERGE.

The **deterministic discrimination pre-filter is CUT for MVP** (D23): it only drops episodes where A
and B compute the same result, only works for *operationalisable* (executable) meaning, never
applies to pure-text meaning, and is fully covered by the LLM's `abstain` vote → BACKLOG (a cost
optimisation for executable cases).

### ARBITRATE — for execution/join (T5) → objective DB re-test (D22)
Actually run the candidate joins against the DB; grade by deterministic validity (executes /
non-empty / no fan-out / referential consistency). The DB is the oracle — no human, no correctness
judge. **Designed now, built when T5 learning is built** (needs offline DB access).

### MERGE — partial overlap (or an ARBITRATE bounce-back) (D22, D23)
1. **LLM restructures**: merge into one richer record, or split into two **context-scoped** records.
   The distinguishing context is **read from the episodes**, not invented; the LLM reorganises, it
   does not judge correctness.
2. **Always run the A/B validation** (reuse the ARBITRATE Option-B machinery): for an additive merge
   it harmlessly abstains (nothing competes); for a split it **confirms each branch holds in its own
   context**. (Conditional-skip of the additive-merge A/B → BACKLOG.)
3. **Program** writes: one merged record / two split records / `contested` if it fails to validate.

### Cross-tier routing principle (D6-4)
The Enhancer routes a lesson by **subject**: format → T3/T4, reasoning/method → T6, join → T5.
**Recurrence is the universal noise filter** across T3–T6.

---

## ④ Write
The program writes the resolved record(s) to the correct tier's **Enhancer-only write client**
(every persistent tier exposes a read client for frontline agents and a separate write client for
the Enhancer — D16). Then it advances `processed_at` (a pure progress marker; T2 is never deleted —
D18-6).

---

## Context cap / chunking (D23 #5)
- The **cost** cap (limit calls per run to save money) is **deferred** — effectiveness-first stage.
- The **input** cap is a hard physical limit: the cluster pass (2a) must fit the context window.
  **MVP does not implement chunking** (User-level volume is small → not on the hot path).
- **Reserved fallback when it is ever hit:** cheap embedding **pre-bucketing** (keep likely-same
  fragments together) → LLM does the **final** clustering within each bucket. This does *not* violate
  D21 (which only forbids embedding *replacing* LLM clustering). → BACKLOG.

---

## What this spec deliberately defers (→ BACKLOG)
- Cheap no-LLM implicit-pushback detection (cost optimisation; LLM used now). *(D23)*
- Per-run **cost** cap; context-cap **chunking** (pre-bucketing). *(D23)*
- Near-exact-text **REINFORCE shortcut**; conditional-skip of additive-merge A/B. *(D23)*
- Deterministic A/B **discrimination pre-filter** for executable meaning. *(D22, D23)*
- A/B **sampled replay** if a slice gets too large. *(D18, D22)*
- **AGGREGATE/PROMOTE** mode (Dept/Inst Enhancers) — built after the User loop works. *(D20)*
- T5 objective DB re-test — designed, built with T5 learning. *(D22)*
- Asymmetric / tunable recurrence threshold N. *(D17, D21)*

## MVP success criterion
For one persona, end-to-end: a recurring T3-meaning lesson is captured from T2, distilled, written
at `support` ≥ 3, injected into the next conversation, and produces an **observable behaviour
change** — with the A/B (Option B) loop correctly arbitrating a user's later correction of that
meaning.
