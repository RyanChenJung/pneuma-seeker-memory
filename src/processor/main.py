import logging
import os
from typing import Any

from processor.base_table_producer.base_table_producer import BaseTableProducer
from processor.base_table_reducer.base_table_reducer import BaseTableReducer
from processor.computation_graph import ComputationGraph, Node
from processor.conductor_state import ConductorState
from processor.model.interface.model_factory import get_embed_model, get_llm
from processor.schema_processor.schema_processor import SchemaProcessor
from processor.table.representation.abstract_table import AbstractTable
from processor.table.store.table_store_factory import (
    ImplementedTableStore,
    get_table_store,
)
from processor.utils.logger import setup_logger


class Processor:
    def __init__(
        self,
        llm_path: str,
        embed_path: str,
        table_store_type: ImplementedTableStore,
        output_path: str,
    ):
        # Initialize Table Store
        table_store_impl = get_table_store(table_store_type)
        table_store = table_store_impl(os.path.join(output_path, "db"))

        # Initialize logger
        logger = setup_logger(
            name="processor_logger",
            log_path=os.path.join(output_path, "log"),
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
            computation_graph=computation_graph,
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
        existing_descriptions: dict[str,str] = dict(),
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Describes all tables within a schema.
        """
        return self.schema_processor.get_table_descriptions(
            ctx=self.ctx,
            db_schema=schema,
            num_sampling=num_sampling,
            num_sampled_rows=num_sampled_rows,
            existing_descriptions=existing_descriptions,
            input_computation_nodes=input_computation_nodes,
        )

    def get_enhanced_schemas(
        self,
        schema: str,
        table_descriptions: dict[str, str],
        num_rows=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Given a list of tables, produces enhanced schemas of the tables.
        """
        return self.schema_processor.get_enhanced_schemas(
            ctx=self.ctx,
            db_schema=schema,
            table_descriptions=table_descriptions,
            num_sampled_rows=num_rows,
            input_computation_nodes=input_computation_nodes,
        )
    
    def select_relevant_table_ids(
        self,
        db_schema: str,
        target_schema: list[str],
        table_descriptions: dict[str, str],
        num_rows=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns the IDs of relevant tables within the DB schema for the given
        target schema.

        Args:
            db_schema (str): The DB schema to get the tables from.
            target_schema (list[str]): The target schema to choose the tables.
            table_descriptions (dict[str,str]): The descriptions of the tables.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[list[str]]): Computation node consisting of list of strings as the IDs of the relevant tables.
        """
        return self.base_table_producer.select_relevant_table_ids(
            self.ctx,
            db_schema,
            target_schema,
            table_descriptions,
            num_rows,
            input_computation_nodes,
        )
    
    def produce_union_operations(
        self,
        db_schema: str,
        table_descriptions: dict[str, str],
        num_rows=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to union tables (if any) within the DB schema.

        Args:
            db_schema (str): The DB schema to get the tables from.
            table_descriptions (dict[str,str]): The descriptions of the tables.
            num_rows (int): Number of rows to sample from each table.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[Any]): Computation node consisting of the union operations.
        """
        return self.base_table_producer.produce_union_operations(
            self.ctx,
            db_schema,
            table_descriptions,
            num_rows,
            input_computation_nodes,
        )
    
    def run_union_operations(
        self,
        table_mappings: dict[str, AbstractTable],
        operations: list[dict[str, Any]],
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to union tables (if any) within the DB schema.

        Args:
            table_mappings (dict[str,AbstractTable]): The mapping between table IDs and table objects.
            operations (list[dict[str, Any]]): The union operations.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[dict[str, AbstractTable]]): Computation node consisting of the table mappings after the operations have been applied.
        """
        return self.base_table_producer.run_union_operations(
            self.ctx,
            table_mappings,
            operations,
            input_computation_nodes,
        )

    def produce_join_operations(
        self,
        db_schema: str,
        table_descriptions: dict[str, str],
        num_rows=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to union tables (if any) within the DB schema.

        Args:
            db_schema (str): The DB schema to get the tables from.
            table_descriptions (dict[str,str]): The descriptions of the tables.
            num_rows (int): The number of rows to sample.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[list[dict[str,str]]]): Computation node consisting of the join operations.
        """
        return self.base_table_producer.produce_join_operations(
            self.ctx,
            db_schema,
            table_descriptions,
            num_rows,
            input_computation_nodes,
        )
    
    def run_join_operations(
        self,
        table_mapping: dict[str, AbstractTable],
        operations: list[dict[str, str]],
        num_values=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Returns a list of operations to join tables (if any) within the DB schema.

        Args:
            table_mappings (dict[str,AbstractTable]): The mapping between table IDs and table objects.
            operations (list[dict[str, Any]]): The join operations.
            num_values (int): Number of rows to sample for each table.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[dict[str, AbstractTable]]): Computation node consisting of the table mappings after the operations have been applied.
        """
        return self.base_table_producer.run_join_operations(
            self.ctx,
            table_mapping,
            operations,
            num_values,
            input_computation_nodes,
        )
    
    def compute_target_table(
        self,
        question: str,
        base_table: AbstractTable,
        target_schema: list[str],
        num_rows=3,
        input_nodes: list[Node] = [],
    ) -> Node:
        """
        Projects `base_table`, specifically its schema, to the `target_schema`,
        resulting in `target_table`.
        """
        return self.base_table_reducer.compute_target_table(
            self.ctx,
            question,
            base_table,
            target_schema,
            num_rows,
            input_nodes,
        )
    
    def apply_predicate_to_target_table(
        self,
        target_table: AbstractTable,
        question: str,
        num_rows=3,
        input_nodes: list[Node] = [],
    ) -> Node:
        """
        Applies a natural-language predicate to target table.
        """
        return self.base_table_reducer.apply_predicate_to_target_table(
            self.ctx,
            target_table,
            question,
            num_rows,
            input_nodes,
        )
