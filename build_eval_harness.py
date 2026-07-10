"""
build_eval_harness.py

Generates a Ryan-format accuracy benchmark for Rules 1, 3, 5, following
the same structure as his 001_baseline-vs-semantic-layer experiment:
  - schema.md, questions.md, questions.json (ground truth), semantic_layer.md
  - reuses his eval.py as-is (no changes needed — it's generic)

Run this from the repo root, AFTER restaurant.db has been built via
ingest_csv.py. It connects to the real database and computes each
question's ground-truth answer directly with SQL — nothing is hardcoded,
so it's safe to re-run any time the underlying data changes.

Output directory: experiments/001_restaurant-tribal-knowledge/harness/
"""

import duckdb
import json
import os

DB_PATH = "src/pneuma_seeker/services/db/datasets/restaurant/restaurant.db"
OUT_DIR = "experiments/001_restaurant-tribal-knowledge/harness"
os.makedirs(f"{OUT_DIR}/reference_results", exist_ok=True)
os.makedirs(f"{OUT_DIR}/round1_baseline", exist_ok=True)
os.makedirs(f"{OUT_DIR}/round2_semantic", exist_ok=True)

con = duckdb.connect(DB_PATH, read_only=True)

def q(sql):
    """Run SQL, return a scalar."""
    return con.execute(sql).fetchone()[0]

def qval(sql):
    """Run SQL, return first column of first row (for single_value answers)."""
    return con.execute(sql).fetchone()[0]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUESTION DEFINITIONS
# Each entry: id, group, tribal_knowledge tag (or None), question text,
# SQL to compute ground truth, answer_type, tolerance override (or None)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTIONS = [
    # ── Group A: Schema baseline (no tribal knowledge) ──────────────────
    dict(id="A-01", group="A", tk=None,
         text="How many venue attendance records are in the visits table?",
         sql="SELECT COUNT(*) FROM visits", atype="single_number"),
    dict(id="A-02", group="A", tk=None,
         text="How many distinct venues are there?",
         sql="SELECT COUNT(DISTINCT venue_code) FROM venues", atype="single_number"),
    dict(id="A-03", group="A", tk=None,
         text="How many distinct cuisine categories are represented?",
         sql="SELECT COUNT(DISTINCT cuisine_type) FROM venues", atype="single_number"),
    dict(id="A-04", group="A", tk=None,
         text="What is the average seating capacity across all venues?",
         sql="SELECT ROUND(AVG(seating_capacity), 2) FROM venues", atype="single_number"),
    dict(id="A-05", group="A", tk=None,
         text="Which cuisine category has the most venues?",
         sql="SELECT cuisine_type FROM venues GROUP BY cuisine_type ORDER BY COUNT(*) DESC LIMIT 1",
         atype="single_value"),

    # ── Group B: Rule 1 — "visitors" differs by department ──────────────
    dict(id="B-01", group="B", tk="visitors_definition",
         text="For Operations reporting: what is the total number of visitors across all venues, for the entire dataset?",
         sql="SELECT SUM(guest_count) FROM visits", atype="single_number"),
    dict(id="B-02", group="B", tk="visitors_definition",
         text="For Marketing reporting: what is the total number of visitors across all venues, for the entire dataset?",
         sql="SELECT SUM(expected_covers) FROM reservations", atype="single_number"),
    dict(id="B-03", group="B", tk="visitors_definition",
         text="For Operations reporting: what is the average number of visitors per venue per day, across the dataset?",
         sql="SELECT ROUND(AVG(guest_count), 2) FROM visits", atype="single_number"),

    # ── Group C: Rule 3 — fiscal year start differs by department ───────
    dict(id="C-01", group="C", tk="fiscal_year_convention",
         text="For Finance reporting: what was the total realized guest count during fiscal Q1?",
         sql="""
            WITH q1_period AS (
                SELECT MIN(period_code) AS p FROM calendar WHERE period_code LIKE '%-1'
            )
            SELECT SUM(v.guest_count) FROM visits v
            JOIN calendar c ON v.service_day = c.service_day
            WHERE c.period_code = (SELECT p FROM q1_period)
         """, atype="single_number"),
    dict(id="C-02", group="C", tk="fiscal_year_convention",
         text="For Operations reporting: what was the total realized guest count during fiscal Q1?",
         sql="""
            WITH q1_period AS (
                SELECT MIN(cycle_label) AS p FROM calendar WHERE cycle_label LIKE '%-1'
            )
            SELECT SUM(v.guest_count) FROM visits v
            JOIN calendar c ON v.service_day = c.service_day
            WHERE c.cycle_label = (SELECT p FROM q1_period)
         """, atype="single_number"),
    dict(id="C-03", group="C", tk="fiscal_year_convention",
         text="For Finance reporting: how many distinct venues had at least one visit during fiscal Q1?",
         sql="""
            WITH q1_period AS (
                SELECT MIN(period_code) AS p FROM calendar WHERE period_code LIKE '%-1'
            )
            SELECT COUNT(DISTINCT v.venue_code) FROM visits v
            JOIN calendar c ON v.service_day = c.service_day
            WHERE c.period_code = (SELECT p FROM q1_period)
         """, atype="single_number"),

    # ── Group D: Rule 5 — booking channel inclusion differs by department ─
    dict(id="D-01", group="D", tk="booking_channel_scope",
         text="For Operations reporting: what is the total covers volume (sum of expected party sizes across all bookings) for direct (in-house) bookings only, across all venues?",
         sql="SELECT SUM(expected_covers) FROM reservations WHERE source_channel = 'direct'", atype="single_number"),
    dict(id="D-02", group="D", tk="booking_channel_scope",
         text="For Marketing reporting: what is the total covers volume (sum of expected party sizes across all bookings) across all booking channels (direct and partner-referred), across all venues?",
         sql="SELECT SUM(expected_covers) FROM reservations", atype="single_number"),
    dict(id="D-03", group="D", tk="booking_channel_scope",
         text="What percentage of total covers volume (sum of expected party sizes) comes from the partner channel?",
         sql="""
            SELECT ROUND(
                100.0 * SUM(CASE WHEN source_channel = 'partner' THEN expected_covers ELSE 0 END)
                / SUM(expected_covers), 2)
            FROM reservations
         """, atype="single_number"),

    # ── Group E: Compound — two rules combined ───────────────────────────
    dict(id="E-01", group="E", tk="fiscal_year_convention+booking_channel_scope",
         text="For Marketing reporting, using Operations' fiscal calendar convention: what was the total covers volume (sum of expected party sizes) across all channels during fiscal Q1?",
         sql="""
            WITH q1_period AS (
                SELECT MIN(cycle_label) AS p FROM calendar WHERE cycle_label LIKE '%-1'
            )
            SELECT SUM(r.expected_covers) FROM reservations r
            JOIN calendar c ON r.visit_day = c.service_day
            WHERE c.cycle_label = (SELECT p FROM q1_period)
         """, atype="single_number"),
    dict(id="E-02", group="E", tk="visitors_definition+fiscal_year_convention",
         text="For Operations reporting, using Finance's fiscal calendar convention: what was the total realized visitor count during fiscal Q1?",
         sql="""
            WITH q1_period AS (
                SELECT MIN(period_code) AS p FROM calendar WHERE period_code LIKE '%-1'
            )
            SELECT SUM(v.guest_count) FROM visits v
            JOIN calendar c ON v.service_day = c.service_day
            WHERE c.period_code = (SELECT p FROM q1_period)
         """, atype="single_number"),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPUTE GROUND TRUTH + WRITE questions.json
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Computing ground-truth answers from restaurant.db...")

questions_json = []
questions_md_lines = ["# Questions\n", "Answer all questions using the database at `../db/restaurant.db`.",
                       "Write your answers to `results/answers.json` in the format specified in INSTRUCTIONS.md.\n"]

current_group = None
group_labels = {
    "A": "Schema Baseline (no tribal knowledge)",
    "B": "Visitors Definition (Rule 1)",
    "C": "Fiscal Year Convention (Rule 3)",
    "D": "Booking Channel Scope (Rule 5)",
    "E": "Compound Business Rules",
}

for item in QUESTIONS:
    expected = q(item["sql"])
    entry = {
        "id": item["id"],
        "group": item["group"],
        "answer_type": item["atype"],
        "expected": expected,
    }
    if item["tk"]:
        entry["tribal_knowledge"] = item["tk"]
    questions_json.append(entry)
    print(f"  {item['id']}: {expected}")

    if item["group"] != current_group:
        current_group = item["group"]
        questions_md_lines.append(f"\n---\n\n## Group {current_group} — {group_labels[current_group]}\n")
    questions_md_lines.append(f"**{item['id']}** {item['text']}\n")

with open(f"{OUT_DIR}/reference_results/questions.json", "w") as f:
    json.dump(questions_json, f, indent=2, default=str)

with open(f"{OUT_DIR}/round1_baseline/questions.md", "w") as f:
    f.write("\n".join(questions_md_lines))
with open(f"{OUT_DIR}/round2_semantic/questions.md", "w") as f:
    f.write("\n".join(questions_md_lines))

print(f"\n✅ questions.json ({len(questions_json)} questions) + questions.md written")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# schema.md
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
schema_md = """# Database Schema

The database is located at `../db/restaurant.db` (DuckDB).

## Tables

### visits
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| guest_count | BIGINT |
| service_day | VARCHAR |
| cal_week | BIGINT |
| walk_in_flag | BOOLEAN |

### reservations
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| expected_covers | BIGINT |
| visit_day | VARCHAR |
| visit_hour | BIGINT |
| booked_on | VARCHAR |
| no_show_flag | BOOLEAN |
| source_channel | VARCHAR |

### venues
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| cuisine_type | VARCHAR |
| location_label | VARCHAR |
| district_code | VARCHAR |
| seating_capacity | BIGINT |

### calendar
| Column | Type |
|--------|------|
| service_day | VARCHAR |
| day_of_week | VARCHAR |
| is_special_day | BIGINT |
| period_code | VARCHAR |
| cycle_label | VARCHAR |

### daily_summary
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| service_day | VARCHAR |
| total_bookings | BIGINT |
| avg_party_size | DOUBLE |
"""
for sub in ["round1_baseline", "round2_semantic"]:
    with open(f"{OUT_DIR}/{sub}/schema.md", "w") as f:
        f.write(schema_md)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# semantic_layer.md (Rule 1, 3, 5 documentation — Ryan's format)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
semantic_layer_md = """# Semantic Layer — Business Rules

This document contains all business rules (tribal knowledge) required to
correctly answer the benchmark questions. In the baseline round, this
document is NOT provided to the model. In the semantic-layer round, this
document IS provided.

---

## 1. "Visitors" Definition (Operations vs. Marketing)

- **Operations** defines "visitors" as actual seated guests — use
  `visits.guest_count`.
- **Marketing** defines "visitors" as booked party size, regardless of
  whether the guest actually showed up — use `reservations.expected_covers`.
- These are NOT interchangeable. A no-show is counted by Marketing's
  definition but not Operations'.

## 2. Fiscal Year Convention (Finance vs. Operations)

- **Finance**'s fiscal year starts **April 1** — use `calendar.period_code`.
- **Operations**' fiscal year is the calendar year, starting **January 1**
  — use `calendar.cycle_label`.
- The same quarter label (e.g. "Q1") refers to different date ranges
  depending on which department is asking.

## 3. Booking Channel Scope (Operations vs. Marketing)

- **Operations** counts only direct (in-house) bookings when reporting
  total booking volume — filter `reservations.source_channel = 'direct'`.
- **Marketing** counts bookings from all channels, including
  partner-referred bookings — no filter on `source_channel`.
- `daily_summary.total_bookings` reflects the Operations convention
  (direct-channel only) — it does NOT include partner-channel bookings.
  Do not treat it as a complete total unless the question specifically
  asks for Operations' definition.
"""
for sub in ["round2_semantic"]:
    with open(f"{OUT_DIR}/{sub}/semantic_layer.md", "w") as f:
        f.write(semantic_layer_md)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INSTRUCTIONS.md (baseline: no semantic layer mention; semantic: mentions it)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
instructions_baseline = """# Instructions

You are a data analyst. Your job is to answer business questions about a
restaurant chain database.

## Database

DuckDB database at: `../db/restaurant.db`

Schema reference: `schema.md`

## Your Task

1. Read `questions.md`
2. For each question, write a SQL query and execute it against the database
3. Record every answer in `../results/answers.json`

## Output Format

Write a single JSON file at `../results/answers.json` with this exact structure:

```json
[
  {"id": "A-01", "sql": "SELECT COUNT(*) FROM visits", "answer": 12345},
  {"id": "A-05", "sql": "...", "answer": "XX"}
]
```

## Important

- Answer all questions. Do not skip any.
- Use only the data in the database — do not guess or estimate.
- Round decimal answers to 2 decimal places unless the question specifies otherwise.
- Some questions reference department context (e.g. "For Operations reporting...").
  Answer strictly from the perspective stated in the question.
"""

instructions_semantic = instructions_baseline.replace(
    "## Database",
    "## Business Rules\n\n**IMPORTANT:** Read `semantic_layer.md` first. It contains "
    "critical business definitions (e.g. how \"visitors\" is defined by department, "
    "when each department's fiscal year starts, which booking channels count) "
    "required to answer many questions correctly.\n\n## Database"
).replace(
    "1. Read `questions.md`",
    "1. Read `semantic_layer.md` - Business rules glossary\n2. Read `questions.md`"
).replace(
    "2. For each question",
    "3. For each question"
).replace(
    "3. Record every answer",
    "4. Record every answer"
)

with open(f"{OUT_DIR}/round1_baseline/INSTRUCTIONS.md", "w") as f:
    f.write(instructions_baseline)
with open(f"{OUT_DIR}/round2_semantic/INSTRUCTIONS.md", "w") as f:
    f.write(instructions_semantic)

print(f"\n✅ Full harness written to {OUT_DIR}/")
print("  reference_results/questions.json  — ground truth (computed from real DB)")
print("  round1_baseline/  — schema.md, questions.md, INSTRUCTIONS.md (no semantic layer)")
print("  round2_semantic/  — schema.md, questions.md, INSTRUCTIONS.md, semantic_layer.md")
print("\nNext: copy restaurant.db into harness/db/, then run each round through Opus,")
print("save answers.json, and run eval.py (reuse Ryan's script as-is).")

con.close()
