import os
import re
from pathlib import Path

import duckdb
from pneuma_seeker.shared.schemas.core.ir_system import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.services.core.ir_system.retriever.abstract_retriever import AbstractRetriever
from pneuma_seeker.shared.str_processor import clean_column_table_name


class Enumerator(AbstractRetriever):
    """Represents a web searcher."""

    @property
    def retriever_type(self) -> RetrieverType:
        """
        Defines the type of the retriever.
        """
        return RetrieverType.ENUMERATOR

    def load(self):
        """
        Loads the retriever, including its dependencies (e.g., its model).
        """
        pass

    def retrieve(
        self,
        query: str,
        k: int,
        sample_only: bool,
        sample_size: int | None = None,
    ) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query, where the query is a regex pattern.
        """
        results: list[AbstractDocument] = []
        for dataset_name in self.config.DATA_SOURCES:
            dataset_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "..",
                "..",
                "..",
                "..",
                "..",
                "..",
                "data_src",
                dataset_name,
                "dataset",
            )
            all_table_paths = os.listdir(dataset_path)
            regex = re.compile(query)
            match_table_paths = [
                path for path in all_table_paths if regex.match(path[:-4])
            ]

            for table_path in match_table_paths:
                table_name = clean_column_table_name(
                    Path(table_path).stem
                )  # Assume table is already ingested
                query_table = f"""
                SELECT * FROM {table_name}
                """
                if sample_only:
                    if sample_size is None or sample_size <= 0:
                        sample_size = 5
                    query_table += f" LIMIT {sample_size}"
                with duckdb.connect(
                    database=os.path.join(self.config.DB_BACKEND_PATH, f"{dataset_name}.db")
                ) as con:
                    actual_table = con.execute(query_table).fetchdf()
                results.append(
                    Table(
                        doc_id=clean_column_table_name(table_path[:-4].split("/")[-1]),
                        retriever_type=RetrieverType.ENUMERATOR,
                        content=actual_table,
                        metadata=dict(),
                        path=f"{dataset_path}/{table_path}",
                    )
                )
        return results

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        pass
