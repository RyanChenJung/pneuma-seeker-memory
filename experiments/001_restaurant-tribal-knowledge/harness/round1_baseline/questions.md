# Questions

Answer all questions using the database at `../db/restaurant.db`.
Write your answers to `results/answers.json` in the format specified in INSTRUCTIONS.md.


---

## Group A — Schema Baseline (no tribal knowledge)

**A-01** How many venue attendance records are in the visits table?

**A-02** How many distinct venues are there?

**A-03** How many distinct cuisine categories are represented?

**A-04** What is the average seating capacity across all venues?

**A-05** Which cuisine category has the most venues?


---

## Group B — Visitors Definition (Rule 1)

**B-01** For Operations reporting: what is the total number of visitors across all venues, for the entire dataset?

**B-02** For Marketing reporting: what is the total number of visitors across all venues, for the entire dataset?

**B-03** For Operations reporting: what is the average number of visitors per venue per day, across the dataset?


---

## Group C — Fiscal Year Convention (Rule 3)

**C-01** For Finance reporting: what was the total realized guest count during fiscal Q1?

**C-02** For Operations reporting: what was the total realized guest count during fiscal Q1?

**C-03** For Finance reporting: how many distinct venues had at least one visit during fiscal Q1?


---

## Group D — Booking Channel Scope (Rule 5)

**D-01** For Operations reporting: what is the total covers volume (sum of expected party sizes across all bookings) for direct (in-house) bookings only, across all venues?

**D-02** For Marketing reporting: what is the total covers volume (sum of expected party sizes across all bookings) across all booking channels (direct and partner-referred), across all venues?

**D-03** What percentage of total covers volume (sum of expected party sizes) comes from the partner channel?


---

## Group E — Compound Business Rules

**E-01** For Marketing reporting, using Operations' fiscal calendar convention: what was the total covers volume (sum of expected party sizes) across all channels during fiscal Q1?

**E-02** For Operations reporting, using Finance's fiscal calendar convention: what was the total realized visitor count during fiscal Q1?
