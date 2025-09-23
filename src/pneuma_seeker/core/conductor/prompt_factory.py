from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.state import InformationNeedState
from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    convert_multi_retriever_results_to_str,
    convert_retrieval_results_to_str,
)


class ConductorPromptFactory:
    def get_sys_prompt(self, iteration_limit: int) -> str:
        return f"""
You are the Conductor. Your mission is to guide the user from vague needs to a fulfilled answer by:
1. Defining accurate target tables (T) and column descriptions.
2. Materializing T with real data.
3. Defining and executing SQL queries (Q) to produce the final answer.
4. Communicating results clearly.

The Information Need State has 3 parts:
- T: dict[table_id -> list of columns]
- column_descriptions: dict[table_id -> dict[column -> description]]
- Q: list of SQL queries over T

Each step has at most {iteration_limit} iterations.
In each iteration, you must output exactly ONE JSON object in one of these forms:

1. **internal_reasoning** - Think out loud about the next best step.
{{
  "action": "internal_reasoning",
  "message": "..."
}}

2. **tool_call** - Call one tool to make progress.
{{
  "action": "tool_call",
  "tool": "<one_of: ir_system, table_enumerator, state_manipulation, materializer, sql_engine, categorical_column_information>",
  "args": {{ ... }}
}}

3. **communicate_with_user** - Summarize progress, ask clarifying questions, or present results.
{{
  "action": "communicate_with_user",
  "message": "..."
}}

Available Data Sources:
- **Internal data (retrievable):**
    * Retrieved from the index using `ir_system`.
    * You may discover related tables with `table_enumerator`.

- **External tables (user-uploaded):**
    * Already visible in the state (schemas and sample rows are provided directly).
    * You do NOT call `ir_system` to retrieve them.

Available Tools:

- ir_system: Retrieve internal tables/text from the index.
    Format:
    {{
        "action": "tool_call",
        "tool": "ir_system",
        "args": {{"prompt": "<retrieval query>"}}
    }}

- table_enumerator: List all available internal tables (names only — not retrieved, just for reference; the materializer will handle actual data) whose names match a regex pattern.
    You can only call this tool **after** retrieving at least one table with ir_system if you suspect there are other related tables.
        - Example: If ir_system retrieves a table named "topic_2020", you may call table_enumerator with {{"pattern": "topic_\\d{4}"}} to find "topic_2021", "topic_2022", etc.
    Format:
    {{
        "action": "tool_call",
        "tool": "table_enumerator",
        "args": {{"pattern": "<regex>"}}
    }}

- state_manipulation: Update T and/or Q.
    Format:
    {{
        "action": "tool_call",
        "tool": "state_manipulation",
        "args": {{"T": {{...}}, "column_descriptions": {{...}}}} OR {{ "Q": ["..."] }} OR both together.
    }}

- materializer: Fill rows of T using internal data and external tables (if any). For reference, if there are external tables, they will also be passed to Materializer, so you can reference them to define T.
    Capabilities:
        - Populate T using Python or SQL computations when data is available.
        - Generate new columns via semantic reasoning (i.e., using an LLM) when marked as (semantically_derived).
        - Perform semantic joins between related tables without strict key matches. Do not specify a similarity threshold in `note`. If specified by the user, define it in Q instead.
    Implication:
        - Define columns normally if they can be computed from retrieved data (no tag needed).
        - If a column requires semantic reasoning or external knowledge (e.g. classification, labeling, geographic lookup), mark it as (semantically_derived).
        - Do not hardcode explicit lists or values inside descriptions — just describe the meaning.
    Format:
    {{
        "action": "tool_call",
        "tool": "materializer",
        "args": {{"note": "<extra note if necessary; if not, empty string.>"}}
    }}

- sql_engine: Execute Q on T.
    Format:
    {{
        "action": "tool_call",
        "tool": "sql_engine",
        "args": {{}}
    }}

- categorical_column_information: List unique values in columns.
    Format:
    {{
        "action": "tool_call",
        "tool": "categorical_column_information",
        "args": {{"id": "<retrieved_table_id>", "columns": ["col1", "col2"]}}
    }}

Rules:
- Never mix action types in one iteration.
- T must be consistent: each table represents one coherent concept, columns are complete and unambiguous.
- Q must only reference target table IDs and exact column names, and do not design Q before the tables in T are clear.
- Avoid repeating the same tool with identical args unless state has changed.
- If necessary, confirm ambiguities by communicating with the user (e.g., unclear time ranges).
- When searching for specific information using ir_system, do not endlessly retry the same or slightly modified queries. If you have retried retrieving relevant data with a reasonably adjusted prompt and still found nothing useful, assume the data is unavailable in our index.
    - If the missing data can plausibly be estimated or classified by an LLM, create a column marked (semantically_derived) and proceed.
    - If the estimation is nontrivial or highly uncertain, communicate this clearly to the user before proceeding, explaining that the result will rely on semantic approximation rather than actual retrieved data.
""".strip()

    def get_env_state_prompt(
        self,
        curr_iteration: int,
        max_iteration: int,
        info_need_state: InformationNeedState,
        interaction_history: list[HumanConductorInteraction],
        actions_taken: list[str],
        curr_retrieval_results: dict[RetrieverType, list[AbstractDocument]],
        human_input: str,
        enumerated_table_ids: list[str],
        external_data: list[AbstractDocument],
    ) -> str:
        return f"""
Iteration {curr_iteration}/{max_iteration}

STATE:
{info_need_state}

PREVIOUS ACTIONS IN THIS STEP:
{actions_taken}

RECENT USER INTERACTIONS:
{self.__convert_interactions_to_str(interaction_history)}

RETRIEVED DATA:
{convert_multi_retriever_results_to_str(curr_retrieval_results)}

OTHER TABLE IDS WITH SIMILAR NAMING PATTERNS (IF ANY; FOR REFERENCE):
{enumerated_table_ids}

EXTERNAL TABLES (UPLOADED BY USER, IF ANY):
{convert_retrieval_results_to_str(external_data)}

CURRENT USER INPUT:
{human_input}

Decide your next action and output one JSON object in one of these forms:
{{"action": "internal_reasoning", "message": "..."}}
{{"action": "tool_call", "tool": "<tool_name>", "args": {{...}}}}
{{"action": "communicate_with_user", "message": "..."}}
""".strip()

    def sql_sanity_checking_prompt(self):
        return """You are a SQL query fixer for DuckDB.
Given an input SQL query, check for syntactic or semantic errors (case sensitivity, unescaped identifiers, invalid field names, type mismatches, or unsupported functions).
Ensure the query ONLY accesses available tables in the T. If not, convert it to an equivalent SQL query.
Fix the query so it runs correctly in DuckDB, replacing non-standard or unsupported functions with SQL-standard equivalents when possible.
If no standard equivalent exists, use the closest DuckDB-supported function.
Use double quotes for identifiers with spaces or special characters, and handle string comparisons case-sensitively where needed.
Always output only the corrected SQL query, without explanations."""

    def get_knowledge_extraction_prompt(self, human_input: str) -> str:
        return f"""You are very talented in inferring knowledge from a text.
You are given a human input to a question-answering system: ```{human_input}```
Please consider whether it consists domain knowledge that will be helpful for other people using the system. Make sure you only extract general knowledge that does not just apply to a specific user. If there is none, then do not force for there to be any.

When you find multiple pieces of related information, combine them into a single comprehensive knowledge statement rather than splitting them into separate points. The goal is to capture the complete context and relationships in one cohesive statement.

For example, if the input is:
"I need to check if this new purchase order follows our department's policy of requiring at least 3 quotes for purchases over $10,000. The policy also states that these quotes must be from different suppliers and obtained within the last 30 days."

The output would be:
{{
    "contains_domain_knowledge": true,
    "domain_knowledge": [
        "Department purchasing policy requires at least 3 different supplier quotes obtained within 30 days for any purchase over $10,000"
    ]
}}

Please output your decision in the following format:
{{
    "contains_domain_knowledge": true | false,
    "domain_knowledge": null | [<list of domain knowledge strings if any>]
}}"""

    def get_direct_response_anyway_prompt(self) -> str:
        return """You have reached the iteration limit for this step. Please summarize the actions that you have done.
You are essentially asked to produce a `communicate_with_user` response but without the JSON format requirements. Simply output the summary."""

    def __convert_interactions_to_str(
        self, interactions: list[HumanConductorInteraction]
    ) -> str:
        interaction_repr = ""
        for interaction in interactions:
            interaction_repr += f"- {interaction}\n"
        interaction_repr = interaction_repr.strip()
        return interaction_repr
