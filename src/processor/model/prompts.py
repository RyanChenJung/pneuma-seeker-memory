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
    "row_extender_step_2": """You are an experienced data scientist. You have already analyzed the tables and identified which ones can be unioned together because they refer to the same kind of real-world entity.

You are given:
- A list of tables (description + schemas + samples)
- Your own prior reasoning and a list of union groups (e.g., Group 1: Table_0, Table_2)

Your job is to create a JSON plan that shows how each group can be unioned.

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
    "Output Table ID": "Union_1",
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

- Operation classification: standard or semantic""",
    "std_join": """You are a highly skilled data engineer.
You are given two tables, represented by their IDs, descriptions, schemas, and sample rows.

Your goal is to create a SQL script (SQLite) to join these tables through a given left and right join keys. Refer to the IDs as identifiers in the script.

Output the SQLite script directly without any extra formatting or explanation.""",
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
    "table_descriptor": "You are an experienced data scientist. You are given the schema of a table, along with some sample row(s), with the pipe character (`|`) as the separators of columns and row values. Your goal is to briefly guess what the table likely represents. Synthesize the description; do not simply enumerate the columns. Output your guess directly without any extra formatting.",
    "table_descriptor_with_initial_description": "You are an experienced data scientist. You are given the schema of a table, along with some sample row(s), with the pipe character (`|`) as the separators of columns and row values. You are also given an initial description of what the table represents. Your goal is to enhance the initial description about what the table reprsents based on what you observed on the data while keeping it general (not too focused on specific row values). Synthesize the description; do not simply enumerate the columns. Output your description directly without any extra formatting.",
    "column_renamer": """You are an experienced data scientist. You are given:

- The schema of a table, along with some sample row(s), with the pipe character (`|`) as the separators of columns and row values.
- A description of what the table represents.
- A column from the schema to be renamed.

Your goal is to rename the specified column to make it more explicit and descriptive while considering the other columns in the schema and the overall description of the table. Start by thinking for a bit and end your thought with this exact format (to ease parsing of your answer):

New column name: ...""",
    "description_combinator": 'You are an expert data scientist skilled in precise reasoning. Your task is to synthesize a single, concise description from several similar ones. Always choose the most specific term when multiple levels of abstraction are mentioned (e.g., if both "retail stores" and "businesses" are mentioned, only use "retail stores"). Do not include both general and specific terms together. Be concise, avoid repetition, and return only the refined description—no extra formatting or commentary.',
}


base_table_reducer_prompts = {
    "column_projection": """You are a helpful data scientist.

You will be provided with:
- A source table called SRC that is represented by its schema and some sample rows.
- A target schema that we will transform the source table into in a step-by-step manner.
- A column from the target schema as the current target column.

Your goal is to determine whether to select a certain column from SRC or extract information from certain column(s) from SRC to form the target column.

The output format for selecting a certain column:
{
    "operation": "select_column",
    "columns_involved": ["Restaurant ID"],
    "description": "Select SRC.Restaurant ID."
}

While for extracting information from certain column(s):
{
    "operation": "extract_column",
    "columns_involved": ["City", "ZIP Code"],
    "description": "Find the country based on SRC.City and SRC.`ZIP Code`."
}

Output your result strictly as a Python dictionary, without any extra formatting, explanations, or text. The output must be directly parseable as a Python dictionary.""",
    "extract_mode": """You are a data scientist working with structured tables.

You will be given:
- A table (schema and sample rows).
- A new column to generate.

Your job is to decide:
1. Should the values of the new column be extracted row-by-row using language reasoning?
2. Or, can the values be generated using a single Python function that processes the other column(s)?

Output one of:
- 'rowwise_extraction'
- 'python_code'

Output ONLY the keyword, without quotes, explanations, or formatting.""",
    "extract_col": """You are a helpful and knowledgeable data scientist.

You will be provided with:
- A table represented by its schema and rows.
- A column to be added to this table whose values depend on the other columns in the table.

Your goal is to determine the values of the new column for all rows. Ensure you consider **all provided columns together** rather than relying on a single column. For example, a city name may exist in multiple locations, but when paired with its corresponding province or county, ambiguity is reduced.

Output your result strictly as a Python list representing the new column values for all rows, without any extra formatting, explanations, or text. The output must be directly parseable as a Python list.""",
    "reduce_row": """You are a helpful and knowledgeable data scientist.

You will be provided with:
- A table, identified as target_table, represented by its schema and sample rows.
- A question over the table.

Your goal is to produce a SQL code (SQLite) containing predicates to reduce the rows of target_table. In other words, you need to eliminate irrelevant rows.

Output your result strictly as a SQL code (SQLite) without any extra formatting, explanations, or text. The output must be directly parseable as a SQL code.""",
}
