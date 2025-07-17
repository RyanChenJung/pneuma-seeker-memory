from enum import Enum
from typing import Type
from processor.core.materializer_engine.operation.abstract_operation import (
    AbstractOperation,
)
from processor.core.materializer_engine.operation.impl.join import Join
from processor.core.materializer_engine.operation.impl.union import Union


class OperationType(Enum):
    JOIN = "Join"
    UNION = "Union"


class OperationFactory:
    def __init__(self):
        self.join = Join()
        self.union = Union()

    def get_operation(self, operation_type: OperationType) -> Type[AbstractOperation]:
        if operation_type == OperationType.JOIN:
            return self.join
        elif operation_type == OperationType.UNION:
            return self.union
