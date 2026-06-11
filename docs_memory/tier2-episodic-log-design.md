# Tier 2 — Episodic State Log — Build Spec (LOCKED v1)

> Status: **LOCKED 2026-06-10 (DECISIONS D12).** Decisions (1)–(4) confirmed by user; this
> is the v1 build spec. Background & boundary: `DECISIONS.md` D12; gap analysis:
> `code-vs-6tier-mapping.md` (Tier 2). Anchored on D11 (interface-first, gitignored local
> store, dumb-first). Wikilink anchor: `[[tier-2-episodic-log]]`.

## Purpose (confirmed)
The append-only **episodic state log** — the "black box flight recorder" / messy
raw-material warehouse that the Enhancer later distills into the persistent tiers (3–6).
In Bayesian terms: **Tier 2 is the likelihood data; the Enhancer computes the posterior
that becomes Tiers 4–6's priors** (which then accelerate latent-intent convergence). Saved
to disk, must survive the session, consumed **asynchronously** by the Enhancer.

## Character vs Tier 1 (the key contrast)
- **Tier 1** is LLM-*curated* (has a brain, online, consumed *now* by the Conductor).
- **Tier 2** is **dumb capture** — records *everything* (incl. failures + raw CoT), and the
  write path uses **ZERO extra LLM calls** (hard constraint: Pneuma latency is already high
  from the long ReAct chain). The ReAct reasoning text already lives in `llm_messages`;
  Tier 2 just **serializes it before it's GC'd**. All "intelligence"
  (summarizing/condensing) is deferred to the async Enhancer.

## LOCKED decisions (1)–(4) — confirmed 2026-06-10

- **(1) Lifecycle. NO-DELETE — LOCKED (D18-6).** **Append-only** and **never deleted**. The
  concrete reason (locked in D18, was a lean under D16): **T2 is the ground-truth replay corpus
  for the Enhancer's A/B validation** (DECISIONS D18-5) — to decide whether a new lesson beats a
  stored one, the Enhancer replays both against past episodes; without the full history, conflict
  resolution falls back to blind-trusting the newer lesson. So `processed_at` is **just a progress
  marker** (how far the Enhancer has consumed), **not** a GC watermark. (Earlier "TTL /
  purge-after-distill" options are dropped; A/B sampled-replay cost limit → BACKLOG.)
- **(2) Backend.** Our **own store** in `services/memory/_episodic/` (gitignored, mirrors
  Tier 1's `_notebooks/`), **NOT** in upstream's `ws.db`. v1 = **JSONL** behind a small
  `EpisodicLog` interface (`append` / `iter` / `mark_processed`). **Recorded upgrade path
  (per user request): swap the JSONL backend to a DuckDB table** — reuse the existing stack
  (ws.db is already DuckDB; DuckDB can even attach Postgres, `db/main.py:404`), Conductor
  code unchanged. SQLite (Hermes-style) rejected: DuckDB already occupies that niche.
  Markdown (Kairos-style) rejected: Tier 2 is high-volume machine-read, wrong shape.
- **(3) Granularity.** **Step-level full trajectory** (incl. failures + raw CoT). This is
  *free on the LLM axis* — the data already exists in memory; only cost is disk + a clean
  schema. Shape = **turn envelope** + **step event stream** (see schema below). Raw CoT is
  stored as-is (cheap bytes); any summarization is the Enhancer's job. The **field set is
  decided by backward-reasoning from what each downstream tier needs.**
- **(4) Inclusion.** User OK'd storing **failures + raw CoT** — nothing excluded.

## Why NOT in `ws.db` (user's pollution concern, confirmed valid)
1. ws.db schema is upstream-owned (🟡 surgical-only territory).
2. Per-conversation files would force the Enhancer to crawl many files.
3. **Decisive:** `persist_session` is **delete-and-replace** (`DELETE` rows,
   `db/main.py:592-595`), which directly contradicts our **append-only** semantics.

Reuse the DuckDB *technology* (upgrade path), not the ws.db *file*.

## Schema (v1)
**Turn envelope** — one per turn (一輪 = one `Conductor.chat()`):
`user_id`, prompt, final answer, timing, tokens.
*(No explicit `user feedback` field: Pneuma has no feedback channel; satisfaction is inferred
by the Enhancer from the **next turn's** prompt/tone — which is just the next envelope — per
DECISIONS D17. Dropped the field that mirrored the rejected `R_user` reward signal.)*

**Step event stream** — one per ReAct step inside the turn:
```
{ turn_id, step_idx, phase[conductor/materializer], action, args,
  status, payload/error, sql?, retrieved_ids?, latency, ts }
```

**Field set ← backward-reasoning from downstream tiers:**
- **Tier 3** needs: `user_id` + question + role.
- **Tier 4** needs: question text + domain.
- **Tier 5** needs: per-join success/failure + error + SQL.
- **Tier 6** needs: full *successful* trajectories.

## Provenance graph is NOT reused as Tier 2
Provenance is a success-only "what worked" DAG of runnable code that gets
`reset_materialization_nodes()`'d; Tier 2 needs exactly the failures / reasoning /
append-only that provenance drops. Tier 2 may **reference** a provenance snapshot, but is
not provenance.

## Write path
A hook inside the Conductor/Materializer ReAct loops (🟡 surgical, additive, behind
`ENABLE_MEMORY_*`, default off) → a single call into our `EpisodicLog`. No extra LLM call.

## v1 spec (minimal — simplicity first)
| Aspect | Design |
|--------|--------|
| Lifecycle | append-only; survives session; `processed_at` watermark; cleanup deferred |
| Backend | JSONL in gitignored `services/memory/_episodic/` behind an **`EpisodicLog` interface** (`append` / `iter` / `mark_processed`); **DuckDB table = deferred backend swap** |
| Granularity | step-level full trajectory (failures + raw CoT included) |
| Schema | turn envelope + step event stream (fields back-reasoned from Tiers 3–6) |
| Write | dumb capture, **zero extra LLM**; hook in ReAct loop, flag-gated |
| Consumer | Enhancer (async / off-peak), advances `processed_at` |

## Implementation notes for v1
- `_episodic/` must be gitignored (local throwaway, same pattern as D11's `_notebooks/`).
- `EpisodicLog` is the single seam for the future DuckDB swap — keep all storage I/O inside
  it; nothing else touches the backend.
- Tier 2 is **dumb by design** — resist adding any "smart" filtering/summarizing on the
  write path; that work belongs to the Enhancer.

## Deferred to later versions (→ BACKLOG.md)
DuckDB backend upgrade, episodic-log cleanup/retention (GC of consumed episodes), the
**Enhancer trigger mechanism** (how/when it runs — feeds back into retention + watermark
semantics).
