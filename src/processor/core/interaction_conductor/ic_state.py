from pandas import DataFrame


class ICState:
    def __init__(self) -> None:
        """
        Initializes the session state with empty SQLs and target schemas.
        """
        self.sqls: list[str] = []
        self.target_schemas: dict[str, DataFrame] = dict()

    def set_state(self, new_sqls: list[str], new_target_schemas: dict[str, DataFrame]) -> None:
        """
        Sets new values for SQLs and Target Schemas
        """
        self.sqls = new_sqls
        self.target_schemas = new_target_schemas

    def get_state(self) -> dict[str, list[str] | dict[str, DataFrame]]:
        """
        Returns the current SQLs and Target Schemas.
        """
        return {
            "sqls": self.sqls,
            "target_schemas": self.target_schemas,
        }
