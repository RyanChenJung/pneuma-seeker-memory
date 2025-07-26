def get_operation_description():
    return """
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
    }}""".strip()
