# 👥 TEAM — Start Here

> **If you are Sola, Juan, or Lawrence, this is your entry point.** You only ever need the few
> docs listed below. Everything else under `docs_memory/` is Ryan's internal design/decision log —
> you do not need it to build your module.
>
> **How versioning works (so you don't have to be told when something changes):**
> 1. Each team-facing doc carries a `📄 Doc version: vN` line in its header.
> 2. This page's table lists every doc's **current version + what last changed**.
> 3. **If a version number here is higher than the one you last built against, that doc changed —
>    re-read it (the "last change" column tells you whether it affects you).**
> Markdown in this repo is the **single source of truth**. (Any Word/`.docx` copy is a non-canonical
> export, regenerated on demand — do not build against it.)

## Current versions

| Doc | For whom | Version | Last change |
|-----|----------|---------|-------------|
| [`scenario-spec.md`](scenario-spec.md) | **Everyone** — the shared campus blueprint + your contract (§6.1 Sola / §6.2 Juan / §6.3 Lawrence) | **v2** | 2026-06-15 — §6.3 Lawrence `/chat` rewritten for the auth'd API (Bearer token + `personas.json` + `dataset_name:"campus"` + send-only-new-turn) |
| [`ROADMAP.md`](ROADMAP.md) | **Everyone** — roles, milestones, weekly tasks, committed hours | **v1** | 2026-06-12 — initial |

## Which sections are yours

- **🗂️ Sola (data / schema):** `scenario-spec.md` **§4** (canonical schema — names/types are fixed),
  **§6.1** (your contract), **§1–3** (the world + the traps your data must make bite). Tasks: `ROADMAP.md`.
- **📚 Juan (knowledge + test set):** `scenario-spec.md` **§2** (the two ambiguous terms), **§6.2**
  (your contract — `tribal_knowledge.json` + `test_cases.json` formats), **§5** (personas).
  Format reference: `src/pneuma_seeker/services/memory/_config/tribal_knowledge.sample.json`. Tasks: `ROADMAP.md`.
- **🚀 Lawrence (benchmark):** `scenario-spec.md` **§6.3** (your contract — the `/chat` invocation),
  **§5** (personas), **§3** (the traps you score against). Tasks: `ROADMAP.md`.

## Working rules (full versions in `scenario-spec.md` / `ROADMAP.md`)

- Build against the spec at the version above; enrich only within your 🎛️ FLEXIBLE zone.
- All your code lives in **our-owned dirs** (Ryan points you to them); never touch upstream Pneuma paths.
- Branch `feature/*` and PR into our integration branch. **Ryan owns all git/branch governance + PR
  safety** (this is a fork — never push/PR to upstream).
- Falling behind is fine **if you flag it early** to Ryan.

---

### Maintenance (Ryan only)
When a team-facing doc materially changes: (1) bump its `📄 Doc version` header line + add a changelog
entry in that doc, and (2) update this table's row (version + last change). That is the whole protocol —
teammates self-serve from here, no individual pings needed. To add a new team-facing doc, give it a
version header and add a row here.
