# Semantic Layer — Business Rules

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
