def get_operation_description():
    return """
- **Document Retriever**
    - Retrieves relevant tabular or textual data from our database based on natural-language prompts
    - Please observe the existing, previously retrieved data, before calling this tool, since this tool erases previously retrieved data (if any). In other words, use this tool only when new or updated data is needed
    - Args: {"prompt": "<retrieval query string, contextualized with columns of target schemas, not just using the the target schema IDs>"}
    - Example: {"prompt": "Get sales data for Q1 2025"}

- **Python Executor**
    - Executes Python code to transform data, the output can be a table (Pandas DataFrame), strings, list of strings, or whatever (you will be informed about the output, but make sure it is not too long, else just produce a table)
    - Common libraries like pandas, numpy are available (they are imported as pd and np, respectively), but to be safe, you can import it yourself in your code
    - Ensure your code uses Pandas DataFrame if you want to manipulate tables
    - Because we use Pandas and Numpy, you can transform the values of certain columns as well. For example, if the sqls expect "yyyy-mm-dd" format for a column, and the column values use "Month Date, Year" format, you can adjust it. Another example is a SQL query may expect uppercase values like "YES" instead of "yes", so adjust the values in this case.
    - All tables, whether retrieved or the ones you formed, are all available in the execution environment in a Python dictionary named "tables". You can simply access the tables you want using their IDs as keys (e.g., tables["../../data_src/environment/dataset/[table_name]"]), and you get them directly in Pandas DataFrame format.
    - Make sure to assign the result to 'result' variable
    - Args: {"code": "<Python code string>"}
    - Again, DO NOT try to read a table using, for instance, pd.read_csv. Use tables["<ID>"], and you get it directly in a Pandas DataFrame format.

- **SQL Executor**
    - Executes a SQL query on available tables to produce another table, NOT executing the `sqls`.
    - Supports standard SQL syntax
    - Assume all tables are available in the database; reference them using their IDs
    - Args: {"sql_query": "<SQL query string>"}
    - Example: {"sql_query": "SELECT * FROM table_1 WHERE date >= '2025-01-01'"}

- Standard Inner Join
    - Joins two tables using the standard inner join
    - Args: {{
        "left_table_id": "<ID of the left table>",
        "right_table_id": "<ID of the right table>",
        "join_key": "<Join key between left table and right table>"
    }}

- Union
    - Unions two or more tables with the same schemas together
    - Only use this if the tables indeed represent the exact same thing (note that some tables may have the same schemas but represent information for different time frame like years)
    - Args: {{
        "table_ids": "<IDs of the tables to union>",
    }}
""".strip()
