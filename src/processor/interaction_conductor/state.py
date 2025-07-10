class ICState:
    def __init__(self) -> None:
        """
        Initializes the session state with empty SQLs and target schemas.
        """
        self.sqls: list[str] = []
        self.target_schemas: list[str] = []
    
    def set_state(self, new_sqls: list[str], new_target_schemas: list[str]) -> None:
        """
        Sets new values for SQLs and Target Schemas
        """
        self.sqls = new_sqls
        self.target_schemas = new_target_schemas

    def reset(self) -> None:
        """
        Sets the values of both SQLs and Target Schemas to be empty.
        """
        self.sqls = []
        self.target_schemas = []

    def get_state(self) -> dict[str, list[str]]:
        """
        Returns the current SQLs and Target Schemas.
        """
        return {
            "sqls": self.sqls,
            "target_schemas": self.target_schemas,
        }
