import pandas as pd

from pandas import DataFrame
from processor.core.materializer_engine.operation.abstract_operation import (
    AbstractOperation,
)


class UnionOperation(AbstractOperation):
    def execute(self, *operands: DataFrame, **kwargs) -> DataFrame:
        if not operands:
            raise ValueError("No operands provided for union.")

        first_schema = list(operands[0].columns)
        for df in operands[1:]:
            if list(df.columns) != first_schema:
                raise ValueError("All tables must have the same columns to union.")

        return pd.concat(operands, ignore_index=True)

    def describe(self) -> str:
        return """{"name": "Union Operation", "Description": "Performs a union between two or more tables with the same columns (vertical stacking).", "Parameters": {"inputs": "Array of table IDs from intermediate_results or retrieved_documents"}}"""
