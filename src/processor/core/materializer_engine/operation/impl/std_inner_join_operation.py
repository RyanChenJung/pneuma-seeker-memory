import pandas as pd

from pandas import DataFrame
from processor.core.materializer_engine.operation.abstract_operation import (
    AbstractOperation,
)


class StdInnerJoinOperation(AbstractOperation):
    def execute(self, left: DataFrame, right: DataFrame, join_key: str) -> DataFrame:
        return pd.merge(left, right, on=join_key)

    def describe(self) -> str:
        return """{"name": "Std Inner Join Operation", "Description": "Performs a relational inner join between two tables on a given join_key.", "Parameters": {"left": "ID of table from intermediate_results or retrieved_documents", "right": "ID of table from intermediate_results or retrieved_documents", "join_key": "The join key (type: str)"}}"""
