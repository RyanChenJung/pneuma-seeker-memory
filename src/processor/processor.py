from processor.planner.planner import Planner
from processor.schema_generator.schema_generator import SchemaGenerator
from processor.types.operation import Operation


class Processor:
    def __init__(self):
        self.schema_generator = SchemaGenerator()
        self.planner = Planner()

    def get_target_schema(self, question: str):
        """
        Given a question over tables, retrieves the target schema of a table that
        can answer the question.

        ## Attributes
        - question (str): The question over tables.

        ## Returns
        - str: The target schema for the question.
        """
        return self.schema_generator.get_target_schema(question)

    def get_transformation_plan(
        self, question: str, target_schema: str, available_table_schemas: list[str]
    ) -> list[Operation]:
        pass

    def execute_plan(plan: list[Operation]):
        pass

    def classify_operation(operation: Operation):
        pass
