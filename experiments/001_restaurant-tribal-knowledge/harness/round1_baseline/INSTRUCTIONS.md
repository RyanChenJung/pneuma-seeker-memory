# Instructions

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
