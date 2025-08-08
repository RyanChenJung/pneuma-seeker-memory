import pandas as pd


def union(
    tables: dict[str, pd.DataFrame],
    table_ids: list[str],
) -> pd.DataFrame:
    operands = [table for table_id, table in tables.items() if table_id in table_ids]
    first_schema = list(operands[0].columns)
    for df in operands[1:]:
        if list(df.columns) != first_schema:
            raise ValueError("All tables must have the same columns to union.")

    return pd.concat(operands, ignore_index=True)
