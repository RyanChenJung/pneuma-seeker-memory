import logging
from typing import Any

from pandas import DataFrame
from processor.base_table_reducer.base_table_reducer import BaseTableReducer

from processor.base_table_producer.base_table_producer import BaseTableProducer
from processor.computation_graph import ComputationGraph, Node
from processor.conductor_state import ConductorState
from processor.models.interface.model_factory import get_embed_model, get_llm
from processor.schema_processor.schema_processor import SchemaProcessor
from processor.table.store.table_store_factory import get_table_store
from processor.utils.logger import setup_logger


class Processor:
    def __init__(self, llm_path: str, embed_path: str, table_type: Any = DataFrame):
        # Initialize Table Store
        table_store_impl = get_table_store(impl=table_type)
        table_store = table_store_impl()

        # Initialize logger
        logger = setup_logger(
            name="processor_logger",
            log_file="logs/processor.log",
            level=logging.INFO,
            max_bytes=10_000_000,
            backup_count=5,
        )

        # Initialize LLM
        llm_impl = get_llm(model_path=llm_path)
        llm = llm_impl(model_name=llm_path)

        # Initialize embedding model
        embed_impl = get_embed_model()
        embed_model = embed_impl(embed_path)

        # Initialize computation graph
        computation_graph = ComputationGraph()

        # Keep track of shared resources as a global context
        self.ctx = ConductorState(
            table_store=table_store,
            logger=logger,
            llm=llm,
            embedding_model=embed_model,
            table_reader=computation_graph,
        )

        # Initialize core services
        self.schema_processor = SchemaProcessor()
        self.base_table_producer = BaseTableProducer()
        self.base_table_reducer = BaseTableReducer()

    def get_target_schema(self, question: str) -> Node:
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
    ) -> Node:
        """
        Describes all tables within a schema.
        """
        return self.schema_processor.get_table_descriptions(
            ctx=self.ctx,
            db_schema=schema,
            num_sampling=num_sampling,
            num_sampled_rows=num_sampled_rows,
        )

    def get_enhanced_schemas(
        self, schema: str, table_descriptions: dict[str, str], num_rows=3
    ) -> Node:
        """
        Given a list of tables, produces enhanced schemas of the tables.
        """
        return self.schema_processor.get_enhanced_schemas(
            ctx=self.ctx,
            db_schema=schema,
            table_descriptions=table_descriptions,
            num_sampled_rows=num_rows,
        )
