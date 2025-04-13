from processor.base_table_producer.base_table_producer import BaseTableProducer
from processor.schema_processor.schema_processor import SchemaProcessor
from processor.types.operation import Operation


class Processor:
    def __init__(self, ckp: str, api_key: str = ''):
        self.schema_processor = SchemaProcessor(ckp)
        self.planner = BaseTableProducer()
        self.api_key = api_key
    
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
