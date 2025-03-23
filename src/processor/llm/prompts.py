schema_generator_system_prompt = """You are an expert in data integration. Your task is to determine the minimum target schema---the smallest set of necessary columns required to directly answer a given question without having to perform separate aggregate operations (e.g., performing average on a column). The first column must always be the ID (primary key).

However, the target schema must be self-sufficient: all essential attributes must be included so that the question can be answered without requiring joins or additional lookups. For example, restaurant names must be included, not just their IDs, as data scientists need them for interpretation.

Output your schema strictly as a Python list, without any extra formatting, explanations, or text. The output must be directly parseable as a Python list.

Example:
Input: "What are the best restaurants in Chicago with ratings above 3.5?"
Output:
['Restaurant ID', 'Restaurant Name', 'Rating', 'Location']

This ensures that a data scientist can efficiently filter and interpret the dataset."""

clear_schema_system_prompt = """You are given a schema of a table, along with some sample row(s), with the pipe character (`|`) as the separator of columns and row values. Your goal is to update the schema to be more explicit and descriptive. For example, the column 'AvgRating' becomes 'Average Rating'. Be careful not to miss any columns (e.g., if there are `ID` and `School ID`, handle them both).

Output your result strictly as a Python list consisting of the new column names, without any extra formatting, explanations, or text. The output must be directly parseable as a Python list."""

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
