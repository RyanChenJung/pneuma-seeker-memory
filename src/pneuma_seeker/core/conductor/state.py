from pandas import DataFrame

from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction


class InformationNeedState:
    """
    Represents user's information need as a set of target schemas and SQLs to be executed over them.
    For example, if the user needs to know about the work addresses of faculty members, the target schemas
    may be ["name", "work address"], where name represents the names of the members, and work address represents
    the corresponding work address of each of them. After materialized by Materializer Engine, the SQLs can be
    executed sequentially over the materialized tables, and the outcome is useful to answer user's needs.
    """

    def __init__(self) -> None:
        self.target_schemas: dict[str, DataFrame] = dict()
        self.is_target_schemas_materialized = False
        self.column_descriptions: dict[str, dict[str, str]] = dict()

        self.sqls: list[str] = []
        self.is_sql_executed = False

    def get_table_repr(self, table: DataFrame, table_id: str):
        table_repr = f"\nTable {table_id}:\ncol: {" | ".join(list(table.columns))}"
        if len(table) > 0:
            # Sample 5 rows to represent the table
            sample_rows = table.sample(min(5, len(table)), random_state=42)
            sample_row_idx = 1
            for _, data in sample_rows.iterrows():
                str_data = [str(i) for i in data]
                table_repr += f"\n- sample row {sample_row_idx}: {" | ".join(str_data)}"
                sample_row_idx += 1
        return table_repr

    def __str__(self) -> str:
        target_schemas_repr = ""
        for schema_id in self.target_schemas:
            table = self.target_schemas[schema_id]
            target_schemas_repr += (
                f"\n- Table {schema_id}:\ncol: {" | ".join(list(table.columns))}"
            )
            if len(table) > 0:
                # Sample 5 rows to represent the table
                sample_rows = table.sample(min(5, len(table)), random_state=42)
                sample_row_idx = 1
                for _, data in sample_rows.iterrows():
                    str_data = [str(i) for i in data]
                    target_schemas_repr += (
                        f"\n- sample row {sample_row_idx}: {" | ".join(str_data)}"
                    )
                    sample_row_idx += 1
            target_schemas_repr += "\n"
        return f"""Target schemas (Is materialized yet? {self.is_target_schemas_materialized}):
{target_schemas_repr.strip()}

Column descriptions of target schemas:
{self.column_descriptions}

SQLs to be run sequentially over the target schemas (Is executed yet? {self.is_sql_executed}):
{self.sqls}"""
