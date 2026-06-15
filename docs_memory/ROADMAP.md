# Roadmap & Timeline — Memory Layer Project

> The "where we are going and by when" doc. **Project definition + milestone backbone**
> live here; per-tier *design* lives in the `tierN-*-design.md` specs and `DECISIONS.md`.
> This roadmap is **adjusted dynamically as progress dictates** — milestones are targets,
> not contracts. It superseded two outdated planning `.docx` files (now deleted). The one
> surviving `.docx` — the team-facing **Team Contract & Tasks (v2)** (bumped 2026-06-15 for the
> Option-B auth'd `/chat` contract, D27) — is a local-only export
> (git-ignored); its living source of truth is this roadmap + `scenario-spec-v1.md`.
> Cross-refs: [`CLAUDE.md`](../CLAUDE.md), [`DECISIONS.md`](DECISIONS.md) (Glossary = the
> three north-star goals, D18-1), [`code-vs-6tier-mapping.md`](code-vs-6tier-mapping.md),
> [`system_architecture.md`](system_architecture.md).

## Project definition (one screen)

**Problem.** For enterprise/campus data agents the bottleneck is not LLM capability — it is
the **semantic ambiguity of institutional knowledge**. The same metric word means different
things to different askers: "retention rate" is *student re-enrollment* to Admissions but
*retained capital / escrow* to Finance — different formulas, different ground-truth tables.
A vanilla text-to-SQL agent cannot resolve this, because it does not know *who is asking* or
*that department's conventions*, and it cannot read a *messy* DB correctly on its own.

**What we build.** A **decoupled memory-layer plugin** that sits between institutional
knowledge and the LLM. A vague query goes in; the plugin **injects the right context** so the
intent converges to the **correct ground-truth table** — with **zero intrusion** into Pneuma
core. Onboarding a new department = configure its knowledge layer; the core does not change.

**The three north-star goals** (full definitions: `DECISIONS.md` Glossary / D18-1):

| Goal | Plain words | Where it lives in the 6-tier design |
|---|---|---|
| **Latent intent** | Resolve a vague query by *who is asking* | T3 (personal focus) + T4 (dept/org overlay) |
| **Tribal knowledge** | Rules locked in people's heads, not visible from the schema | T4 authored (authoritative KB) + T3/T4 learned |
| **Schema knowledge** | Knowing how to read *this* (dirty) DB correctly: joins, value decoding, time traps | T5 schema graph (learn-by-correction) |

**The thesis to prove.** Same vague query + "I'm Admissions" → table A; same query + "I'm
Finance" → table B; **without** our layer → wrong table or many clarifying turns. The summer
work exists to validate this empirically against the Pneuma baseline.

**Self-evolution.** The target system is **self-evolving** (auto-captures tribal knowledge
from interactions and refines itself — this is core, not optional). **Fallback:** if behind
schedule, ship **static** injection first and add the self-evolving layer after. Static still
proves the *value* of injection; self-evolution proves we can *auto-learn* it instead of
hand-authoring.

## Milestone backbone

Targets, re-balanced as we go. Hours commitments drive sequencing (see note below).

| Milestone | Proves | Tiers exercised | Self-evolving? |
|---|---|---|---|
| **M1 · 7/5 — v0.1-MVP** (hard target) | **latent intent + tribal knowledge** | T4-authored (knowledge injection) + dept/user overlay (T3/T4); T1 session | ❌ **static first** (hand-authored knowledge injected) |
| **M2 · end Aug — self-evolving mechanism** | "gets smarter with use": auto-capture knowledge from dialogue, distil & write back; + token/latency lightweighting | T2 episodic log (capture) + **Enhancer** (synthesise → T3/T4) | ✅ this milestone *is* the self-evolving build |
| **M3 · end Sept — schema knowledge + PoC** | agent reads a dirty DB correctly (joins / value decode / time traps); + blind-test PoC; + counter-question/clarification logic | **T5 schema graph** (self-evolving via learn-by-correction) | ✅ |
| **M4 · Oct–Dec — real-world deployment** | UA / campus real data; Microsoft Fabric LLMOps; handover before Dec graduation | full stack, matured | ✅ (background; not detailed yet) |

### Design implications worth keeping in view

- **Static vs self-evolving splits cleanly on tribal knowledge.** M1 (static) proves
  *injecting* a hand-authored rule (e.g. "retention rate excludes transfer students") fixes a
  query the baseline gets wrong. M2 (self-evolving) proves the Enhancer can *auto-learn* that
  same rule from interactions instead of a human typing it. So the M1 static fallback does
  **not** weaken the thesis.
- **The validation dataset must be engineered to make the baseline fail.** If the synthetic
  data is too clean, the baseline answers correctly on its own and we prove nothing. So the
  dataset must deliberately contain: (a) ≥2 departments sharing an ambiguous term that resolves
  to different tables/formulas (→ latent intent); (b) rules **not** inferable from the schema
  (→ tribal knowledge); (c) **dirty** schema where naive interpretation joins/decodes wrong
  (→ schema knowledge). This is the first principle for the "scenario spec" the team builds from.
- **September is the team's high-capacity window.** Committed hours: in Sept the three
  teammates ramp to 40 hrs/wk while Ryan drops to 20. So the most teammate-heavy work
  (M3: dirty-schema dataset, blind-test PoC, full benchmark runs) is sequenced into September —
  with the grain of the hours, not against it.

### Committed weekly hours (from the team doc; re-declare if changed)

| Person | Jun | Jul–Aug | Sep |
|---|---|---|---|
| Ryan | 40 | 20 | 20 |
| Juan | 10 | 10 | 40 |
| Lawrence | 10 | 10 | 40 |
| Sola | 10 | 10 | 40 |

## Team roles & allocation

**Guiding principle.** Ryan owns the core **and the scenario spec** (the single source of
truth for the fake campus world). Each teammate owns one **decoupled module** and never needs
to read the memory internals or Pneuma to do their part. Every role is written in two buckets:

- 🔒 **MUST** — the hard contract. Violate it and the module won't plug into everyone else's.
- 🎛️ **FLEXIBLE** — their own zone; being *more* ambitious (e.g. more complexity) is welcome.

**The skeleton/flesh split.** The scenario spec fixes the *skeleton* (required tables,
canonical table/column **names**, the ground-truth semantics, which terms must be ambiguous,
which hidden rules must bite, the deliberate traps). Teammates build the *flesh* to that
skeleton and may enrich within their flexible zone. Canonical **names and semantics are fixed**
so the three modules stay mutually consistent without horizontal coordination.

**Shared facts for everyone.** Memory is an **in-process plugin inside Pneuma** (Pneuma is
already a FastAPI service — `/chat` etc.), toggled by an `ENABLE_MEMORY_*` flag. We do **not**
build a separate memory microservice. **Git/branch governance + PR safety = Ryan only** (this
is a fork; never push/PR to upstream — see `CLAUDE.md`); teammates branch `feature/*` and PR
into our integration branch. All teammate code lives in **our-owned dirs**, never upstream paths.

**How the experiment is set up (the context model).** "Who is asking" is **not** a query
parameter — it is the asking user's **identity = (department, role)**, held in a minimal **T3
provisioned** map `{user → (department, role)}` (a small config for M1; the *learned* half of T3
matures in M2). The memory layer reads the identity and injects that department's tribal
knowledge. Declaring identity is **not cheating** (it is a legitimately-known fact, exactly the
real logged-in-user setup); the cheating line is pre-supplying the *resolved formula / SQL /
answer* — which we never do. The agent still retrieves, reasons, and generates SQL; we only
supply institutional knowledge it cannot know on its own.
- **Shared visibility (authorization deferred — BACKLOG):** both departments' datasets
  are **co-searchable**, so an ambiguous term has real competing tables. Justification: real
  deployments restrict tables by role/dept, but that does not stop *two users with the same
  permissions and different purposes* — holding authorization constant and varying intent is
  exactly what latent intent must resolve.
- **Department is the crisp M1 axis** (dept → right table). **Role is a second axis, dosed
  small for M1:** role changes *presentation / granularity / default scope* (which is T3's
  format-preference territory), **not** the answer's table — so it neither collapses into
  authorization nor becomes contrived. 1–2 role-varying teaser cases in M1; role's main act is
  M2 (with learned format prefs).
- **Multi-turn from M1:** Pneuma already supports multi-turn, so the harness runs multi-turn
  and measures **clarifying-turn count** from M1 — memory-on should need *fewer* clarifying
  turns than baseline (a strong A/B signal). Counter-question *quality* refinement is M3.

### 🗂️ Sola — "The Sandbox" (campus data + ingestion)

Owns the synthetic campus world's **data** and getting it loaded into Pneuma.
- **M1 deliverable (end of Week 2, ~6/21 — hard gate for Ryan):** loadable **Admissions** +
  **Finance** DuckDB datasets + a one-shot load script + column-description metadata.
- **M3 (Sept, her 40 hr window):** a **dirtied** schema version (cryptic column names, broken
  join keys, `YYYYMM`-style date traps) to enable the schema-knowledge proof.

🔒 **MUST**
- **DuckDB only**, ingested via Pneuma's existing `ingest_csv.py` into
  `services/db/datasets/`; **verified loadable + queryable by Pneuma**. (No Postgres/MySQL —
  the docx was wrong; Pneuma reads DuckDB `.db` files.)
- Implement the **canonical tables/columns + ground-truth semantics exactly as the scenario
  spec states** (so Juan's test cases and Lawrence's scoring line up).
- The data must make the **hidden rules actually bite**: transfer students must exist (so
  "exclude transfers" changes the number); fiscal-vs-calendar year must change the answer; the
  ambiguous terms (`retention`, `yield`) must resolve to **different tables** per department.
  Data clean enough that the baseline already answers correctly proves nothing.
- **Both datasets must be co-loadable / co-searchable** (shared visibility) so the ambiguous terms have real
  competing tables — not isolated per-department instances.
- Provide **column descriptions / metadata** (Pneuma indexes these for retrieval).
- Stay in our-owned dirs; never touch upstream paths.

🎛️ **FLEXIBLE** (her call; more is welcome)
- Volume/scale, value distributions, naming realism, **extra tables/rows** — current target is
  ~hundreds of rows, 3 tables/dept; she may go bigger/more realistic.
- **Additional ambiguous terms or tribal rules** beyond the required `retention` + `yield`.
- Data-generation method (faker, scripts, etc.).
- The specific "mess" chosen for the M3 dirty version, within the trap categories.

Needs only: the scenario spec. Does not need: memory internals, Pneuma internals beyond
`ingest_csv.py` + `docker-compose up`.

> **Ryan's note to Sola — hunt for a real dataset.** Spend some of your own time researching
> whether a suitable real campus/open dataset exists; if one fits, the synthetic-generation step
> can be dropped. ⚠️ **Guardrail (Ryan's view):** a found dataset rarely contains *our engineered
> failure modes* (same term → different dept-meaning, schema-invisible rules, dirty joins), and
> those are the whole point — a too-clean real set proves nothing and we lose control of the
> traps. So: **time-box the search; synthetic stays the controlled path for the M1 thesis**; aim
> real data at **realism / schema-dirtiness (M3) and enterprise validation (M4)**, or **hybrid**
> (real schema backbone + curated ambiguities). The hunt must **not block the 7/5 MVP.**

### 📚 Juan — "The Domain Truth" (institutional knowledge + test set)

Owns the **meaning** of the campus world: the injectable business-logic definitions (the
tribal knowledge) and the ambiguous test queries with their ground-truth answers. Where Sola
makes a rule *able to bite* in the data, Juan *writes the rule down* — as injectable knowledge
and as the scoring key.
- **M1 deliverables (June, 2 departments — Admissions + Finance):**
  - **Tribal-knowledge JSON** — the T4-authored input: for each ambiguous term × department,
    the formula, target tables/columns, and the hidden rule.
  - **`test_cases.json`** — ~20 ambiguous queries, each labelled `{asking-user persona =
    (department, role), ground-truth answer}`. Includes some **multi-turn** cases and **1–2
    role-teaser** cases (same dept, different role → different presentation/granularity, not a
    different table). This is the eval baseline **and** Lawrence's scoring key.
- **Jul–Aug deliverable (part-time): onboard a 3rd department** (e.g. Registrar/HR) — author
  its knowledge layer + add its test cases. This **proves the plug-and-play scale-out claim**
  ("onboard a new dept = just configure its knowledge layer, zero core redesign") and fills his
  part-time window. (Replaces SOTA, which is dropped — see note below.)
- **Sept deliverable (40 hr): judge of self-evolution (M2).** As the domain-truth owner, verify
  whether the Enhancer's **auto-learned** tribal knowledge is actually correct — compare learned
  vs his authored ground truth, report divergences. The natural Phase-2 role for this seat.

🔒 **MUST**
- JSON matches **the format Ryan specifies** (T4-authored ingestion), or memory can't load it.
- Definitions **exactly match the scenario spec's canonical semantics** and reference Sola's
  canonical table/column names — else injection points at the wrong table / ground truth
  diverges from the data.
- **Ground truth = the correct target table + whether the right rule was applied** (not an
  exact number). This is the definition of "intent convergence success" Lawrence scores against.
  *Consequence:* Juan writes `test_cases.json` from the **scenario spec alone** — no dependency
  on Sola's data; both build off the spec and meet at Ryan.
- Queries must be **genuinely ambiguous** (resolvable only with the asker's identity — dept,
  and for the teaser cases, role).
- Stay in our-owned dirs.

🎛️ **FLEXIBLE**
- Number of test cases (~20 target, more welcome), phrasing/variety of the ambiguous queries.
- Extra tribal rules/definitions beyond the required set (must stay consistent with the spec).
- How deep/realistic the business-logic write-ups are.

Needs only: the scenario spec + Ryan's JSON-format contract. Does not need: memory internals,
Pneuma internals, or Sola's data (thanks to table+rule ground truth).

> **SOTA research (context caching / prompt pruning, e.g. LLMLingua) is DROPPED** as a Juan
> deliverable — a shallow SOTA survey does not advance Ryan's development. **Measure vs reduce —
> keep them separate:** *measuring + recording* token & latency is **already Lawrence's** (core
> metrics in his telemetry pipeline). What is unowned is *reducing* them (lightweighting) —
> owner = **Ryan, just-in-time**, driven by Lawrence's numbers when a real cost problem appears
> (not a speculative survey).

### 🚀 Lawrence — "The Judge" (benchmark + telemetry)

Owns **measurement**: an automated **black-box** pipeline that drives Pneuma's `/chat` over
Juan's test set, memory **off (baseline) vs on**, captures metrics, and reports.
- **M1 deliverable:** harness scaffolded against the `/chat` contract (can build against a stub
  before the MVP exists), then hooked to v0.1-MVP — first full **A/B run + report**.
- **M3 (Sept, 40 hr):** full benchmark runs including the dirty-schema (schema-knowledge) cases
  and larger scale; comparison reports.

**Metrics (the thesis dimensions):** intent-convergence **success rate** (right table + right
rule, per Juan's ground truth) · **token** consumption · **latency** · **clarifying-turn count**.

🔒 **MUST**
- Benchmark target = **Pneuma's own `/chat`** (no separate service), run memory **OFF vs ON**
  via the `ENABLE_MEMORY_*` flag — the A/B comparison is the whole point.
- **Set the asking-user identity (department, role)** per Pneuma's session/user mechanism, using
  Ryan's invocation contract — so each case runs "as" the right persona.
- **Black-box**: only talk to `/chat` over HTTP; never reach into memory internals.
- Read **Juan's `test_cases.json`**; score success against its ground-truth labels (table + rule).
- **Multi-turn capable from M1**; measure clarifying-turn count.
- Output the agreed metric set so OFF vs ON are comparable.
- Stay in our-owned dirs.

🎛️ **FLEXIBLE**
- Tooling (asyncio/aiohttp/locust/pytest), report format (CSV/MD/dashboard), concurrency/load
  patterns, harness structure, extra metrics beyond the required set.

Needs only: Juan's `test_cases.json` + Ryan's `/chat` invocation contract (how to set the
persona, how to toggle the flag). Does not need: memory internals, domain logic.

> **Workload-balance pass — DONE.** Juan (the light seat after SOTA dropped) reinforced with a
> full arc: M1 = 2-dept knowledge + tests; Jul–Aug = onboard a 3rd department (proves
> plug-and-play scale-out); Sept = judge of self-evolution. Sola/Lawrence keep their
> milestone-driven rhythm. **The two outdated planning `.docx` were deleted** (2026-06-12, per
> Ryan); only the team-facing **Team Contract & Tasks (v2).docx** survives as a local-only
> (git-ignored) export of this roadmap + `scenario-spec-v1.md`.

## Weekly task breakdown — next 4 weeks

**Cadence (standing rule):** every teammate delivers their week's artifact **every Wednesday**.
Next four deliverable dates: **6/17, 6/24, 7/1, 7/8** (v0.1-MVP freeze = 7/5, inside W4).
Beyond 7/8 is deferred — planned later. **Hard dependency:** Ryan publishes the **scenario spec
v1 + the 3 contracts by ~6/15** so the 6/17 deliverables can be built against it; until then the
spec is the gate for everyone.

### 🔧 Ryan — Core (40 hr)
- **W1 → 6/17:** clone/build/**run Pneuma locally**; **locate the injection hook** (where the
  prompt is assembled before the LLM call); confirm how `/chat` sets the **user identity
  (dept, role)**. **Author scenario spec v1** + **publish the 3 contracts** (Sola schema /
  Juan JSON+test format / Lawrence `/chat` invocation). ← the keystone that unblocks everyone.
- **W2 → 6/24:** scaffold `services/memory/` + `ENABLE_MEMORY_*` flag; minimal **T3** (provisioned
  `{user → (dept, role)}`); **T4-authored** loader (ingests Juan's JSON); **walking skeleton**
  (stub injection wired into the hook, behind the flag, end-to-end callable).
- **W3 → 7/1:** real T4-authored **injection into the hook**; integrate **Sola's datasets**
  (co-searchable); end-to-end on the 2-dept data: ambiguous query + persona → right table.
- **W4 → 7/8 (freeze 7/5):** integrate **Lawrence's pipeline**; run the A/B; fix; **freeze v0.1-MVP**.

### 🗂️ Sola — Sandbox (10 hr)
- **W1 → 6/17:** Pneuma running + understand `ingest_csv.py`/`datasets`; from the spec, **draft
  the Admissions+Finance schemas** (tables/cols + descriptions); ingest a tiny sample into DuckDB,
  verified loadable. *(Time-boxed: begin the real-dataset hunt.)*
- **W2 → 6/24 (hard gate):** full synthetic data for both depts (~hundreds of rows), rules
  embedded (transfers exist; fiscal-year shifts answers), **co-searchable**; **deliver loadable
  datasets + load script + column metadata to Ryan.**
- **W3 → 7/1:** support integration — fix data issues Ryan/Lawrence surface; verify queries
  return the expected ground truth.
- **W4 → 7/8:** co-test the MVP; stabilise the datasets for the A/B run.

### 📚 Juan — Domain Truth (10 hr)
- **W1 → 6/17:** from the spec, **draft the tribal-knowledge JSON** (retention + yield × 2 depts:
  formula, target tables/cols, hidden rule) in Ryan's format.
- **W2 → 6/24 (hard gate):** finalise the knowledge JSON + author **~20 `test_cases.json`**
  (persona-labelled, ground truth = table + rule, incl. multi-turn + 1–2 role teasers);
  **deliver both to Ryan + Lawrence.**
- **W3 → 7/1:** co-audit MVP outputs vs the test cases; fix queries that don't actually trip the
  baseline; tighten ground-truth labels.
- **W4 → 7/8:** final eval audit; sign off that the test set genuinely exercises latent-intent +
  tribal-knowledge.

### 🚀 Lawrence — Judge (10 hr)
- **W1 → 6/17:** stand up the isolated async **harness project** (tooling chosen); build the
  `test_cases.json` **parser** against the agreed schema.
- **W2 → 6/24:** build the `/chat` caller (against a **stub** if MVP isn't ready) + metric capture
  (success / token / latency / turns) + the **memory OFF/ON** toggle; runs end-to-end on the stub.
- **W3 → 7/1:** hook to the **real MVP** endpoint; first real **A/B run** on Juan's test set;
  CSV/MD report.
- **W4 → 7/8:** full A/B run on v0.1-MVP; **deliver the Phase-1 benchmark report** (baseline vs
  memory).

> **After 7/8: deferred** — break down once M1 lands and we see the real numbers.

## Reconciliations with the outdated .docx

- **Integration shape — RESOLVED.** Pneuma is **already a FastAPI service**
  (`src/pneuma_seeker/main.py`, `/chat` NDJSON stream, `/index`, `/provenance`). Our memory is
  an **in-process plugin inside Pneuma** (additive `ENABLE_MEMORY_*` hooks), **not** a separate
  service. The Analyst benchmarks by driving Pneuma's own `/chat` with the flag **off (baseline)
  vs on (Pneuma + memory)** — the `ENABLE_MEMORY_*` flag is the A/B switch. The docx's standalone
  `/api/v1/context/inject` FastAPI service is **superseded / dropped**.
- **DB engine — RESOLVED.** Pneuma uses **DuckDB** (`.db` per dataset, ingested from CSV via
  `services/db/datasets/ingest_csv.py`), **not** Postgres/MySQL. The docx's DB-server tasks are
  superseded; Sola produces DuckDB datasets.
- **"Compress / remove outdated records"** (docx self-evolving description) **contradicts**
  `DECISIONS.md` D18-6 (**T2 = no-delete**, it is the A/B replay corpus). The docx language is
  superseded; the no-delete decision stands.
