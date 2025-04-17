base_table_producer_prompts = {
    "tables_selector": """You are an experienced data scientist. You are given:
- A table, represented by its schema, a description of what it contains, and some sample rows. The pipe character (`|`) is used as the separator for both columns and row values.
- A target schema that needs to be constructed using one or more of the available tables.

Your task is to determine whether this table is **relevant** for constructing the target schema — either fully or partially. A table is considered relevant if it provides **any** useful information toward fulfilling the target schema, such as:
- Matching any of the target columns exactly,
- Providing a column that can be transformed into a target column,
- Contributing auxiliary information (e.g., geographic clues from `city` or `address` that help construct `Is in Bay Area`).

Err on the side of inclusion: if you think even **one** column might help, mark the table as **relevant**.

End your reasoning with the following exact format, to ease parsing:

Relevant: yes/no
""",
    "row_extender_step_1": """You are an experienced data scientist. You are given:
- A list of tables, each with its schema, a short description, and a few sample rows.
- The pipe character (`|`) is used to separate both column names and values.

Your task is to **analyze and describe** what each table represents, and then identify **which tables describe the same kind of real-world entity or object** (such as people, products, companies, events, etc.).

Only group tables that:
- Refer to the same kind of entity
- Can be combined via **row extension** (i.e., vertical stacking)
- Even if the columns are not exactly the same, their rows should be logically stackable (e.g., two tables of products with different attributes)

Do **not** group tables that refer to different concepts/entities, even if they share similar-looking columns.

Finish with a list of compatible groups like:
Row extension groups: Group 1: Table_0, Table_2 Group 2: Table_3, Table_4 ... (or none if no combinations are found)""",
    "row_extender_step_2": """You are an experienced data scientist. You have already analyzed the tables and identified which ones can be combined via row extension (i.e., vertically stacked) because they refer to the same kind of real-world entity.

You are given:
- A list of tables (description + schemas + samples)
- Your own prior reasoning and a list of row-extension groups (e.g., Group 1: Table_0, Table_2)

Your job is to create a JSON plan that shows how each group can be merged via row extension.

Instructions:
- For each group, create a **unified schema** by merging **semantically equivalent** columns (e.g., "Customer_Rating" and "RATING" should both become "Rating")
- Use **simple, general, and meaningful** names for the unified columns (e.g., "Phone", "Address", "Rating", "Reviews")
- For each table, create a mapping from its original column names to the unified schema
- It's okay if some original columns do not exist in the unified schema — just leave them unmapped
- Do not include duplicate columns in the unified schema — each concept should appear only once

Output directly the following format without extra texts or explanations:

Format if row extension groups exist:
```json
[
  {
    "Tables": ["Table_0", "Table_2"],
    "Unified Schema": ["Column1", "Column2", ...],
    "Mappings": {
      "Table_0": {"OrigColA": "Column1", "OrigColB": "Column2", ...},
      "Table_2": {"ColX": "Column1", "ColY": "Column2", ...}
    }
  }
]```

Format if row extension groups are empty/none:
```json
[]```""",
    "join_planner": """You are a highly skilled data engineer. You are given:
- A list of tables (with descriptions, schemas, and sample rows)
- The goal is to **join all tables** together into a final unified table by **step-wise horizontal merging**.

Assumptions:
- All tables should be joinable via appropriate key columns, either directly or through intermediate tables.
- You can choose any join order as long as all tables are included by the end.
- You should identify the most appropriate **key columns** for joining each pair of tables based on semantics or value similarity.
- The operations will be carried out using either SQL or semantic joins.

Your task:
- Construct a step-by-step join plan as a **list of operations**, where each operation joins two tables (or previous join results).
- Each step should specify:
  - The two input tables, one of which may be a join result from the prior step.
  - The columns being used for the join
  - The resulting table name for that step (e.g., "Join_1", "Join_2", etc.)

Output your answer directly as a JSON object with the following format without any extra explanations or formatting:

```json
[
  {
    "Join Result": "Join_1",
    "Left Table": "Table_A",
    "Right Table": "Table_B",
    "Left Join Key": "Column_X",
    "Right Join Key": "Column_Y"
  },
  {
    "Join Result": "Join_2",
    "Left Table": "Join_1",
    "Right Table": "Table_C",
    "Left Join Key": "UserID",
    "Right Join Key": "Customer_ID"
  }
]```""",
    "classification_prompt": """You are a highly skilled data engineer. You are given:
- A description of a join operation between two tables.
- Sample values for each join key column from both tables.

Your task is to classify whether the join can be performed using a standard SQL join (e.g., matching IDs or exactly matching names), or if it requires a *semantic join*. A semantic join is needed when the values differ in representation — for example, abbreviations, name variations, different formats, or different languages — and require normalization, transformation, or external knowledge to align correctly.

Carefully examine the values. If they are *not exactly equal*, and some interpretation or resolution is needed to make the join work, it is a semantic join.

At the end of your reasoning, respond in the following format (for easy parsing):

- Operation classification: standard or semantic"""
}


schema_processor_prompts = {
    "schema_generator_system_prompt": """You are an expert in data integration. Your task is to determine the minimum target schema---the smallest set of necessary columns required to directly answer a given question without having to perform separate aggregate operations (e.g., performing average on a column). The first column must always be the ID (primary key).

However, the target schema must be self-sufficient: all essential attributes must be included so that the question can be answered without requiring joins or additional lookups. For example, restaurant names must be included, not just their IDs, as data scientists need them for interpretation.

Output your schema strictly as a Python list, without any extra formatting, explanations, or text. The output must be directly parseable as a Python list.

Example:
Input: "What are the best restaurants in Chicago with ratings above 3.5?"
Output:
['Restaurant ID', 'Restaurant Name', 'Rating', 'Location']

This ensures that a data scientist can efficiently filter and interpret the dataset.""",
    "table_descriptor": "You are an experienced data scientist. You are given the schema of a table, along with some sample row(s), with the pipe character (`|`) as the separators of columns and row values. Your goal is to briefly guess what the table likely represents. Output your guess directly without any extra formatting.",
    "column_renamer": """You are an experienced data scientist. You are given:

- The schema of a table, along with some sample row(s), with the pipe character (`|`) as the separators of columns and row values.
- A description of what the table represents.
- A column from the schema to be renamed.

Your goal is to rename the specified column to make it more explicit and descriptive while considering the other columns in the schema and the overall description of the table. Start by thinking for a bit and end your thought with this exact format (to ease parsing of your answer):

New column name: ...""",
    "description_combinator": 'You are an expert data scientist skilled in precise reasoning. Your task is to synthesize a single, concise description from several similar ones. Always choose the most specific term when multiple levels of abstraction are mentioned (e.g., if both "retail stores" and "businesses" are mentioned, only use "retail stores"). Do not include both general and specific terms together. Be concise, avoid repetition, and return only the refined description—no extra formatting or commentary.',
}








# DEPRECATED
clear_schema_system_prompt = """You are given a schema of a table, along with some sample row(s), with the pipe character (`|`) as the separator of columns and row values. Your goal is to update the schema to be more explicit and descriptive. For example, the column 'AvgRating' becomes 'Average Rating'. Be careful not to miss any columns (e.g., if there are `ID` and `School ID`, handle them both).

Output your result strictly as a Python list consisting of the new column names, without any extra formatting, explanations, or text. The output must be directly parseable as a Python list."""

clear_schema_system_prompt_neo = """You are given a column of a table, along with a description of what it likely represents. Please rename the column to be more descriptive and easy to understand based on the description while keeping it compact. If there is no description for a column, keep the name as is. Output the name directly without any extra formatting, explanations, or text."""

plan_generator_first_step_system_prompt = """You are a helpful data scientist.

You will be provided with:
- A question in natural language.
- A list of available tables, each represented with its schema and a sample row.
- A target schema, which defines the supposedly relevant table to answer the question.

Your goal is to determine which table among the available tables consists of the superset or the exact set of the target schema. If the table exists, return "operation": "select_table" and specify the table.
If table join(s) is **strictly** necessary, then return "operation": "join" and specify the necessary joins.

The output format for selecting a single table:
{
    "operation": "select_table",
    "tables_involved": ["Table_0"],
    "description": "Select Table_0."
}

While for joining tables:
{
    "operation": "join",
    "tables_involved": ["Table_0", "Table 1"],
    "description": "Join Table_0 with Table_1 on Table_0.Department ID and Table_1.DeptID"
}

Output your result strictly as a Python dictionary, without any extra formatting, explanations, or text. The output must be directly parseable as a Python dictionary."""
