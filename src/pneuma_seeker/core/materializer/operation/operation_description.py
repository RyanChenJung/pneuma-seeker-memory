def get_operation_description():
    return """
- **Document Retriever**
    - Retrieves relevant tabular or textual data from our database based on natural-language prompts
    - Please observe the existing, previously retrieved data before calling this tool, since this tool erases previously retrieved data (if any). In other words, use this tool only when new or updated data is needed
    - Args: {"prompt": "<retrieval query string, contextualized with columns of target schemas, not just using the target schema IDs>"}
    - Example: {"prompt": "Get sales data for Q1 2025 with columns like order_id, product_name, and sale_amount"}

- **Table Enumerator**
    - Lists all available tables in the database whose names match a given regex pattern
    - This is useful when you retrieve one table (e.g., `topic_2020`) but suspect there are other related tables (`topic_2021`, `topic_2022`, etc.)
    - Args: { "pattern": "<regex pattern to match table names>" }
    - Example: { "pattern": "^sales_\\d{4}$" } will match all tables named like `sales_2020`, `sales_2021`, etc.

- **Python Executor**
    - Executes Python code to transform data, the output can be a table (Pandas DataFrame), strings, or list of strings
    - Common libraries like pandas and numpy are available (they are imported as pd and np, respectively), but to be safe, you can import it yourself in your code
    - Ensure your code uses Pandas DataFrame if you want to manipulate tables
    - Because we use Pandas and Numpy, you can transform the values of certain columns as well. For example, if the SQLs expect "yyyy-mm-dd" format for a column, and the column values use "Month Date, Year" format, you can adjust it. Another example is a SQL query may expect uppercase values like "YES" instead of "yes", so adjust the values in this case.
    - All tables, whether retrieved or ones you formed, are available in the execution environment in a Python dictionary named "tables". You can simply access the tables you want using their IDs as keys (e.g., tables["table_id"]), and you get them directly in Pandas DataFrame format.
    - Make sure to assign the result to a variable named 'result'
    - Args: {"code": "<Python code string>"}
    - Again, DO NOT try to read a table using, for instance, pd.read_csv. Use tables["<ID>"], and you get it directly in a Pandas DataFrame format.

- **Table Select**
    - Selects retrieved tables directly as the materialized forms of some tables in target schemas.
    - Args: {"<target schema ID>": {
                    {
                        "id": "<retrieved table ID>",
                        "columns": ["<The relevant columns from the selected retrieved table to form target schema ID>"]
                    }
                }
            }
    - This is useful, for example, if you retrieve a table A that directly matches a target schema B. In this case, you do not need to create SQL queries or Python code to select table A to represent target schema B; just provide a mapping as args {"B": "A"}.

- **SQL Executor**
    - Executes a SQL query on available tables to produce another table, NOT executing the `sqls`.
    - Supports standard SQL syntax
    - Assume all tables are available in the database; reference them using their IDs
    - Args: {"sql_query": "<SQL query string>"}
    - Example: {"sql_query": "SELECT * FROM table_1 WHERE date >= '2025-01-01'"}

- **Semantic Join**
    - Joins two tables by computing semantic similarity between specified columns using both embedding-based cosine similarity and string edit similarity.
    - This is useful when the user explicitly asks for it, or when two tables contain related entities that do not match exactly by key or text (e.g., "Intl Business Machines" vs. "IBM").  
      Even if both tables share a key column (e.g., "product_id"), the user may prefer semantic matching — for instance, comparing product descriptions between catalogs from different years to detect essentially identical products that were renumbered but now sold at different prices.
    - Args: {
        "left_table_id": "<ID of left table (must exist in retrieved or intermediate tables)>",
        "right_table_id": "<ID of right table (must exist in retrieved or intermediate tables)>",
        "relevant_left_cols": ["<list of columns from left table used for semantic comparison>"],
        "relevant_right_cols": ["<list of columns from right table used for semantic comparison>"],
        "joined_table_id": "<ID to store the resulting joined table>"
      }
    - Similarity is computed as a weighted combination of cosine similarity (from embeddings) and normalized Damerau-Levenshtein edit similarity. Default weight α=0.6, default join threshold=0.6.
    - The output is a new table where each row corresponds to a semantically matched pair, with a similarity_score column.
    - Example: {
        "left_table_id": "companies_2024",
        "right_table_id": "clients_2024",
        "relevant_left_cols": ["company_name", "headquarters_city"],
        "relevant_right_cols": ["client_name", "hq_location"],
        "joined_table_id": "company_client_matches"
      }

- **Semantic Column Generator**
    - Creates a new column for an existing table using an LLM, based on a natural-language instruction describing how to derive values.
    - Assumes:
        - All columns in the source table are relevant to the generation (irrelevant columns should be removed first).
        - The instruction already includes the expected domain or possible values of the new column.
    - The system automatically batches unique rows for efficiency and caches results to avoid redundant LLM calls.
    - Args: {
        "table_id": "<ID of the table to modify (must exist in retrieved or intermediate tables)>",
        "new_column_name": "<name of the column to add>",
        "instruction": "<instruction describing how to generate the new column values>"
      }
    - The new column is added directly to the specified table in-place.
    - Example: {
        "table_id": "products_2024",
        "new_column_name": "category",
        "instruction": "Classify each product into 'Electronics', 'Furniture', or 'Clothing' based on its description."
      }
""".strip()
