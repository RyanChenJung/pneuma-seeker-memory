def get_operation_description(enable_web_search = False):
    return """
- **pneuma_retriever**
    - Retrieves relevant tables from the internal database based on natural-language prompts.
    - Does not affect user-provided external tables. However, previously retrieved internal tables are replaced each time this tool is called.
    - Args: {"prompt": "<retrieval query string, contextualized with columns of the target tables (T), not just using the target table IDs>"}
    - Example: {"prompt": "Get sales data for Q1 2025 with columns like order_id, product_name, and sale_amount"}

- **table_enumerator**
    - **Precondition — MUST NOT be called unless there is at least one internal table already retrieved.**
    - The `pattern` argument **must be derived from the names of existing internal tables** (or obvious common tokens in them).
    - Lists other available internal tables in the database whose names match a given regex pattern.
    - This is useful when you retrieve one table (e.g., `topic_2020`) but suspect there are other related tables (`topic_2021`, `topic_2022`, etc.)
    - Does not affect user-provided external data.
    - Args: {"pattern": "<regex pattern to match table names>"}
    - Example: {"pattern": "^sales_\\d{4}$"} will match all tables named like `sales_2020`, `sales_2021`, etc.

- **python_executor**
    - Executes Python code to transform and/or combine data. Output can be a new table (Pandas DataFrame), string, or list of strings.
    - All tables — whether internal, external, or intermediate — are available via `tables["<ID>"]` (Pandas DataFrame).
    - Never use `pd.read_csv`; tables are already provided in memory.
    - Pandas, NumPy, and SciPy are available for data manipulation (remember to add relevant import statements in the code if you need them).
    - Common libraries like pandas and numpy are available for data manipulation (they are imported as pd and np, respectively), but to be safe, you can import it yourself in your code
    - You can perform many things, including transforming the values of certain columns. For example, if the SQLs expect "yyyy-mm-dd" format for a column, and the column values use "Month Date, Year" format, you can adjust it. Another example is a SQL query may expect uppercase values like "YES" instead of "yes", so adjust the values as well in this case.
    - Make sure to assign the result to a variable named 'result'
    - Args: {"code": "<Python code string>"}

- **table_select**
    - Directly maps an existing table (internal, external, or intermediate) to a target table (or a subset of its columns).
    - Args: {"<target_table_id>": {
                    {
                        "id": "<source_table_id>",
                        "columns": ["<subset of columns from source table to use>"]
                    }
                }
            }
    - Example use case: If table A has columns that match some columns of target table B, you can select it directly instead of creating SQL queries or Python code.

- **sql_executor**
    - Executes SQL queries on available tables (internal, external, or intermediate).
    - Supports standard SQL syntax
    - Args: {"sql_query": "<SQL query string>"}
    - Example: {"sql_query": "SELECT * FROM table_1 WHERE date >= '2025-01-01'"}

- **semantic_join**
    - Joins two tables (internal, external, or intermediate) by computing semantic similarity between specified columns.
    - Similarity uses a weighted combination of embedding cosine similarity and normalized Damerau-Levenshtein edit similarity.
    - Produces a new joined table containing matched rows and a similarity_score column.
    - Use case: when the user explicitly asks for it, or when two tables contain related entities that do not match exactly by key or text (e.g., "Intl Business Machines" vs. "IBM").  
      Even if both tables share a key column (e.g., "product_id"), the user may prefer semantic matching — for instance, comparing product descriptions between catalogs from different years to detect essentially identical products that were renumbered but now sold at different prices.
    - Args: {
        "left_table_id": "<ID of left table (must exist in retrieved or intermediate tables)>",
        "right_table_id": "<ID of right table (must exist in retrieved or intermediate tables)>",
        "relevant_left_cols": ["<list of columns from left table used for semantic comparison>"],
        "relevant_right_cols": ["<list of columns from right table used for semantic comparison>"],
        "joined_table_id": "<ID to store the resulting joined table>"
      }
    - Example: {
        "left_table_id": "companies_2024",
        "right_table_id": "clients_2024",
        "relevant_left_cols": ["company_name", "headquarters_city"],
        "relevant_right_cols": ["client_name", "hq_location"],
        "joined_table_id": "company_client_matches"
      }

- **semantic_column_generator**
    - Adds a new column to an *intermediate* table using an LLM.
    - The column is derived from specified `relevant_columns` only — no other columns are used.
    - External and internal tables should first be transformed into intermediate tables if new columns are needed, because retrieved internal tables can be replaced.
    - The system automatically batches unique rows for efficiency and caches results to avoid redundant LLM calls.
    - Args: {
        "table_id": "<intermediate_table_id>",
        "new_column_name": "<column to add>",
        "relevant_columns": ["<list of source columns for generation>"],
        "instruction": "<instruction describing how to generate the new column values>"
      }
    - Example: {
        "table_id": "products_2024",
        "new_column_name": "category",
        "relevant_columns": ["product_name", "description"],
        "instruction": "Classify each product into 'Electronics', 'Furniture', or 'Clothing'."
      }
""".strip() + (get_web_search_description() if enable_web_search else "")

def get_web_search_description():
    """Gets the optional web search description for the Materializer."""
    return """\n- **web_search**
    - Retrieves information from the web to assist in filling tables when internal and external data are insufficient.
    - Args: {"prompt": "<query describing what data to retrieve or clarify>"}
    - Usage notes:
        - Use web_search only when no reliable internal/external source exists for the required column(s).
        - Avoid repetitive or redundant queries."""
