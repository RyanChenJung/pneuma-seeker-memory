from pneuma_seeker.core.ir_system.data_model import AbstractDocument


class InformationNeedState:
    """
    Represents a user's information need as a pair (T,Q), where T is a set of
    tables and Q is a sequene of SQL queries to be executed over them. For example,
    if the user needs to know about the work addresses of faculty members, the target schemas
    may be ["name", "work address"], where name represents the names of the members, and work address represents
    the corresponding work address of each of them. After materialized by Materializer Engine, the SQLs can be
    executed sequentially over the materialized tables, and the outcome is useful to answer user's needs.
    """

    def __init__(self) -> None:
        self.target_schemas: dict[str, AbstractDocument] = dict()
        self.is_target_schemas_materialized = False
        self.column_descriptions: dict[str, dict[str, str]] = dict()

        self.sqls: list[str] = []
        self.is_sql_executed = False

    def __str__(self) -> str:
        T_repr = ""
        for _, T_doc in self.target_schemas.items():
            T_repr += f"\n- {T_doc}"
        return f"""Target schemas (Is materialized yet? {self.is_target_schemas_materialized}):
{T_repr.strip()}

Column descriptions of target schemas:
{self.column_descriptions}

SQLs to be run sequentially over the target schemas (Is executed yet? {self.is_sql_executed}):
{self.sqls}"""

    def get_current_state_instance(self):
        MAX_ROWS = 10
        return {
            "T": {
                table_id: table_doc.content.head(MAX_ROWS).to_dict(orient="records")
                for table_id, table_doc in self.target_schemas.items()
            },
            "is_T_materialized": self.is_target_schemas_materialized,
            "column_descriptions": self.column_descriptions,
            "Q": self.sqls,
            "is_Q_executed": self.is_sql_executed,
        }
