from enum import Enum

from pneuma_seeker.shared.schemas.core.ir_system import AbstractDocument


class InformationNeedState:
    """
    Represents a user's information need as a pair (T,S), where T is a set of
    tables and S is a Python script to be executed over them. For example,
    if the user needs to know about the work addresses of faculty members, the target schemas
    may be ["name", "work address"], where name represents the names of the members, and work address represents
    the corresponding work address of each of them. After materialized Materializer, the Python code can be
    executed over the materialized tables, and the outcome is useful to answer the user's information need.
    """

    def __init__(self) -> None:
        self.T: dict[str, AbstractDocument] = dict()
        self.is_T_materialized = False
        self.column_descriptions: dict[str, dict[str, str]] = dict()

        self.S: str = ""
        self.is_S_executed = False

    def __str__(self) -> str:
        T_repr = ""
        for _, T_doc in self.T.items():
            T_repr += f"\n- {T_doc}"
        return f"""Target tables (T; is materialized yet? {self.is_T_materialized}):
{T_repr.strip()}

Column descriptions of T:
{self.column_descriptions}

Script (S) to be run over T (Is executed yet? {self.is_S_executed}):
{self.S}"""

    def get_current_state_instance(self):
        MAX_ROWS = 10

        def serialize_dataframe(df):
            # Convert DataFrame to a JSON-safe list of dicts
            return (
                df.head(MAX_ROWS)
                .map(lambda x: x.isoformat() if hasattr(x, "isoformat") else x)
                .to_dict(orient="records")
            )

        return {
            "T": {
                table_id: serialize_dataframe(table_doc.content)
                for table_id, table_doc in self.T.items()
            },
            "is_T_materialized": self.is_T_materialized,
            "column_descriptions": self.column_descriptions,
            "S": self.S,
            "is_S_executed": self.is_S_executed,
        }



class UserConductorInteraction:
    """
    Keeps track of pairs of user input-Conductor (final) response for the input
    """

    def __init__(self, user_input: str, llm_response: str) -> None:
        self.user_input = user_input
        self.llm_response = llm_response

    def __str__(self) -> str:
        return f"""{{"user input": {self.user_input}, "llm response": {self.llm_response}}}"""