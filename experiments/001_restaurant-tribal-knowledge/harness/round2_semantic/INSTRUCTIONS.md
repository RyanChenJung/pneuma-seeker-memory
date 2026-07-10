# Instructions

You are a data analyst. Your job is to answer business questions about a
restaurant chain database.

## Business Rules

**IMPORTANT:** Read `semantic_layer.md` first. It contains critical business definitions (e.g. how "visitors" is defined by department, when each department's fiscal year starts, which booking channels count) required to answer many questions correctly.

## Database

DuckDB database at: `../db/restaurant.db`

Schema reference: `schema.md`

## Your Task

1. Read `semantic_layer.md` - Business rules glossary
2. Read `questions.md`
3. For each question, write a SQL query and execute it against the database
4. Record every answer in `../results/answers.json`

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
