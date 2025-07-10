from typing import Type
from processor.materializer_engine.operation.abstract_operation import AbstractOperation
from processor.materializer_engine.operation.impl.join import Join
from processor.materializer_engine.oepration.impl.union import Union


class OperationType(Enum):
    JOIN = 'Join'
    UNION = 'Union'


def get_operation(operation_type: OperationType) -> Type[AbstractOperation]:
    if operation_type == OperationType.JOIN:
        return Join
    elif operation_type == OperationType.UNION:
        return Union
