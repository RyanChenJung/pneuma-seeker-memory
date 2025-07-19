from enum import Enum
from processor.core.materializer_engine.operation.abstract_operation import (
    AbstractOperation,
)
from processor.core.materializer_engine.operation.impl.std_inner_join_operation import (
    StdInnerJoinOperation,
)
from processor.core.materializer_engine.operation.impl.union_operation import (
    UnionOperation,
)


class OperationType(Enum):
    STD_INNER_JOIN_OPERATION = "Std Inner Join Operation"
    UNION_OPERATION = "Union Operation"


class OperationFactory:
    def __init__(self):
        self.std_inner_join_operation = StdInnerJoinOperation()
        self.union_operation = UnionOperation()

    def available_operations(self):
        return [
            self.std_inner_join_operation,
            self.union_operation,
        ]

    def get_operation(self, operation_type: str) -> AbstractOperation:
        if operation_type == OperationType.STD_INNER_JOIN_OPERATION.value:
            return self.std_inner_join_operation
        elif operation_type == OperationType.UNION_OPERATION.value:
            return self.union_operation
        else:
            raise ValueError(f"Unrecognized operation: {operation_type}")
