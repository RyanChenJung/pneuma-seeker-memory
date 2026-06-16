# Pneuma-Seeker — Codebase Map

> Read-only survey of the repository as of branch `feat-memory-experiement`.
> Scope: the Python backend under `src/pneuma_seeker` (the actual system), plus
> the surrounding data, baselines, and frontend-bridge assets. Frontend (OpenWebUI)
> lives in a separate repo; only the bridge functions are in-tree.
>
> **⚠️ Updated 2026-06-15 after syncing `upstream/prod`** (the "Polish backend to
> accommodate new UI" + "Ensure resilience" refactor). Major changes folded in below:
> `main.py` split into `routers/` (auth · chat · indexing); a Postgres-backed
> **auth/users/groups/permissions (RBAC)** subsystem; the data layer split into
> `datasets/ + users/ + workspaces/` behind a new `PneumaDB` facade
> (`db/main.py` → `db/workspaces/manager.py`); **Claude + Gemini** LLM backends.

---

## 1. Architecture Overview

**What it is.** Pneuma-Seeker is an LLM-powered agent that answers natural-language
questions over *tabular* data. Given a question, it (a) discovers relevant tables,
(b) reifies the user's information need as a target schema, (c) integrates/transforms
data to populate that schema, and (d) runs computation to produce an answer — while
recording a **provenance graph** of every transformation so the result is explainable
and reproducible as standalone Python code.

**Problem it solves.** Bridging messy, multi-table data and a human intent without
forcing the user to know the schema, write SQL, or find the right tables. The paper
framing is "relational reification": turn an information need into a concrete pair
`(T, S)` — target tables `T` plus a Python script `S` over them — and fulfill it.

**Shape of the system.** A single FastAPI backend that streams responses. Internally
it is a three-role agent loop layered over shared infrastructure services:

```
              FastAPI (main.py = app + lifespan bootstrap, mounts routers)
                                │
          routers/  ──  auth.router · chat.router · indexing.router
            │                   │  (every /chat & /index call: Bearer-token auth →
       UserDB (Postgres)        │   get_current_user → group permissions)
       users·groups·perms       │
                                │
                         SessionManager  ──>  ChatSession (per user_id+chat_id)
                                │
                            Conductor   ── high-level ReAct planner over an action set
                          /     │     \
              Materializer   ActionSet   ProvenanceGraph
              (builds T)    (the tools)  (records every step as code)
                                │
        ┌───────────────────────┼─────────────────────────────┐
   IR / Retriever        LanguageModel API                 DB API
   (Pneuma hybrid        (LLM + embeddings,                (DuckDB datasets +
    BM25 + vector)        provider factory)                 per-chat workspaces)
```

Key design principle (see `docs/architecture.md`): **separation of orchestration**
(Conductor), **retrieval** (Retriever/IR), and **materialization** (Materializer)
from supporting infra (LM service, DB service, Indexing service). This keeps each
LLM's context bounded and the roles independently testable.

---

## 2. Directory Structure

| Path | Responsibility |
|------|----------------|
| `src/pneuma_seeker/` | The backend package. Everything below is under here unless noted. |
| `main.py` | FastAPI app + `lifespan` bootstrap (init `UserDB` schema, seed `admin` group/user) + CORS. **Mounts `routers/`; no endpoint bodies live here anymore.** Entry point. |
| `routers/` | The HTTP endpoints, split by concern (post-sync): `auth.py` (register/login/logout/me, group+permission admin), `chat.py` (`POST /chat` NDJSON stream, chat history/search/delete), `indexing.py` (`POST /index`, dataset metadata). Each depends on `get_current_user` (Bearer token). |
| `session_manager.py` | Caches one `ChatSession` per `(user_id, chat_id)`. Now constructed with a shared `PneumaDB` passed into each `DBAPI`. |
| `chat_session.py` | Per-conversation object. Owns the `Conductor`, **always** restores/persists session state (the `PERSIST_CHAT_SESSION` toggle was removed). `chat(latest_user_message, files)` takes a single new message string and maintains `self.messages` internally. |
| `models.py` | Pydantic request/response models (renamed from `model.py`). Now also covers auth/users/groups: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`, `GroupCreateRequest/Response`, `SetPermissionRequest`, plus `PermissionKey` + `EndpointTag` enums. |
| `provenance/` | The provenance graph (`graph.py`) and code-generation helpers (`provenance_helper.py`). |
| `services/core/conductor/` | The Conductor agent — top-level planner. `main.py`, `state.py` (the `(T,S)` state), prompt factories. |
| `services/core/materializer/` | The Materializer agent — builds the target tables. `main.py`, `state.py`, prompt factories, `action_descriptions.py`. |
| `services/core/action_set/` | The shared **tool library**. `main.py` (`ActionSet` facade), `interfaces.py` (ABCs), `impl/` (one file per action). |
| `services/core/ir_system/` | Retrieval subsystem. `main.py` (`Retriever` facade), `retriever/` (factory + impls + persisted indices), `indexing.py`, prompt factory. |
| `services/core/api/` | Thin API clients the agents talk to: `db.py` (`DBAPI`), `language_model.py` (`LanguageModelAPI`). |
| `services/db/` | Post-sync, split behind the **`pneuma_db.py` (`PneumaDB`) facade**: `datasets/manager.py` (`DatasetManager` — dataset `.db` files, metadata, postgres registry, **group-permission-gated `get_accessible_local_datasets`**), `workspaces/manager.py` (`WorkspaceManager` — per-chat workspace DBs + session persistence; **this is the renamed old `db/main.py`**), `users/manager.py` (`UserDB` — **Postgres-backed** users/groups/permissions + auth tokens), `users/models.py`, `datasets/ingest_csv.py`. |
| `services/indexing/` | `IndexingService` — registers a dataset and builds retrieval indices. `connectors/` (CSV, PostgreSQL, base ABC), `metadata_store.py`. |
| `services/language_model/` | LLM + embedding implementations. `abstract_model.py`, `model_factory.py`, `impl/` (OpenAI, Azure OpenAI, Ollama, **Claude (`claude_llm.py`), Gemini (`gemini_llm.py`)**, mock). |
| `shared/` | Cross-cutting code: `config.py` (env-driven settings), `logger.py`, `parser.py` (JSON/code extraction), `str_processor.py`, `table_reader.py`, `table_serializer.py`, `schemas/` (typed data models). |
| `shared/schemas/` | `core/action.py` (action enum), `core/conductor.py`, `core/ir_system.py` (document types + `RetrieverType`), `db/document_type.py`, `language_model/` (message/role/option). |
| `docker/` | `core-service.dockerfile` for the backend. |
| `tests/` | Pytest suite mirroring the `src` tree (actions, conductor, materializer, ir_system, db, indexing, language_model, shared, provenance). |
| `data_src/` | Sample datasets (CSV) by domain: archeology, astronomy, biomedical, environment, hospital, legal, plus `target_tables/` referenced by `PneumaDB`. |
| `baselines/` | Comparison systems (`dsguru`, `smolagents`) — standalone, not imported by the backend. |
| `openwebui_functions/` | Python "pipe"/filter functions imported into OpenWebUI to bridge the UI to this backend. Not part of the backend runtime. |
| `pneuma-seeker-ui/` | Vendored OpenWebUI frontend (separate project; not analyzed here). |
| `docs/` | Architecture overview + figures. **This file lives here.** |
| `docs_understanding/`, `docs_memory/` | Working notes / experiment design (the latter is a forward-looking 6-tier-memory spec — *not* implemented; see §7). |
| `quick_start.ipynb`, `hospital_start_draft.ipynb` | End-to-end walkthroughs (index a dataset, then query). |

---

## 3. Core Modules

### 3.1 Entry & session layer

**`SessionManager`** — `session_manager.py`
- `get_chat_session(user_id, chat_id) -> ChatSession` — get-or-create, cached in a dict.
  Constructed with a shared `PneumaDB`; each new session gets a `DBAPI(..., pneuma_db=...)`
  and its own `LanguageModelAPI`.

**`ChatSession`** — `chat_session.py`
- Holds `messages`, a `dataset_name`, and a `Conductor`. **Always** restores prior state
  from the workspace DB on construction via `load_session` (the `PERSIST_CHAT_SESSION`
  toggle was removed post-sync; `load_session` now also returns the persisted `dataset_name`).
- `chat(latest_user_message, external_data_paths) -> generator[str]` — **takes a single new
  user message string** (not a full message list), appends it to `self.messages`, pairs up
  prior user/assistant turns into `UserConductorInteraction` history, delegates to
  `Conductor.chat(...)`, yields response chunks + a final `"DONE"`, then appends the
  assistant reply.
- `persist_session(dataset_name)` — writes the latest turn + full state/provenance back via `DBAPI`.

### 3.2 Conductor — the top-level agent

**`Conductor`** — `services/core/conductor/main.py`
- Owns: `ActionSet`, `Materializer`, `ConductorState`, `ProvenanceGraph`, the prompt
  factory, plus accumulated context (`retrieved_tables`, `enumerated_tables`,
  `external_tables`, `web_search_result`, `web_crawl_result`, `join_paths`).
- `chat(user_input, interaction_history, external_table_paths) -> generator`
  Runs a **ReAct planning loop** up to `MAX_CONDUCTOR_STEPS`:
  1. Build an env-state system prompt (current `(T,S)`, retrieved tables, history…).
  2. Ask the LLM for a JSON `{"plan": [{action, args}, ...]}`.
  3. Validate the plan; strip user-facing messages if real work is also planned.
  4. Execute each action via `__execute_action`, feeding outcomes back as messages.
  5. Stop when a `user_facing_communication` is produced (or force one at the end).
- `__execute_action(name, args)` — big `match` over the conductor-level actions:
  `situational_analysis`, `user_facing_communication`, `table_retrieve`,
  `web_search`, `web_crawl`, `table_enumeration`, `state_manipulation`,
  `materializer`, `python_executor`, `assumption_check`.
  - `state_manipulation` is how the agent edits `T` (target schemas + column
    descriptions) and `S` (the script).
  - `materializer` / `python_executor` trigger materialization (lazily, if needed)
    and execute `S` against the workspace DB.
- `set_prov_graph(graph)` — swaps the provenance graph and re-points `ActionSet` and
  `Materializer` at it (used when restoring a persisted session).

**`ConductorState`** — `services/core/conductor/state.py`
- The reified information need: `T: dict[str, AbstractDocument]`, `column_descriptions`,
  `S: str`, plus `is_T_materialized` / `is_S_executed` flags.
- `get_current_state_instance(nrows)` — JSON-serializable snapshot for the UI.

### 3.3 Materializer — builds the target tables

**`Materializer`** — `services/core/materializer/main.py`
- `materialize_T(T, column_descriptions, S, ...) -> (retrieved_tables, web_search,
  web_crawl, join_paths, materialized_T)`. Runs its own bounded ReAct loop
  (`MAX_MATERIALIZER_STEPS`) using the **materializer-level** action subset
  (relational + semantic ops): `table_projection`, `equality_join`, `table_union`,
  `semantic_join`, `semantic_column_generation`, `query_executor`, `python_executor`,
  `table_retrieve`, `table_enumeration`, plus optional `web_search`/`web_crawl`/`assumption_check`.
- Every successful op appends a **`ProvenanceNode`** (source `MATERIALIZER`) wired to
  its input nodes, and registers the resulting intermediate `Table` in `MaterializerState`.
- `__check_completion(T)` — done when every target id exists as a DataFrame whose
  columns are a *superset* of the target schema (extra columns allowed).
- `MaterializerState` (`materializer/state.py`) tracks retrieved/external/intermediate
  tables and is reset between runs; `reset_materialization_nodes()` on the graph keeps
  source nodes but drops prior materializer nodes.

### 3.4 ActionSet — the tool library

**`ActionSet`** — `services/core/action_set/main.py`
- A facade that instantiates one object per action (all subclasses under
  `action_set/impl/`) and exposes typed convenience methods: `retrieve_documents`,
  `retrieve_multi_topic_documents`, `discover_join_paths`, `join_equality`,
  `union_tables`, `project_table`, `execute_code`, `execute_query`, `join_semantic`,
  `generate_semantic_column`, plus the `generate_*_code` provenance helpers.
- Holds the **allow-lists** `valid_conductor_actions` / `valid_materializer_actions`
  (feature-flag gated by `config.ENABLE_*`), used by both agents to validate plans.
- `get_action_description(ActionNames)` — pulls each action's self-description into prompts.

**Action interfaces** — `action_set/interfaces.py`
- `Action(ABC)` — `get_name / get_description / get_input_schema / get_notes`.
- `Applicable.apply(input)` and `Executable.execute(input)` — the two call shapes.
- Each `impl/*.py` (e.g. `equality_join.py`, `semantic_join.py`, `python_executor.py`,
  `query_executor.py`, `table_projection.py`, `table_union.py`, `table_retrieve.py`,
  `table_enumeration.py`, `web_search.py`, `web_crawl.py`, `join_path_extraction.py`,
  `context_extraction.py`, `semantic_column_generation.py`, `situational_analysis.py`,
  `state_manipulation.py`, `user_facing_communication.py`) implements one tool.

**`ActionNames`** — `shared/schemas/core/action.py` — the canonical enum of action
string ids. Note `CONTEXT_EXTRACTION` maps to the wire name `"assumption_check"`.

### 3.5 IR / Retrieval subsystem

**`Retriever`** (IR facade) — `services/core/ir_system/main.py`
- `retrieve_documents(type, prompt, k, sample_only, sample_size)`,
  `retrieve_multi_topic_documents(...)`, `index_documents(type, docs)`.
- Delegates to a `RetrieverFactory`.

**`RetrieverFactory`** — `ir_system/retriever/retriever_factory.py`
- Maps `RetrieverType` → concrete retriever: `PNEUMA_RETRIEVER → PneumaRetriever`,
  `DOCUMENT_DB → DocumentDB`, `WEB_SEARCH → WebSearch`, `ENUMERATOR → Enumerator`,
  `WEB_CRAWL → WebCrawler`.

**`AbstractRetriever`** — `ir_system/retriever/interface.py`
- ABC: `retriever_type` (property), `load()`, `retrieve(query,k,sample_only,sample_size)`,
  `index(documents)`. This is the main retriever extension point.

**`PneumaRetriever`** — `ir_system/retriever/impl/pneuma_retriever.py`
- The table-discovery engine. **Hybrid retrieval**: BM25 (`bm25s`) full-text index +
  Chroma (`chromadb_deterministic`) vector index, fused by `HybridRetriever`
  (min-max normalized, `alpha=0.5`), with an optional **entity/keyword relevance
  booster** that scans DuckDB columns/values via regex.
- Indices are persisted on disk under `impl/indices/pneuma/{vector,fulltext}-index-<dataset>`.
- `index(documents, overwrite)` — builds those indices from per-column LLM "schema
  summaries" + sampled rows + table context.

### 3.6 Supporting API clients

**`LanguageModelAPI`** — `services/core/api/language_model.py`
- `chat(messages, option)`, `batch_chat(...)`, `encode(texts, option)`,
  `encode_tokenizer(texts)`. Resolves concrete LLM/embedding classes via
  `model_factory.get_llm/get_embed_model` from `config.LLM_PATH` / `EMBED_MODEL_PATH`.

**`DBAPI`** — `services/core/api/db.py` — thin pass-through to `PneumaDB` (§3.7); now
constructed with `pneuma_db=` injected by the `SessionManager`.

### 3.7 Data layer

**`PneumaDB`** — `services/db/pneuma_db.py` (the **facade**; the old monolithic
`services/db/main.py` was split + renamed in the sync). Composes two managers and
forwards to them:
- **`DatasetManager`** (`datasets/manager.py`) — DuckDB dataset stores: one `.db` per
  dataset under `services/db/datasets/<name>/<name>.db`, attached read-only into a
  workspace via `link_dataset_tables` (also supports a **PostgreSQL** source via the
  postgres extension). **New: `get_accessible_local_datasets(is_admin, group_permissions)`**
  filters visible datasets by the caller's group `dataset:access:<name>` permissions.
- **`WorkspaceManager`** (`workspaces/manager.py` = the **renamed old `db/main.py`**) —
  one `ws.db` per `(user_id, chat_id)` under `services/db/workspaces/<user>/<chat>/`,
  holding intermediate/target tables + the **session-persistence schema** (see §6).
  New chat-history methods: `get_user_chat_sessions`, `search_chat_sessions`,
  `delete_chat_session`, `load_chat_history`.
- Key forwarded methods: `ingest_dataset`, `link_dataset_tables`, `register_postgres_dataset`,
  `execute_query`, `register_temporary_df`, `persist_df`, `persist_session`, `load_session`.
- **Note for our memory layer:** the T2 episodic-log capture hook attaches around
  `WorkspaceManager.persist_session` (DuckDB-backed) — not the old `db/main.py` path.

**`UserDB`** — `services/db/users/manager.py` (**new subsystem, Postgres-backed**). The
identity + access-control substrate the rest of the auth layer rides on:
- **Users**: `create_user`, `get_user_by_id/email/token`, `verify_user`, password hashing
  (PBKDF2), session tokens (`create_session_token`/`get_user_by_token`/`revoke_token`).
- **Groups (hierarchical)**: `GroupRecord{group_id, name, parent_group_id}`; `create_group`,
  `list_group_ancestors` (walks the `parent_group_id` chain root→leaf, cycle-checked).
- **Permissions (inherited overlay)**: `GroupPermissionRecord{group_id, key, value}`;
  `get_effective_group_permissions` resolves a group's permissions by walking ancestors —
  **"parent applied first; child with the same key overrides ancestors"** (CLAUDE.md-style
  overlay precedence). `PermissionKey`: `admin`, `dataset:access:*`, `user:management`,
  `indexing:management`.
- **Why this matters to us:** this is a real backing for our **Level axis** (D20:
  User→Department→Institution ≈ group `parent_group_id` chain) and the **authorization**
  we deferred (D14/BACKLOG) — a potential reuse substrate, discussed separately (not yet wired).

**`IndexingService`** — `services/indexing/main.py`
- Orchestrates dataset registration + index build. `index_dataset(...)` /
  `start_indexing_run` + `run_indexing_job`: a `SourceConnector` discovers streams,
  documents are built (`Table` + optional `TableContext`), the dataset is registered
  for querying (CSV ingest or postgres connection string), and `PneumaRetriever.index`
  builds the indices. Run status tracked in `IndexingMetadataStore`.
- `SourceConnector` (`connectors/base.py`) ABC: `source_type`, `check_connection`,
  `discover`, `read`. Registry: `register_connector(type, cls)`. Built-ins: `csv`, `postgres`.

### 3.8 Shared schemas — the document model

**`AbstractDocument`** — `shared/schemas/core/ir_system.py`
- Base unit of information: `doc_id`, `retriever_type`, `content`, `metadata`, `path`,
  `last_node_id` (link to the provenance node that produced it). Equality/hash on
  `(doc_id, retriever_type)`.
- Subclasses: `Table` (content = DataFrame, rich `__str__` for prompts), `Text`,
  `TableContext`, `Knowledge`.
- `RetrieverType` enum: `PNEUMA_RETRIEVER`, `CONDUCTOR`, `ENUMERATOR`, `MATERIALIZER`,
  `DOCUMENT_DB`, `WEB_SEARCH`, `USER` (external/uploaded), `WEB_CRAWL`.

---

## 4. Data Flow — a `/chat` request end to end

1. **HTTP in.** `POST /chat` (`routers/chat.py`). **Requires a Bearer token** →
   `get_current_user` resolves the `UserRecord`; `user_id` comes from the authenticated
   user (no longer a body param). Body carries `chat_id`, `dataset_name` (sets
   `config.DATA_SOURCES`; required), the new `message`/`user_message`/`content` string,
   and `files`. Response is an **NDJSON `StreamingResponse`**.
2. **Session.** `SessionManager.get_chat_session(user_id, chat_id)` returns the cached
   `ChatSession` (which **always** restores prior `(T,S)` + provenance from the workspace DB).
3. **Producer thread.** `ChatSession.chat(...)` runs in a worker thread; its yielded
   strings are pushed through a `Queue` and re-emitted to the client as `log` /
   `assistant` / `done` payloads.
4. **Conductor loop.** `Conductor.chat`:
   - Loads any user-uploaded tables (`USER` provenance nodes) into the workspace DB.
   - Each step: build env-state prompt → LLM returns a JSON plan → validate → execute
     each action, appending outcomes to the message list.
   - Typical trajectory: `table_retrieve` (Pneuma hybrid retrieval + join-path
     discovery) → `state_manipulation` (define `T` + column descriptions, set `S`) →
     `materializer` → `python_executor` (run `S`) → `user_facing_communication`.
5. **Materialization.** `Conductor.__materialize_T_driver` → `Materializer.materialize_T`
   runs its own loop using relational/semantic ops, writing intermediate tables into the
   workspace DB and **growing the provenance graph** (each op = a `MATERIALIZER` node
   wired to its inputs).
6. **Execution.** `python_executor` runs `S` against the materialized `T` via
   `ActionSet.execute_code` → `DBAPI.execute_query` (DuckDB). The natural-language
   answer is the final `user_facing_communication`.
7. **Stream out + persist.** Each chunk is streamed; on stream close,
   `ChatSession.persist_session(dataset_name)` writes the new turn, `(T,S)`, the provenance
   graph, and the document sets into the workspace DB (always on post-sync).
8. **Side endpoints** read this same state: `/provenance/nodes/...`,
   `/combined/html/...` (state + materialization steps), `/all_tables/...` (ZIP of `T`),
   `/materializer_code/...` (the provenance graph rendered as runnable `.py`),
   `/execute_code/...`.

**Indexing flow** (prerequisite, separate): `POST /index` → `IndexingService` builds the
dataset DB + BM25/vector indices in a background task; status via `GET /index/<name>/latest`.

---

## 5. External Interfaces & Extension Points

These are the seams clearly designed for plug-in:

| Extension point | Where | How to extend |
|-----------------|-------|---------------|
| **HTTP API** | `routers/{auth,chat,indexing}.py` | FastAPI `APIRouter`s mounted in `main.py`; tags from `models.py:EndpointTag` (`auth`/`chat`/`indexing`). Endpoints take a `get_current_user` dependency (Bearer token). |
| **Auth / access control** | `routers/auth.py` + `services/db/users/manager.py` (`UserDB`) | Add a `PermissionKey`, gate an endpoint via `get_current_user_permissions` / `ensure_admin`; groups are hierarchical (`parent_group_id`) with inherited permissions. |
| **New action / tool** | `action_set/impl/` + `interfaces.py` | Implement `Action` (+ `Applicable`/`Executable`), add to `ActionNames`, wire into `ActionSet.__init__` and the action allow-lists. |
| **New retriever** | `ir_system/retriever/interface.py` | Subclass `AbstractRetriever`, add a `RetrieverType`, register in `RetrieverFactory`. |
| **New data source connector** | `services/indexing/connectors/base.py` | Subclass `SourceConnector`; `IndexingService.register_connector("type", Cls)`. Built-ins: CSV, PostgreSQL. |
| **New LLM / embedding provider** | `services/language_model/abstract_model.py` + `model_factory.py` | Implement `AbstractModel`, add a branch in `get_llm` / `get_embed_model` keyed on `LLM_PATH`/`EMBED_MODEL_PATH`. Existing: OpenAI, Azure OpenAI, Ollama, **Claude, Gemini**, mock. (Our Enhancer can reuse `claude_llm` — but note its `batch_chat` is a sequential loop, not the Anthropic Batches API, and `encode` raises `NotImplementedError`, so embeddings need another provider.) |
| **Prompt variants** | `*/prompt_factory*.py` | Conductor and Materializer ship ablation factories (`_no_context_extraction`, `_no_state`) — swap-in alternate prompting strategies. |
| **Reranking strategy** | `pneuma_retriever.py:RerankingMode` | `NONE` vs `LLM`; set in `PneumaRetriever.__init__`. |
| **Configuration** | `shared/config.py` (env / `.env`) | Feature flags (`ENABLE_WEB_SEARCH`, `ENABLE_SEMANTIC_JOIN`, `ENABLE_CONTEXT_EXTRACTION`, our `ENABLE_MEMORY_INJECTION`, …), step caps, retrieval/semantic tuning. Post-sync also: `ANTHROPIC_API_KEY`/`GEMINI_API_KEY`, `AUTH_*`, `POSTGRES_*` (the `PERSIST_CHAT_SESSION` toggle was removed). |
| **Frontend bridge** | `openwebui_functions/*.py` | OpenWebUI "pipe"/filter functions that call this backend; imported into the UI as JSON. |

---

## 6. Archive & Provenance Graph — implementation & interface

> **Terminology note:** there is **no class or module literally named `archive`** in the
> codebase (verified by search). I read your "archive" as the **persistence / storage
> layer** — i.e. how state and indices are durably stored and reloaded. The two concrete
> things that play that role are (A) the DuckDB persistence schema and (B) the on-disk
> retrieval indices. If you meant something else by "archive," flag it (see §7).

### 6.1 Provenance graph

**Implementation:** `src/pneuma_seeker/provenance/graph.py` (+ code generators in
`provenance/provenance_helper.py`).

- **`ProvenanceNode`** — `id` (uuid4), `source_retriever: RetrieverType`,
  `python_code`, `description`, `parents`, `children`. `add_child` keeps the
  parent/child links symmetric.
- **`ProvenanceGraph`** — `nodes: dict[id, ProvenanceNode]`; optional default root
  (`import pandas as pd; tables = {}`). Interface:
  - Mutation: `add_node(node, overwrite=False)`, `connect(parent, child)`,
    `reset_materialization_nodes()` (drop `MATERIALIZER` nodes, keep sources).
  - Query: `get_nodes(filters)`, `get_node(filters)`, `get_node_by_id(id)`,
    `trace_upstream/trace_downstream`, `topological_sort()` (Kahn, cycle-warned).
  - Rendering: `get_graph_code()` (concatenate node code in topo order → a runnable
    Python program reproducing `T`), `get_graph_explanation()` (per-step Markdown),
    `to_text()`, `get_graph_visualization()` (pyvis HTML).
- **Who writes it:** the `Materializer` adds a node per operation and wires it to its
  input tables' `last_node_id`; the `Conductor` adds `USER` nodes for uploaded tables.
  Every `AbstractDocument` carries `last_node_id` so the graph and the data stay linked.
- **Who reads it:** endpoints `/provenance/nodes/...`, `/combined/html/...`,
  `/materializer_code/...`.

### 6.2 Persistence "archive" (DuckDB)

**Implementation:** `services/db/workspaces/manager.py` (`WorkspaceManager`, behind the
`services/db/pneuma_db.py` facade — renamed from the old `services/db/main.py`), surfaced
through `services/core/api/db.py` (`DBAPI`).

- **Workspace persistence schema** (`__define_all_persistence_tables`), one `ws.db`
  per `(user_id, chat_id)`:
  `chat_history`, `conductor_state` (the `(T,S)` + `join_paths`), `provenance_nodes`,
  `provenance_edges`, `documents`, `document_metadata`, `state_document_roles`.
- **Write:** `persist_session(...)` — inserts the latest user/assistant turn, a new
  `conductor_state` row, all provenance nodes then edges, and each document tagged by
  role (`DocumentType`: target / retrieved / enumerated / web-search / web-crawl).
  When `ENABLE_FINE_GRAINED_STATE_CHANGE_TRACKING` is off, it snapshots by wiping the
  prior state tables first (keep-latest semantics).
- **Read:** `load_session(...)` — rebuilds `messages`, `ConductorState`,
  `ProvenanceGraph` (nodes + edges), the document sets, and the persisted `dataset_name`,
  re-attaching dataset tables as needed. `ChatSession.__init__` always calls this
  (the `PERSIST_CHAT_SESSION` gate was removed post-sync).
- **Dataset archive:** ingested datasets are stored as DuckDB `.db` files under
  `services/db/datasets/`; retrieval **indices** are persisted under
  `ir_system/retriever/impl/indices/pneuma/{vector,fulltext}-index-<dataset>/`
  (Chroma + BM25). These are the durable, reloadable retrieval artifacts.

---

## 7. Open Questions / Please Confirm

1. **"Archive" meaning.** No literal `archive` exists. I mapped it to the DuckDB
   persistence layer + on-disk indices (§6.2). Did you mean (a) that persistence layer,
   (b) the on-disk retrieval indices specifically, (c) the provenance "history" of past
   sessions, or (d) a concept from the *planned* memory experiment (below)? This changes
   what §6 should emphasize.

2. **`docs_memory/system_architecture.md` is aspirational, not implemented.** It
   specifies a "ClinicalPneuma" **6-tier hierarchical memory** system (transient +
   persistent tiers, an `Enhancer` background agent, a schema-routing property graph,
   vector stores). I found **no code** implementing tiers 3–6, the `Enhancer`, or a
   vector memory store. Given the branch name `feat-memory-experiement`, I assume that
   doc is the design target for upcoming work — confirm whether this map should also
   sketch where that memory subsystem would attach (likely: a new persistent layer
   beside `PneumaDB`, a read path injected into Conductor/Retriever prompts, and an
   offline consumer of the `chat_history`/`provenance` tables).

3. **`docs_understanding/`** contains generated HTML (`00_project_overview.html`,
   module pages) + a `CHECKPOINT.md`. Is that an output you maintain, or scratch I can
   ignore? It overlaps with this file's purpose.

4. **Two notebooks** (`quick_start.ipynb`, `hospital_start_draft.ipynb`) and the
   `baselines/` systems are out of the backend runtime; I treated them as
   demos/comparisons rather than core. Confirm that's the right scope.

5. **Default model.** `config.LLM_PATH` defaults to `o3-2025-04-16` and the codebase
   routes `gpt/o3/o4` names to (Azure) OpenAI. If the memory experiment expects a
   specific model/provider, that wiring lives in `model_factory.py` and would need a
   branch — worth confirming before building on it.
