from typing import Any
from pandas import DataFrame

from pneuma_seeker.shared.schemas.core.action import ActionNames
from pneuma_seeker.services.core.actions.interfaces.abstract_action import Action
from pneuma_seeker.services.core.actions.interfaces.applicable import Applicable
from pneuma_seeker.shared.parser import augmented_literal_eval
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.role import Role


class SemanticColumnGeneration(Action, Applicable):
    def get_name(self) -> str:
        return ActionNames.SEMANTIC_COLUMN_GENERATION.value

    def get_description(self) -> str:
        return "Generates a new column for a given table based on semantic understanding, outputting the updated table."

    def get_input_schema(self) -> dict[str, str]:
        return {
            "table": "The table to which the new column will be added.",
            "column_name": "Name of the new column to be generated.",
            "description": "Description of the content and purpose of the new column.",
        }

    def get_notes(self) -> str:
        return (
            "This action uses semantic analysis to generate a new column in the specified table. "
            "Ensure that the table exists and that the description accurately reflects the intended content of the new column."
        )

    def apply(self, input: dict[str, Any]) -> DataFrame:
        table = input.get("table")
        column_name = input.get("column_name")
        description = input.get("description")

        if not isinstance(table, DataFrame):
            raise ValueError("Invalid input type. 'table' must be a pandas DataFrame.")

        if not isinstance(column_name, str) or not isinstance(description, str):
            raise ValueError(
                "Invalid input types. 'column_name' and 'description' must be strings."
            )
        
        table = table.copy()  # to avoid modifying the original DataFrame

        if len(table) == 0:
            return table

        cached_values: dict[str, str] = {}
        formatted_values = self.__format_values(table)

        unique_values = list(dict.fromkeys(formatted_values))
        for i in range(
            0,
            len(unique_values),
            self.config.SEMANTIC_COL_GEN_VALUE_GENERATION_BATCH_SIZE,
        ):
            batch = unique_values[
                i : i + self.config.SEMANTIC_COL_GEN_VALUE_GENERATION_BATCH_SIZE
            ]
            encoded_prompt = [
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content="You are given a list of values from a table, and your task is to generate a new column. Output the values directly as a Python list of strings/integers/floats WITHOUT any extra formatting or explanation.",
                ),
                LLMMessage(
                    role=Role.USER.value,
                    content=f"User-defined instruction to form the new column named {column_name}: {description}",
                ),
                LLMMessage(
                    role=Role.USER.value,
                    content=f"Values to transform: {batch}",
                ),
            ]

            raw_output = "".join(self.language_model_api.chat(encoded_prompt)).strip()
            start = raw_output.find("[")
            end = raw_output.rfind("]")

            if start != -1 and end != -1 and start < end:
                list_str = raw_output[start : end + 1]  # include the closing bracket
                try:
                    transformed_values = augmented_literal_eval(list_str)
                except (SyntaxError, ValueError):
                    # fallback if the content is not valid Python literal
                    transformed_values = []
            else:
                # no valid list delimiters found
                transformed_values = []

            for val_idx, value in enumerate(transformed_values):
                cached_values[batch[val_idx]] = value

        new_column_values = [cached_values[val] for val in formatted_values]
        table[column_name] = new_column_values
        return table

    def __format_values(self, table: DataFrame):
        formatted_values: list[str] = []
        for _, row in table.iterrows():
            row_values: list[str] = []
            for col_name in table.columns:
                row_values.append(f"{col_name}: {row[col_name]}")
            formatted_values.append("; ".join(row_values))
        return formatted_values
