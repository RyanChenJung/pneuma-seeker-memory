# ClinicalPneuma: 6-Tier Memory Architecture Implementation Guide

## 1. Project Overview & Objective

You are tasked with implementing the core memory subsystem for **ClinicalPneuma**, an self-evolving multi-agent framework designed for clinical EHR analytics.
The goal is to implement a **6-Tier Hierarchical Memory System** that strictly separates real-time clinical reasoning (Transient Memory) from asynchronous skill synthesis and knowledge retention (Persistent Memory).

## 2. Core Architectural Principles (Strict Constraints)

Before writing any code, adhere to these non-negotiables:

1. **Asynchronous Evolution:** Persistent memories are NEVER updated during a live user session. A dedicated `Enhancer` agent handles background consolidation (Post-Session).
2. **Decoupled Read/Write:** Frontline agents only have `Read` access to persistent memory. Only the `Enhancer` has `Write` authority.

---

## 3. The 6-Tier Memory Specification

### [Transient Memory Layer] (Real-time, Session-scoped)

#### Tier 1: Short-Term Reasoning Buffer

- **Role:** The active context window for the `Conductor`.
- **Data Structure:** Standard LLM message history (`List[Dict]`).
- **Lifecycle:** Strictly purged upon session completion to prevent context contamination.

#### Tier 2: Episodic State Log

- **Role:** The append-only raw recording of the entire session (The "black box" flight recorder).
- **Data Structure:** JSON/JSONL logging.
- **Content:** User prompts, Conductor's internal thoughts (ReAct trace), tool calls, SQL execution outcomes (success/errors from Materializer), and user feedback.
- **Lifecycle:** Saved to disk/DB. Consumed asynchronously by the `Enhancer` later.

### [Persistent Memory Layer] (Long-term, Global-scoped)

#### Tier 3: User Memory

- **Role:** Stores persona constraints and inquiry habits.
- **Storage:** Vector Database (e.g., Qdrant/Chroma) for semantic retrieval.
- **Impact:** Accelerates _Latent Intent Convergence_.

#### Tier 4: Organization Memory

- **Role:** Stores clinical definitions, guidelines, and hospital-specific protocols.
- **Storage:** Vector Database + Document Store.
- **Impact:** Provides _Contextual Priors_ to align with institutional standards.

#### Tier 5: Schema Routing Memory (CRITICAL)

- **Role:** A virtual overlay patching messy EHR databases, preventing AI-induced schema drift.
- **Storage:** **Property Graph Database** (e.g., Neo4j or NetworkX mapped to JSON/Vector).
- **Data Structure:**
  - **Nodes:** Physical EHR Tables and Columns (e.g., `Patient`, `Admissions`).
  - **Edges (Directed):** Validated SQL Join Paths.
  - **Edge Properties (JSON Payload):**
    - `Empirical_Utility_Score` (Float): Frequency/reliability weight.
    - `Associated_Experience` (String/JSON): Tribal knowledge and "Negative Constraints" (e.g., _"Do not join on ID, use patient_id. Failed log #123"_).
- **Impact:** Transforms blind schema inference into high-confidence graph retrieval, drastically improving _Execution Accuracy_.

#### Tier 6: Long Memory

- **Role:** Stores abstract procedural skills and high-level reasoning strategies.
- **Storage:** Vector Database for few-shot prompt injection.
- **Impact:** Reduces _Reasoning Latency_ by reusing successful problem-solving templates.

---

## 4. Multi-Agent Orchestration & Permissions

Implement the following 4 agents with strict access controls:

1. **CONDUCTOR (Frontline Orchestrator)**
   - **Permissions:** `Read/Write` Tier 1 & 2. `Read` Tier 3, 4, 5, 6.
   - **Task:** Receives query, retrieves relevant memory, formulates logic, dispatches to Materializer.

2. **RETRIEVER (Search Engine)**
   - **Permissions:** `Read` Tier 3, 4, 5, 6.
   - **Task:** Injects high-value facts/paths directly into Conductor's Tier 1 buffer.

3. **MATERIALIZER (Execution Sandbox)**
   - **Permissions:** `Execute` on actual EHR DB (Read-only). `Write` logs to Tier 2.
   - **Task:** Executes SQL/Python safely. Returns deterministic results or sanitized error logs.

4. **ENHANCER (Background Synthesizer)**
   - **Permissions:** `Read` Tier 2. `Read/Write/Delete` Tier 3, 4, 5, 6.
   - **Task:** Runs completely decoupled during off-peak hours.

---

## 5. Memory Management Mechanism (Enhancer Logic)

The `Enhancer` implementation must follow this strict pipeline:

1. **Trigger:** Scans Tier 2 (Episodic Logs) for threshold rewards ($R_{execution} + R_{user}$) and "instructive failure trajectories".
2. **Evaluation (LLM-as-a-judge):**
   - Extracts the _Architectural Triplet_: `[Clinical Intent, Associated Experience, Utility Score]`.
3. **Micro A/B Validation:**
   - Before committing to persistent memory, mathematically evaluate if the new triplet outperforms existing records.
4. **Action Routing:**
   - **Skip:** Reject redundant/inferior inputs.
   - **Merge:** Extract successful sub-components to synthesize a hybrid memory.
   - **Insert:** Direct integration for novel, high-utility structures.
5. **Retention & Pruning:** Implement a cron-like job to decay `Utility Score` based on dormancy, purging idle records when token capacity is reached.
