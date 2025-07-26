import pandas as pd


def std_inner_join(
    left_table_id: str,
    right_table_id: str,
    tables: dict[str, pd.DataFrame],
    join_key: str,
) -> pd.DataFrame:
    left_table = tables[left_table_id]
    right_table = tables[right_table_id]
    return pd.merge(left_table, right_table, on=join_key)
