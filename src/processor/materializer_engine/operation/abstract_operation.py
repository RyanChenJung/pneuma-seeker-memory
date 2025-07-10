from enum import Enum


class OperationType(Enum):
    JOIN = 'Join'
    UNION = 'Union'


class AbstractOperation:
    def execute(self, **kwargs):
        """
        Executes the operation on the arguments (operands).
        """
        pass
