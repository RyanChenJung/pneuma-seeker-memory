import os
import re

import pandas as pd
from pneuma_seeker.core.ir_system.data_model import RetrieverType, Table
from pneuma_seeker.core.ir_system.data_model import AbstractDocument
from pneuma_seeker.core.ir_system.retriever.abstract_retriever import AbstractRetriever
from pneuma_seeker.utils.str_processor import clean_column_table_name


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
        self, query: str, sources: list[str], k: int
    ) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query, where the query is a regex pattern.
        """
        results: list[AbstractDocument] = []
        for data_src in sources:
            dataset_path = f"../../data_src/{data_src}/dataset"
            all_table_paths = os.listdir(dataset_path)
            regex = re.compile(query)
            match_table_paths = [
                path for path in all_table_paths if regex.match(path[:-4])
            ]

            for table_path in match_table_paths:
                actual_table = pd.read_csv(f"{dataset_path}/{table_path}")
                actual_table.rename(columns=clean_column_table_name, inplace=True)
                results.append(
                    Table(
                        doc_id=clean_column_table_name(table_path[:-4].split("/")[-1]),
                        retriever_type=RetrieverType.PNEUMA_RETRIEVER,
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
