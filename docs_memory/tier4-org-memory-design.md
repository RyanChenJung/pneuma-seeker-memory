# Tier 4 — Organization Memory — Build Spec (LOCKED v1)

> Status: **LOCKED 2026-06-10 (DECISIONS D15).** Background & boundary: `DECISIONS.md` D13
> (scope hierarchy, actionability filter, auto-fill) + D14 (T3↔T4 boundary); gap analysis:
> `code-vs-6tier-mapping.md` (Tier 4). Anchored on D11/D12 (interface-first, gitignored
> local store, dumb-first).

## Purpose (confirmed)
A persistent layer of **institutional truth** that gives the Conductor *contextual priors*
to align with how *this* organization works: clinical definitions, official protocols,
data-dictionary meanings, and the org's own learned conventions. Read-only to frontline
agents. Distinct from T3 (which is about a *person*) in **owner / authority / subject**.

## What T4 holds — TWO heads (the defining structure)

Unlike T1/T2/T3, T4 has two sources with **different writers, different authority, and
different read modes**:

| | **(A) Authored knowledge base** | **(B) Learned org conventions** |
|---|---|---|
| Content | clinical definitions, official protocols, data dictionaries, guidelines | cross-user org habits ("in Admissions everyone filters X this way", "this join is the house standard") |
| Writer | **external ingestion** (human / HR / file import) — **NOT Tier 2, NOT the Enhancer** | **Enhancer**, distilled from **aggregated** Tier 2 (scope key = org, not user) |
| Authority | **authoritative** (a rule) | **heuristic** (an observed habit) |
| Size | large corpus | small (distilled) |
| Read mode | **retrieve top-k by query** (Retriever → Tier 1 buffer) | **inject whole** (joins the overlay composition) |
| v1 backend | document store (`indices/kb/*`, BM25 → vector deferred; possibly reused `DocumentDB`) | structured overlay file (gitignored local) |

This mirrors T3's Provisioned/Learned split, but here the **authored side is the main mass**
(T3's provisioned was a thin testing stub; T4's authored is the whole point of `DocumentDB`).

**Refines D13's unifying frame.** D13 said "Tiers 3–6 are all Enhancer-written, all distilled
from Tier 2." T4's **(A) authored side breaks that by design**: T4 = a layer of *external
authoritative truth* **plus** a layer of *internally-learned convention*.

## Authority / trust — the T4-unique dimension
T3 had no authority dimension; T4 does, and it drives the conflict rule:
- **Authored (A) always wins.** Learned (B) may only **supplement**, never **override**
  authored. (e.g. if an official guideline says X but aggregated behavior suggests Y, the
  guideline stands; the habit is offered as a secondary observation, not a replacement.)
- **Both are injected labelled** with provenance + trust level, so the Conductor knows which
  is a *rule* vs an *observed habit*.
- **Governance is thin in v1:** a metadata tag (source, trust, scope). Real version-control /
  who-authored / approval workflow → BACKLOG.
- **Authored trust is static in v1, DYNAMIC later (D18-8).** v1's "authored always wins" is a
  fixed rule. The refinement: authored gains a **dynamic trust weight = f(base authority, the
  `negative`-`support` the *learned* side accumulates against it)** — when learned empirical
  evidence repeatedly contradicts an authored fact (learned records of `type: negative_anti_pattern`
  whose `support` keeps climbing), authored trust **erodes**, and the system learns the org's real
  practice diverges from its docs (the "learned > authored" north-star made operational). Authored
  stays *outside* the shared sextuple record (it is declarative, D18-7), but is *governed by* the
  learned side's `type`+`support`. Conflict-resolution formula → BACKLOG (does not block B3/B4).

## Scope & hierarchy
- **Scope key = `(institution, department)`** — a hierarchy, overlay-style (D13): broad
  `institution` (global-org) base + narrower `department` (local-org) augment/override, in
  the same CLAUDE.md global+project model used for the T3 overlay.
- **Actionability filter (D13):** store specific groundable facts ("in Admissions a
  'matriculant' means X"), not vague breadth ("UChicago is a university"). Heterogeneous
  departments ⇒ the institution layer is naturally thin; actionable mass concentrates at the
  department layer.
- **Soft, overlapping, multi-membership clusters** (D14 refinement) = BACKLOG; v1 is the
  hard-hierarchy mechanism.

## Promotion ladder (only the learned head)
- **Only (B) learned conventions promote**: `T1 (personal note) → T3 (user habit) →
  T4-department (local-org) → T4-institution (global-org)`. **(A) authored never promotes**
  (it is already authoritatively placed at a scope).
- **Gate:** recurrence threshold N + content-kind filter — a generalizable convention may
  promote; a personal preference / PII may not (D14). Two-stage convergence (D13): commonality
  *within* a department → local-org; recurs *across* departments → global-org.
- This is also where a strongly-recurring learned convention could one day be promoted into an
  **authored draft** — a reason both heads live under one facade (below).

## Read path (split by head)
1. **Learned overlay** — small → `get_org_overlay(scope)` returns the whole block; it joins
   D14's overlay composition (`institution → department → user`, narrowest augments/overrides)
   in the Conductor's env-state prompt. No runtime summarization (compression at write time).
2. **Authored knowledge** — large → `search_authored(query, scope)` returns top-k relevant
   slices; the **Retriever** pulls these into the Tier 1 buffer on demand (matches the spec's
   "RETRIEVER injects high-value facts into Conductor's Tier 1 buffer"). Not injected whole.

## Write path
- **(A) Authored:** an **ingestion pipeline** (out of the live session, not the Enhancer) loads
  documents into the document store with scope + trust metadata. (HR/identity-system feed
  deferred → BACKLOG; v1 = manual/file import.)
- **(B) Learned:** the **Enhancer** (async / off-peak) reads *aggregated* Tier 2 across the
  scope's users, mines recurring conventions, and writes them with the recurrence-N gate.
  Rewritable living doc (last-write-wins + `last_seen`), like T3's learned head.

## Interface — one `OrgMemory` facade
```python
class OrgMemory:
    def get_org_overlay(self, scope) -> str:           # (B) learned, inject-whole
        ...
    def search_authored(self, query, scope) -> list:   # (A) authored, top-k retrieval
        ...
```
- **One facade, not two split interfaces** (D15 Q5-ii): (i) concept alignment — one tier = one
  interface, like T1/T2/T3; (ii) the promotion ladder needs both heads under one roof.
- The **authored backend is hidden behind the facade** — our own store vs reusing upstream
  `DocumentDB`/`Knowledge`. **The reuse question is settled in principle (D24):** `DocumentDB`
  is a backend/index substrate *behind* this authored head, not a competing architecture — so
  only the code-level backend swap remains deferred. Interface-first means the choice doesn't
  block us; it only swaps the authored backend later.

## v1 spec (minimal — simplicity first)
| Aspect | Design |
|--------|--------|
| Scope key | `(institution, department)` (overlay hierarchy) |
| Heads | (A) Authored authoritative KB + (B) Learned org conventions |
| Authority | authored wins; learned supplements only; both labelled with trust |
| Backend | `OrgMemory` facade over two stores: authored = doc store (`indices/kb/*`, BM25; vector & `DocumentDB`-reuse deferred), learned = structured overlay file (gitignored local) |
| Read | learned → inject whole (overlay); authored → top-k retrieval (Retriever → Tier 1) |
| Write | authored → ingestion pipeline; learned → Enhancer from aggregated Tier 2 (recurrence N) |
| Promotion | only learned promotes (T1→T3→T4-dept→T4-inst), gated by N + content-kind |
| MVP scope | single institution + single department; **near-term ≥2 departments** (see below) |

## MVP & near-term target
- **MVP = single institution + single department**: build the scope-hierarchy mechanism and
  both heads end-to-end. **MVP seeds a small *real* authored set** (option b, D15 Q5-i) — not
  an empty pipeline.
- **NEAR-TERM (not backlog) = single institution + ≥2 departments.** This is the test that
  actually proves the core claim: **different departments asking the *same* question each
  converge to the *correct* (different) latent intent.** The differing per-department authored
  definitions are the likely convergence variable — which is why the MVP must seed real
  authored content.

## What T4 does NOT hold (boundaries)
- ❌ Person-specific habits/identity → Tier 3.
- ❌ Physical schema / join navigation → Tier 5 (T4 = *meaning / institutional rules*; T5 =
  *physical DB navigation*; route a correction by its *subject*, D13).
- ❌ Raw trajectories → Tier 2; reusable procedural skills → Tier 6.

## Deferred to later versions (→ BACKLOG.md)
Vector backend, the `DocumentDB`/`Knowledge` **code-level backend swap** (reuse-vs-build
settled in principle by **D24**; only the wiring is deferred), exact scope-level count +
overlay precedence rules, full governance (versioning/who-authored/sign-off), HR/identity-
system authored feed, soft-overlapping-cluster org scope.
