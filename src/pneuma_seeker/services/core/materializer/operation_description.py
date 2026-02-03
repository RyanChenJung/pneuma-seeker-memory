from pneuma_seeker.services.core.actions.action_names import ActionNames


def get_operation_description(
    enable_web_search=False,
    enable_web_crawl=False,
    enable_assumption_check=False,
) -> str:
    return (
        f"""
- **{ActionNames.TABLE_RETRIEVE.value}**
    - Retrieves relevant tables from the internal database based on natural-language prompts.
    - Does not affect user-provided external tables. However, previously retrieved internal tables are replaced each time this tool is called.
    - Args: {{"prompt": "<retrieval query string, contextualized with columns of the target tables (T), not just using the target table IDs>"}}
    - Example: {{"prompt": "Get sales data for Q1 2025 with columns like order_id, product_name, and sale_amount"}}

- **{ActionNames.TABLE_ENUMERATION.value}**
    - **Precondition — MUST NOT be called unless there is at least one internal table already retrieved.**
    - The `pattern` argument **must be derived from the names of existing internal tables** (or obvious common tokens in them).
    - Lists other available internal tables in the database whose names match a given regex pattern.
    - This is useful when you retrieve one table (e.g., `topic_2020`) but suspect there are other related tables (`topic_2021`, `topic_2022`, etc.)
    - Does not affect user-provided external data.
    - Args: {{"pattern": "<regex pattern to match table names>"}}
    - Example: {{"pattern": "^sales_\\d{4}$"}} will match all tables named like `sales_2020`, `sales_2021`, etc.

- **{ActionNames.PYTHON_EXECUTOR.value}**
    - Executes Python code to transform and/or combine data. Output is a **SINGLE** new table (Pandas DataFrame).
    - All tables — whether internal, external, or intermediate — are available via `tables["<ID>"]` (Pandas DataFrame).
    - Never use `pd.read_csv`; tables are already provided in memory.
    - Pandas, NumPy, and SciPy are available for data manipulation (remember to add relevant import statements in the code if you need them).
    - You can perform many things, including transforming the values of certain columns. For example, if the SQLs expect "yyyy-mm-dd" format for a column, and the column values use "Month Date, Year" format, you can adjust it. Another example is a SQL query may expect uppercase values like "YES" instead of "yes", so adjust the values as well in this case.
    - Make sure to assign the result, which must be a **SINGLE** pandas DataFrame, to a variable named 'result'
    - Args: {{"code": "<Python code string>"}}
{get_assumption_check_description() if enable_assumption_check else ""}

- **{ActionNames.TABLE_PROJECTION.value}**
    - Directly maps an existing table (internal, external, or intermediate) to a target table (or a subset of its columns).
    - Args: {{"<target_table_id>": {{
                    {{
                        "id": "<source_table_id>",
                        "columns": ["<subset of columns from source table to use>"]
                    }}
                }}
            }}
    - Example use case: If table A has columns that match some columns of target table B, you can select it directly instead of creating SQL queries or Python code.

- **{ActionNames.SQL_EXECUTOR.value}**
    - Executes SQL queries on available tables (internal, external, or intermediate).
    - Supports standard SQL syntax
    - Args: {{"sql_query": "<SQL query string>"}}
    - Example: {{"sql_query": "SELECT * FROM table_1 WHERE date >= '2025-01-01'"}}

- **{ActionNames.SEMANTIC_JOIN.value}**
    - Joins two tables (internal, external, or intermediate) by computing semantic similarity between specified columns.
    - Similarity uses a weighted combination of embedding cosine similarity and normalized Damerau-Levenshtein edit similarity.
    - Produces a new joined table containing matched rows and a similarity_score column.
    - Use case: when the user explicitly asks for it, or when two tables contain related entities that do not match exactly by key or text (e.g., "Intl Business Machines" vs. "IBM").
      Even if both tables share a key column (e.g., "product_id"), the user may prefer semantic matching — for instance, comparing product descriptions between catalogs from different years to detect essentially identical products that were renumbered but now sold at different prices.
    - Args: {{
        "left_table_id": "<ID of left table (must exist in retrieved or intermediate tables)>",
        "right_table_id": "<ID of right table (must exist in retrieved or intermediate tables)>",
        "relevant_left_cols": ["<list of columns from left table used for semantic comparison>"],
        "relevant_right_cols": ["<list of columns from right table used for semantic comparison>"],
        "joined_table_id": "<ID to store the resulting joined table>"
      }}
    - Example: {{
        "left_table_id": "companies_2024",
        "right_table_id": "clients_2024",
        "relevant_left_cols": ["company_name", "headquarters_city"],
        "relevant_right_cols": ["client_name", "hq_location"],
        "joined_table_id": "company_client_matches"
      }}

- **{ActionNames.SEMANTIC_COLUMN_GENERATION.value}**
    - Adds a new column to an *intermediate* table using an LLM.
    - The column is derived from specified `relevant_columns` only — no other columns are used.
    - External and internal tables should first be transformed into intermediate tables if new columns are needed, because retrieved internal tables can be replaced.
    - Args: {{
        "table_id": "<intermediate_table_id>",
        "new_column_name": "<column to add>",
        "relevant_columns": ["<list of source columns for generation>"],
        "instruction": "<instruction describing how to generate the new column values>"
      }}
    - Example: {{
        "table_id": "products_2024",
        "new_column_name": "category",
        "relevant_columns": ["product_name", "description"],
        "instruction": "Classify each product into 'Electronics', 'Furniture', or 'Clothing'."
      }}
""".strip()
        + (get_web_search_description() if enable_web_search else "")
        + (get_web_crawl_description() if enable_web_crawl else "")
    )


def get_assumption_check_description():
    return f"""\n- **{ActionNames.ASSUMPTION_CHECK.value}**
    - Executes Python code to explore, inspect, or test assumptions about the data.
    - This tool is used ONLY to gather evidence, perform sanity checks, or confirm suspicions. There are no side effects.
    - It MUST NOT be used to construct final outputs or pipeline tables.
    - All tables are available via `tables[\"<ID>\"]` as Pandas DataFrames.
    - The code must assign a SINGLE pandas DataFrame to a variable named `result`.
    - Typical uses:
        - Checking whether a condition holds
        - Inspecting column value distributions or edge cases
        - Counting, filtering, sampling, or summarizing to confirm a belief
    - The output is considered *ephemeral* and used only for reasoning.
    - Args: {{\"code\": \"<Python code string>\"}}"""


def get_web_search_description():
    """Gets the optional web search description for the Materializer."""
    return f"""\n- **{ActionNames.WEB_SEARCH.value}**
    - Retrieves information from the web to assist in filling tables when internal and external data are insufficient.
    - Args: {{"prompt": "<query describing what data to retrieve or clarify>"}}
    - Usage notes:
        - Use web_search only when no reliable internal/external source exists for the required column(s).
        - Avoid repetitive or redundant queries."""


def get_web_crawl_description():
    """Gets the optional web crawl description for the Materializer."""
    return f"""\n- **{ActionNames.WEB_CRAWL.value}**
    - Crawls a specified web page to extract textual content for table materialization.
    - Args: {{"url": "<URL of the web page to crawl>"}}
    - Usage notes:
        - Use this when the user specifically requests information from a particular URL.
        - The crawler respects robots.txt and will not fetch disallowed paths.
        - Returned content is raw extracted text from the page (no summarization)."""
