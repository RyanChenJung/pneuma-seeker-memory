# Scenario Spec v1 — The Fake Campus World

> **The single blueprint** every teammate builds against. Ryan owns this file.
> It fixes the *skeleton* (canonical table/column **names**, ground-truth semantics,
> which terms are ambiguous, which hidden rules must bite, the deliberate traps) so the
> three modules (Sola data / Juan knowledge+tests / Lawrence benchmark) stay mutually
> consistent **without horizontal coordination**. Build the *flesh* to this skeleton;
> enrich within your 🎛️ FLEXIBLE zone (see `ROADMAP.md`).
>
> Cross-refs: [`ROADMAP.md`](ROADMAP.md) (roles, milestones), [`DECISIONS.md`](DECISIONS.md)
> (Glossary = the three north-star goals, D18-1).
> **Status:** v1 draft for the 6/17 deliverables. Hard dependency for everyone's W1.
>
> **✅ 2026-06-15 — API drift RESOLVED (D27 = Option B).** The `upstream/prod` sync changed
> `/chat` (Bearer-token auth; `user_id` from the authenticated user, not the body; `dataset_name`
> required; server keeps history). **Decision: the harness targets the new auth'd API** (D27).
> §6.3 Contract C below has been **rewritten to the B wire shape** (token header + `personas.json`
> + `dataset_name:"campus"` + send-only-new-turn). The team `.docx` is bumped to **v2** to match.

---

## 1. The world

A single fictional university. Two departments, **co-loaded and co-searchable** (shared visibility):

- **Admissions** — student application, admission, matriculation, retention.
- **Finance** — funds, transactions, investments.

Both datasets are loaded into the **same** Pneuma instance and are searchable together, so
an ambiguous term has **real competing tables** across departments. Authorization (who may
*see* which table) is deliberately **deferred** — we hold permissions constant and vary only
*intent*, which is exactly what latent intent must resolve.

**The thesis this world exists to prove:** the same vague query + "I'm Admissions" → table A;
the same query + "I'm Finance" → table B; without the memory layer → wrong table or many
clarifying turns.

---

## 2. The two ambiguous terms (the heart)

Two metric words mean **different things in different departments** → resolve to **different
tables** with **different formulas** and **different hidden rules**.

| Term | Admissions meaning | Finance meaning |
|---|---|---|
| **retention** | First-year cohort re-enrollment rate (did last year's freshmen come back?) → `enrollments` + `students` | Share of received funds kept rather than disbursed → `transactions` + `funds` |
| **yield** | Admission yield: of admitted applicants, the share who matriculate → `applications` | Investment return rate on invested principal → `investments` |

### 2.1 Admissions · retention
- **Definition:** of the first-time first-year students in cohort year *Y*, the fraction
  still enrolled in fall of *Y+1*.
- **Formula:** `count(cohort students enrolled in Y+1) / count(first-time first-year students in cohort Y)`
- **Target tables:** `students` (cohort membership), `enrollments` (re-enrollment flag).
- **🔒 Hidden rule (tribal knowledge — invisible from schema):** **exclude transfer students**
  (`is_transfer = true`) from the cohort denominator. Standard IPEDS-style rule; the schema
  alone gives no hint. Without it the number is wrong.

### 2.2 Admissions · yield
- **Definition:** of admitted applicants, the fraction who matriculate (enroll).
- **Formula:** `count(applications where enrolled = true) / count(applications where decision = 'admitted')`
- **Target table:** `applications`.
- **🔒 Hidden rule:** only **degree-seeking** applicants count (`is_degree_seeking = true`);
  non-degree/visiting applicants are excluded from both numerator and denominator.

### 2.3 Finance · retention
- **Definition:** of funds received in a fiscal year, the share retained (not disbursed).
- **Formula:** `sum(amount where txn_type = 'retained') / sum(amount where txn_type = 'inflow')`
  over the fiscal year.
- **Target tables:** `transactions`, `funds`.
- **🔒 Hidden rule:** the **fiscal year is July 1 – June 30**, not the calendar year. Period
  filtering must use the fiscal calendar; using Jan–Dec gives the wrong window and wrong answer.

### 2.4 Finance · yield
- **Definition:** return rate on invested principal over a period.
- **Formula:** `sum(return_amount) / sum(principal)` over the period.
- **Target table:** `investments`.
- **🔒 Hidden rule:** only **realized** returns count (`is_realized = true`); unrealized /
  mark-to-market gains are excluded.

---

## 3. The three deliberate traps

The validation data must be engineered to make the **baseline fail** (clean data proves nothing).

1. **Same term → different table (latent intent).** `retention` and `yield` each resolve to a
   different table per department (§2). Resolvable only by knowing *who is asking*.
2. **Schema-invisible rule (tribal knowledge).** Each of the four metrics carries a 🔒 hidden
   rule (exclude transfers / degree-seeking only / fiscal-year Jul–Jun / realized only) that
   cannot be inferred from column names — it must be **injected**. The data must make the rule
   **bite**: transfer students must exist, non-degree applicants must exist, transactions must
   straddle the calendar/fiscal-year boundary, unrealized returns must exist.
3. **Dirty schema (schema knowledge — mainly M3, designed-in now).** v1 ships a **clean**
   schema, but the canonical design must be **dirtiable** without changing semantics: a person's
   id differs across tables (`applications.applicant_id` vs `enrollments.student_id` are the same
   human in different id spaces → join trap), periods stored as opaque strings (`fiscal_period`)
   → date trap, and columns that can later be renamed to cryptic codes. Sola produces the dirty
   version in September; v1 only needs the clean schema laid out so the M3 dirtying is mechanical.

---

## 4. Canonical schema (skeleton)

Names and semantics are **fixed**. Sola implements exactly these names/types; Juan references
them; Lawrence never touches them. Columns marked **[rule]** are what makes a hidden rule bite.
Sola may add columns/rows/realism (🎛️) but **must not rename or drop** these.

### 4.1 Admissions

**`applications`** — one row per application.
| column | type | notes |
|---|---|---|
| `application_id` | TEXT | PK |
| `applicant_id` | TEXT | the person (id space A — join trap seed) |
| `term` | TEXT | e.g. `2024-Fall` |
| `decision` | TEXT | `admitted` / `denied` / `waitlisted` |
| `enrolled` | BOOLEAN | did the admit matriculate |
| `is_degree_seeking` | BOOLEAN | **[rule: yield]** |
| `is_transfer` | BOOLEAN | transfer applicant |
| `residency` | TEXT | filler/realism |

**`students`** — one row per matriculated student.
| column | type | notes |
|---|---|---|
| `student_id` | TEXT | PK (id space B — join trap seed) |
| `applicant_id` | TEXT | links back to `applications` (same person, different space) |
| `cohort_year` | INTEGER | year first enrolled |
| `is_transfer` | BOOLEAN | **[rule: retention]** |
| `program` | TEXT | filler/realism |

**`enrollments`** — one row per student per term.
| column | type | notes |
|---|---|---|
| `enrollment_id` | TEXT | PK |
| `student_id` | TEXT | FK → `students` |
| `term` | TEXT | e.g. `2025-Fall` |
| `is_enrolled` | BOOLEAN | actively enrolled that term |

### 4.2 Finance

**`funds`** — one row per fund.
| column | type | notes |
|---|---|---|
| `fund_id` | TEXT | PK |
| `fund_name` | TEXT | |
| `fund_type` | TEXT | `endowment` / `operating` / `escrow` |
| `opening_balance` | DECIMAL | |

**`transactions`** — one row per transaction.
| column | type | notes |
|---|---|---|
| `txn_id` | TEXT | PK |
| `fund_id` | TEXT | FK → `funds` |
| `txn_date` | DATE | actual date — **[rule: fiscal-year]** straddles Jun/Jul |
| `fiscal_period` | TEXT | e.g. `FY2024` (opaque-string seed for M3 date trap) |
| `txn_type` | TEXT | `inflow` / `disbursement` / `retained` |
| `amount` | DECIMAL | |

**`investments`** — one row per investment position.
| column | type | notes |
|---|---|---|
| `investment_id` | TEXT | PK |
| `fund_id` | TEXT | FK → `funds` |
| `principal` | DECIMAL | invested amount |
| `return_amount` | DECIMAL | return in `period` |
| `is_realized` | BOOLEAN | **[rule: yield]** |
| `period` | TEXT | e.g. `2024-Q3` |

---

## 5. Personas (the identity model — used by everyone)

"Who is asking" is **not** a query parameter. It is the asking user's **identity =
(department, role)**, carried by the request's `user_id` and resolved by a minimal **T3
provisioned map** (Ryan owns this map). For M1 the map is a small fixed config:

| `user_id` (persona key) | department | role |
|---|---|---|
| `u_adm_analyst` | Admissions | analyst |
| `u_adm_director` | Admissions | director |
| `u_fin_analyst` | Finance | analyst |
| `u_fin_director` | Finance | director |

- **Department** is the crisp axis: it determines the **right table** for an ambiguous term.
- **Role** is dosed small for M1: it changes **presentation / granularity** (analyst → row-level
  detail, director → summary/aggregate), **never the table**. 1–2 role-teaser cases only.
- Declaring identity is **not cheating** (it is a legitimately-known logged-in fact). The cheating
  line — never crossed — is pre-supplying the resolved formula / SQL / answer.

---

## 6. Contracts (build against these)

Three decoupled contracts. Each teammate needs only their own contract + this spec.

### 6.1 Contract A — Sola (data / schema)

- **Engine: DuckDB only.** Ingest via Pneuma's existing
  `src/pneuma_seeker/services/db/datasets/ingest_csv.py` into the datasets dir; verify the data
  is **loadable + queryable by Pneuma**.
- **Implement §4 exactly** (table + column names/types). Add rows/columns/realism freely (🎛️);
  do **not** rename or drop the canonical columns.
- **Make the hidden rules bite (§3 trap 2):** transfer students must exist (Admissions
  retention/yield change when excluded); non-degree applicants must exist; transactions must
  straddle the **Jun 30 / Jul 1** fiscal boundary (so calendar-year math differs from fiscal);
  unrealized investment returns must exist.
- **Co-loadable / co-searchable (shared visibility):** both departments' tables loaded into the **same**
  Pneuma instance and searchable together — not isolated per-department instances.
- **Provide column descriptions / metadata** (Pneuma indexes these for retrieval).
- **Scale (🎛️):** ~hundreds of rows, 3 tables/dept is the target; bigger/more realistic welcome.
- **M3 (Sept):** a **dirtied** variant of this same schema (cryptic names, mismatched join keys
  between `applicant_id` spaces, `YYYYMM`-style date traps) — mechanical because §4 designed it in.
- Stay in our-owned dirs; never touch upstream paths.
- *You need only: this spec.* Not: memory internals, Pneuma internals beyond `ingest_csv.py`.

### 6.2 Contract B — Juan (institutional knowledge + test set)

Two artifacts, both authored from **this spec alone** (no dependency on Sola's data — ground
truth is *table + rule*, not an exact number).

**(1) `tribal_knowledge.json`** — the T4-authored input the memory layer ingests. One object
per `(department, term)`. **Exact format (do not deviate — memory loads this):**

```json
[
  {
    "department": "Admissions",
    "term": "retention",
    "definition": "First-year cohort re-enrollment rate the following fall.",
    "formula": "count(cohort students enrolled in Y+1) / count(first-time first-year students in cohort Y)",
    "target_tables": ["students", "enrollments"],
    "target_columns": ["students.cohort_year", "students.is_transfer", "enrollments.is_enrolled"],
    "hidden_rule": "Exclude transfer students (is_transfer = true) from the cohort denominator.",
    "trap_type": "tribal_knowledge"
  }
]
```

Author all **four** `(department, term)` objects of §2. `trap_type` ∈
`{latent_intent, tribal_knowledge, both}`.

**(2) `test_cases.json`** — ~20 ambiguous queries, persona-labelled, with table+rule ground
truth. **Exact format:**

```json
{
  "version": "1.0",
  "cases": [
    {
      "id": "TC001",
      "turns": ["What's our retention rate for last year's class?"],
      "persona": { "user_id": "u_adm_analyst", "department": "Admissions", "role": "analyst" },
      "ground_truth": {
        "target_table": "enrollments",
        "required_rule": "exclude_transfers",
        "rule_check": "denominator excludes is_transfer = true"
      },
      "trap_type": "both",
      "notes": "Pairs with TC002 (same query, Finance persona → transactions)."
    }
  ]
}
```

- 🔒 `tribal_knowledge.json` matches the format above (memory ingestion contract).
- 🔒 Definitions reference **§4 canonical table/column names exactly**.
- 🔒 Ground truth = **correct target table + whether the right rule was applied** (not an exact
  number). This is the definition of "intent convergence success" Lawrence scores against.
- 🔒 `persona.user_id` must be one of the §5 keys.
- 🔒 Queries must be **genuinely ambiguous** (resolvable only with the asker's identity).
- Include some **multi-turn** cases (`turns` has >1 entry) and **1–2 role-teaser** cases (same
  dept, `u_*_analyst` vs `u_*_director` → same table, different `ground_truth.presentation`).
- 🎛️ Count (~20, more welcome), phrasing/variety, extra rules consistent with the spec.
- *You need only: this spec + this format.* Not: memory internals, Sola's data.

### 6.3 Contract C — Lawrence (`/chat` invocation) — **v2 (Option B, auth'd API, D27)**

Drive Pneuma's **own** `/chat` (no separate service), black-box, OFF vs ON. **Updated for the
post-sync auth'd API** (`src/pneuma_seeker/routers/chat.py`; the old pre-auth shape is retired).

- **Endpoint:** `POST /chat`, response is an **NDJSON stream** (`application/x-ndjson`). Each line
  is a JSON payload with a `type` field: `log` (progress), `assistant` (model output incl. the
  generated SQL/reasoning), `done` (terminal, carries elapsed seconds). *(stream unchanged)*
- **Auth (NEW):** every call needs `Authorization: Bearer <token>`. **Ryan provides `personas.json`**
  mapping each persona → its `{token, user_id}` (produced by the setup fixture — see below). Lawrence
  picks the case's persona token; **he does not register/login himself.**
- **Request body (NEW shape):**
  ```json
  {
    "chat_id": "TC001-run3",
    "dataset_name": "campus",
    "message": "What's our retention rate for last year's class?"
  }
  ```
- **Persona is carried by the token, not the body.** The asking identity = the authenticated user
  behind the token; the memory layer maps that user → `(department, role)` (Ryan-owned map, §5).
  **Do not** put `user_id`/`department`/`role` in the body — pick the right **token** instead.
- **`dataset_name` is required and is always `"campus"`** — the single combined dataset holding
  **both** departments' tables (co-visibility is preserved by the dataset's design, §4, not by
  omitting a param). Ambiguous terms still have competing tables within it.
- **Multi-turn:** the server keeps history per `(user_id, chat_id)` → **send only the new turn's
  `message`**, reusing the same `chat_id`. Use a **fresh `chat_id` per case run** for isolation.
- **Bootstrap (Ryan-provided, one-time per server boot):** Ryan ships a setup helper that runs
  `docker compose up` (Postgres + core), registers the 4 personas into their dept groups, and emits
  `personas.json`. You consume `personas.json`; the auth machinery is not your concern.
- **A/B toggle is a server-side env var, NOT a per-request param.** Baseline = launch Pneuma with
  the memory flag **OFF**; memory = launch with it **ON**. Run the same suite against both launches
  (two base URLs or two server boots). *Proposed flag name `ENABLE_MEMORY_INJECTION` — Ryan confirms
  in W2; the contract (env-var, per-process) is stable regardless of the final name.* (Note: the
  existing `ENABLE_MEMORY_PROFILING` is unrelated telemetry, not the A/B switch.)
- **Scoring:** read Juan's `test_cases.json`; for each case, extract the **target table** from the
  generated SQL in the `assistant` payloads and check it against `ground_truth.target_table` +
  whether `required_rule` was applied (`rule_check`). Success = right table + right rule.
- **Metrics (required, OFF vs ON comparable):** intent-convergence **success rate**, **token**
  consumption, **latency** (from the `done` payload), **clarifying-turn count**.
- 🎛️ Tooling (asyncio/aiohttp/pytest/…), report format (CSV/MD/dashboard), concurrency, extra
  metrics. You can build the harness + parser against a **stub** before the MVP exists.
- *You need only: Juan's `test_cases.json` + this contract.* Not: memory internals, domain logic.

---

## 7. Open / TBD (do not block 6/17)

These are Ryan-internal and do **not** change any teammate's contract:

- **Exact `ENABLE_MEMORY_*` flag name** and the T3 provisioned-map file path — settled in Ryan's
  W2 (`services/memory/` scaffold). Contract C is written to be name-agnostic.
- **Whether `/chat` retains session history server-side** (so clients could send only the new
  turn) — confirmed in Ryan's W1. Until then, Contract C's "resend full history" is the safe path.
- **`role` presentation semantics** (what exactly "director summary vs analyst detail" renders) —
  refined with Juan when the 1–2 teaser cases are authored; not on the M1 critical path.
