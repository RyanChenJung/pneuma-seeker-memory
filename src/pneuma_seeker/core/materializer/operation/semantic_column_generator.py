from pandas import DataFrame
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.utils.parser import augmented_literal_eval


class SemanticColumnGenerator:
    def __init__(self, llm: AbstractModel, batch_size: int = 10) -> None:
        self.llm = llm
        self.batch_size = max(1, batch_size)

    def generate_semantic_column(
        self,
        source_table: DataFrame,
        new_column_name: str,
        instruction: str,  # Explanation includes the possible values, i.e., the domain
    ) -> list[str]:
        """
        Produces a new semantically-induced column using the values from
        `source_table` based on the specified instruction.

        **Assumption**:
            - All columns in the source table are relevant to get values of the new column
              (meaning that the irrelevant columns have been removed)
            - The instruction already includes the expected values

        Parameters:
            source_table: The table to generate a new column for.
            new_column_name: The name of the new column.
            instruction: The instruction for the LLM to produce values for the new column.
        """
        if len(source_table) == 0:
            return []

        cached_values: dict[str, str] = {}
        formatted_values = self.__format_values(source_table)

        unique_values = list(dict.fromkeys(formatted_values))
        for i in range(0, len(unique_values), self.batch_size):
            batch = unique_values[i : i + self.batch_size]
            encoded_prompt = [
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content="You are given a list of values from a table, and your task is to generate a new column. Output the values directly as a Python list of strings/integers/floats WITHOUT any extra formatting or explanation.",
                ),
                LLMMessage(
                    role=Role.USER.value,
                    content=f"User-defined instruction to form the new column named {new_column_name}: {instruction}",
                ),
                LLMMessage(
                    role=Role.USER.value,
                    content=f"Values to transform: {batch}",
                ),
            ]

            raw_output = "".join(self.llm.chat(encoded_prompt)).strip()
            start = raw_output.find("[")
            end = raw_output.rfind("]")

            if start != -1 and end != -1 and start < end:
                list_str = raw_output[start:end+1]  # include the closing bracket
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

        return [cached_values[val] for val in formatted_values]

    def __format_values(self, table: DataFrame):
        formatted_values: list[str] = []
        for _, row in table.iterrows():
            row_values: list[str] = []
            for col_name in table.columns:
                row_values.append(f"{col_name}: {row[col_name]}")
            formatted_values.append("; ".join(row_values))
        return formatted_values
