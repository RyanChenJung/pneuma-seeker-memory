# Tier 1 — Short-Memory "Notebook" — Design DRAFT

> Status: **DRAFT, pending user decisions (a)–(d).** Once locked, this becomes the build
> spec. Background & confirmed intent: `DECISIONS.md` D9; gap analysis:
> `code-vs-6tier-mapping.md` (Tier 1). Confirmed understanding 2026-06-09.

## Purpose (confirmed)
Counter "lost in the middle": key evidence retrieved mid-context gets buried and
forgotten, raising hallucination. Keep the important bits curated and re-read right before
answering — like a human taking side-notes and consulting them. Conversation-scoped;
resets on a new conversation/problem. Conductor has it for sure; Materializer = OPEN (Q2).

## What the notebook looks like (concrete example)
A per-conversation Markdown, three sections, each entry tagged with source + turn:

```markdown
# 📒 Notebook — conversation c45 (problem: 2023 年住院 > 30 天的病人與主治醫師)

## 🎯 Ground-truth evidence (retrieved, judged important)
- [E1] 住院天數欄位是 `length_of_stay`（單位：天），不是 `los_hours`。 ⟵ table_retrieve, turn 1
- [E2] 病人↔醫師關聯用 `physician_id`（admissions 表有此欄）。 ⟵ join_path, turn 1

## 🧠 Reasoning conclusions
- [R1] 「超過 30 天」= `length_of_stay > 30`（已確認單位是天）。 ⟵ turn 1

## 🙋 User corrections / constraints
- [C1] 只算入院日期落在 2023 的，不是出院日期。 ⟵ user, turn 2 (supersedes earlier assumption)
```

Before generating an answer, the whole notebook is pinned into the prompt for the LLM to
glance at.

## v1 spec (minimal — simplicity first; fancy stuff deferred)
| Aspect | Design |
|--------|--------|
| Entry types | Evidence (E) / Reasoning (R) / User correction (C) |
| Entry fields | one-line content + source (which retrieval/step/user) + turn + optional "supersedes" |
| Format | Markdown |
| Scope / reset | conversation-level; cleared on new conversation/problem |
| Agents | Conductor (yes); Materializer (OPEN — Q2) |

## OPEN decisions — need user (a)–(d), recommendations inline
- **(a) Write trigger.** *Rec:* v1 = LLM writes explicitly via a lightweight `note`
  action when it deems something important (simplest, LLM-controlled). Auto post-event
  "should I note this?" judge = deferred.
- **(b) Storage.** *Rec:* one `.md` file per conversation under `services/memory/`
  (matches the CLAUDE.md intuition, human-inspectable, simplest). Alt: a table in `ws.db`.
- **(c) Pin position.** *Rec:* pin at the **end** of the assembled prompt, right before
  generation (ends are best-attended; matches "look at notes right before answering").
- **(d) Capacity.** *Rec:* soft cap (~30 entries / token budget) + dedup + allow
  supersede. Importance scoring / time decay = deferred.

## Deferred to later versions (not v1)
Importance/confidence scores, time decay, automatic salience judging, Materializer
notebook (pending Q2), cross-conversation reuse (that would be Tier 3/6, not Tier 1).
