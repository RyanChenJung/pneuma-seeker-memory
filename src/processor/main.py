from processor.base_table_producer.base_table_producer import BaseTableProducer
from processor.llm.interface.model_factory import get_model
from processor.llm.interface.model_interface import ModelProtocol
from processor.schema_processor.schema_processor import SchemaProcessor
from processor.types.operation import Operation


class Processor:
    def __init__(self, model_name: str):
        model_protocol = get_model(model_name)
        self.model: ModelProtocol = model_protocol(model_name)
        self.schema_processor = SchemaProcessor(self.model)
        self.base_table_producer = BaseTableProducer(self.model)

    def get_enhanced_schema(self, tables):
        return self.schema_processor.get_enhanced_schema(tables)

    def get_target_schema(self, question: str):
        """
        Given a question over tables, retrieves the target schema of a table that
        can answer the question.

        ## Attributes
        - question (str): The question over tables.

        ## Returns
        - str: The target schema for the question.
        """
        return self.schema_processor.get_target_schema(question)

    def get_transformation_plan(
        self, question: str, target_schema: str, available_table_schemas: list[str]
    ) -> list[Operation]:
        pass

    def execute_plan(plan: list[Operation]):
        pass

    def classify_operation(operation: Operation):
        pass
