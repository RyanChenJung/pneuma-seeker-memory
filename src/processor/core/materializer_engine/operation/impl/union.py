from processor.core.materializer_engine.operation.abstract_operation import AbstractOperation


class Union(AbstractOperation):
    def execute(self, **kwargs):
        return super().execute(**kwargs)
