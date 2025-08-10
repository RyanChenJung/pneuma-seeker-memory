from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.state import InformationNeedState
from pneuma_seeker.core.conductor.table_enumerator import table_id_enumerator
from pneuma_seeker.core.ir_system.ir_data_model import (
    AbstractDocument,
    RetrieverType,
    convert_multi_retriever_results_to_str,
)


class ConductorPromptFactory:
    def get_sys_prompt(self, iteration_limit: int) -> str:
        return f"""You are the Conductor.  
Your mission is to guide the user from vague needs to a fulfilled answer by:
1. Defining accurate target schemas and column descriptions.
2. Materializing those schemas with real data.
3. Defining and executing SQL queries to produce the final answer.
4. Communicating results clearly.

The Information Need State has 3 parts:
- target_schemas: dict[schema_id -> list of columns]
- column_descriptions: dict[schema_id -> dict[column -> description]]
- sqls: list of SQL queries over the target schemas

Each step has at most {iteration_limit} iterations.  
In each iteration, you **must** choose exactly one action:

1. **internal_reasoning** - Think privately about the next best step.  
   Format: {{"intent": "internal_reasoning", "message": "..."}}

2. **tool_call** - Call one tool to make progress.  
   Format: {{"intent": "tool_call", "tool": "<tool_name>", "args": {{...}}}}

   Tools:
   - ir_system: Retrieve tables/text. Args: {{"prompt": "<retrieval query>"}}
   - state_manipulation: Update schemas or SQLs.  
     Args:  
       {{ "target_schemas": {{...}}, "column_descriptions": {{...}} }}  
       OR {{ "sqls": ["..."] }}  
       OR both together.  
   - materializer_engine: Fill rows of target schemas. Args: {{"note": "<instructions>"}}
   - sql_engine: Execute state's SQLs on materialized schemas. Args: {{}}
   - categorical_column_information: List unique values in columns.  
     Args: {{"id": "<retrieved_table_id>", "columns": ["col1", "col2"]}}

3. **communicate_with_user** - Summarize progress, ask clarifying questions, or present results.  
   Format: {{"intent": "communicate_with_user", "message": "..."}}

**Rules**:
- Never mix action types in one iteration.
- Progress toward **executing SQL successfully** within the step limit.
- Avoid repeating the same tool with identical args unless state has changed.
- Do not design SQLs before schemas are clear.
- Confirm ambiguities (e.g., multiple candidate tables, unclear time ranges) by communicating with the user before materializing.
- Always output **valid JSON only**, no extra text.

Your output **must** be exactly one JSON object matching one of the above formats.
"""
    
    def get_env_state_prompt(
    self,
    curr_iteration: int,
    max_iteration: int,
    info_need_state: InformationNeedState,
    interaction_history: list[HumanConductorInteraction],
    actions_taken: list[str],
    curr_retrieval_results: dict[RetrieverType, list[AbstractDocument]],
    human_input: str,
) -> str:
        return f"""Iteration {curr_iteration}/{max_iteration}

STATE:
{info_need_state}

PREVIOUS ACTIONS IN THIS STEP:
{actions_taken}

RECENT USER INTERACTIONS:
{self.__convert_interactions_to_str(interaction_history)}

RETRIEVED DATA:
{convert_multi_retriever_results_to_str(curr_retrieval_results)}

OTHER TABLE IDS WITH SIMILAR NAMING PATTERNS (LISTED ONLY; NOT RETRIEVED):
{table_id_enumerator(curr_retrieval_results[RetrieverType.PNEUMA]) if len(curr_retrieval_results.keys()) > 0 else dict()}

CURRENT USER INPUT:
{human_input}

**Reminders**:
- If multiple relevant retrieved tables exist, confirm with user which one(s) to use before defining target schemas.
- Target schemas must be consistent: each table represents one coherent concept, columns are complete and unambiguous.
- SQLs must only reference target schema IDs and exact column names.
- Aim to materialize schemas and execute SQL before iteration limit.

Decide your next action and output one JSON object in one of these forms:
{{"intent": "internal_reasoning", "message": "..."}}
{{"intent": "tool_call", "tool": "<tool_name>", "args": {{...}}}}
{{"intent": "communicate_with_user", "message": "..."}}"""

    def sql_sanity_checking_prompt(self):
        return """You are a SQL query fixer for DuckDB. 
Given an input SQL query, check for syntactic or semantic errors (case sensitivity, unescaped identifiers, invalid field names, type mismatches, or unsupported functions).
Ensure the query ONLY accesses available tables in the target schemas. If not, convert it to an equivalent SQL query.
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

    def __convert_interactions_to_str(self, interactions: list[HumanConductorInteraction]) -> str:
        interaction_repr = ""
        for interaction in interactions:
            interaction_repr += f"- {interaction}\n"
        interaction_repr = interaction_repr.strip()
        return interaction_repr
