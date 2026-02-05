from typing import Any
from pandas import DataFrame

from pneuma_seeker.shared.schemas.core.action import ActionNames
from pneuma_seeker.services.core.actions.interfaces.abstract_action import Action
from pneuma_seeker.services.core.actions.interfaces.applicable import Applicable


class TableProjection(Action, Applicable):
    def get_name(self) -> str:
        return ActionNames.TABLE_PROJECTION.value

    def get_description(self) -> str:
        return "Select retrieved tables to be "

    def get_input_schema(self) -> dict[str, str]:
        return {}

    def get_notes(self) -> str:
        return ""

    def apply(self, input: dict[str, Any]) -> DataFrame:
        table = input.get("table")
        relevant_columns = input.get("relevant_columns")

        if not isinstance(table, DataFrame):
            raise ValueError("Input 'table' must be a pandas DataFrame.")
        if not isinstance(relevant_columns, list) or not all(
            isinstance(col, str) for col in relevant_columns
        ):
            raise ValueError("Input 'relevant_columns' must be a list of strings.")

        return table[relevant_columns]
