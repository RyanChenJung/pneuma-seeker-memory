import logging
from pandas import DataFrame
from processor.base_table_producer.base_table_producer import BaseTableProducer
from processor.llm.interface.model_factory import get_model
from processor.llm.interface.model_interface import ModelProtocol
from processor.schema_processor.schema_processor import SchemaProcessor
from processor.utils.dataframe_store import DataFrameStore
from processor.utils.logger import setup_logger
from processor.utils.operation import Operation
from processor.utils.system_context import SystemContext


class Processor:
    def __init__(self, model_name: str):
        # Initialize DataFrame Store
        df_store = DataFrameStore()

        # Initialize logger
        logger = setup_logger(
            name='processor_logger',
            log_file='logs/processor.log',
            level=logging.INFO,
            max_bytes=10_000_000,
            backup_count=5,
        )

        # Initialize LLM
        model_protocol = get_model(model_name)
        llm: ModelProtocol = model_protocol(model_name)

        # Keep track of shared resources as a global context
        self.context = SystemContext(
            df_store=df_store,
            logger=logger,
            llm=llm,
        )

        # Initialize core services
        self.schema_processor = SchemaProcessor()
        self.base_table_producer = BaseTableProducer()
    
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

    def get_enhanced_schema(self, tables: list[DataFrame]) -> list[str]:
        """
        Given a list of tables, produces enhanced schemas of the tables.

        ## Attributes
        - tables (list[DataFrame]): The tables whose schemas are to be enhanced by the Processor.

        ## Returns
        - list[str]: The enhanced schema of the tables.

        Produces a target schema given a question.
        """
        return self.schema_processor.get_enhanced_schema(tables)

    def get_transformation_plan(
        self, question: str, target_schema: str, available_table_schemas: list[str]
    ) -> list[Operation]:
        pass

    def execute_plan(plan: list[Operation]):
        pass

    def classify_operation(operation: Operation):
        pass
