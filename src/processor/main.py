import logging
from typing import Any

from pandas import DataFrame

from processor.base_table_producer.base_table_producer import BaseTableProducer
from processor.conductor_state import ConductorState
from processor.llm.interface.model_factory import get_model
from processor.schema_processor.schema_processor import SchemaProcessor
from processor.table_reader.table_reader_factory import get_table_reader
from processor.table_store.table_store_factory import get_table_store
from processor.utils.logger import setup_logger


class Processor:
    def __init__(self, model_name: str, table_type: Any = DataFrame):
        # Initialize Table Store
        table_store_impl = get_table_store(impl=table_type)
        table_store = table_store_impl()

        # Initialize Table Formatter
        table_formatter_impl = get_table_reader(table_type=table_type)
        table_formatter = table_formatter_impl()

        # Initialize logger
        logger = setup_logger(
            name="processor_logger",
            log_file="logs/processor.log",
            level=logging.INFO,
            max_bytes=10_000_000,
            backup_count=5,
        )

        # Initialize LLM
        model_impl = get_model(model_name=model_name)
        llm = model_impl(model_name=model_name)

        # Keep track of shared resources as a global context
        self.ctx = ConductorState(
            table_store=table_store,
            table_reader=table_formatter,
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
        return self.schema_processor.get_target_schema(
            ctx=self.ctx,
            question=question,
        )

    def get_table_descriptions(
        self,
        schema: str,
        num_sampling=3,
        num_sampled_rows=3,
    ):
        """
        Describes all tables within a schema.

        - num_sampling (int): Number of different samples to consider.
        - num_sampled_rows (int): Number of rows to sample for each sampling process.
        - redescribe (bool): Redescribe tables that have already been described.
        """
        return self.schema_processor.get_table_descriptions(
            ctx=self.ctx,
            schema=schema,
            num_sampling=num_sampling,
            num_sampled_rows=num_sampled_rows,
        )

    def get_enhanced_schemas(
        self, schema: str, table_descriptions: dict[str, str], num_rows=3
    ) -> dict[str, list[str]]:
        """
        Given a list of tables, produces enhanced schemas of the tables.

        ## Attributes
        - tables (list[DataFrame]): The tables whose schemas are to be enhanced by the Processor.

        ## Returns
        - list[str]: The enhanced schema of the tables.

        Produces a target schema given a question.
        """
        return self.schema_processor.get_enhanced_schemas(
            ctx=self.ctx,
            schema=schema,
            table_descriptions=table_descriptions,
            num_rows=num_rows,
        )
