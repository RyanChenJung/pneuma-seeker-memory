from typing import TypedDict


class ICStateStructure(TypedDict):
    sqls: list[str]
    target_schemas: dict[str, dict[str, str]]


class ICState:
    def __init__(self) -> None:
        """
        Initializes the session state with empty SQLs and target schemas.
        """
        self.sqls: list[str] = []
        self.target_schemas: dict[str, dict[str, str]] = dict()

    def set_state(
        self, new_sqls: list[str], new_target_schemas: dict[str, dict[str, str]]
    ) -> None:
        """
        Sets new values for SQLs and Target Schemas
        """
        self.sqls = new_sqls
        self.target_schemas = new_target_schemas

    def get_state(self) -> ICStateStructure:
        """
        Returns the current SQLs and Target Schemas.
        """
        return ICStateStructure(
            sqls=self.sqls,
            target_schemas=self.target_schemas,
        )
