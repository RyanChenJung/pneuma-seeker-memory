def get_tool_description():
    return """
- **Document Retriever**
    - Retrieves relevant tabular or textual data from our database based on natural-language prompts
    - Use when new or updated data is needed, but remember that calling this tool erases previously retrieved data (if any)
    - Args: {"prompt": "<retrieval query string>"}
    - Example: {"prompt": "Get sales data for Q1 2025"}

- **Python Executor**
    - Executes Python code to transform data, the output can be a table (Pandas DataFrame), strings, list of strings, or whatever (you will be informed about the output, but make sure it is not too long, else just produce a table)
    - Ensure your code uses Pandas DataFrame if you want to manipulate tables
    - Common libraries like pandas, numpy are available (they are imported as pd and np, respectively), but to be safe, you can import it yourself in your code
    - Assume all tables can be accessed through 'tables' dictionary with table IDs as keys
    - Make sure to assign the result to 'result' variable
    - Args: {"code": "<Python code string>"}
    - Examples:
      ```python
      result = tables["table_1"].describe()
      result = tables["sales_data"].groupby('category').sum()
      ```

- **SQL Executor**
    - Executes a SQL query on available tables
    - Supports standard SQL syntax
    - Assume all tables are available in the database; reference them using their IDs
    - Args: {"sql_query": "<SQL query string>"}
    - Example: {"sql_query": "SELECT * FROM table_1 WHERE date >= '2025-01-01'"}
""".strip()