from processor.core.ir_system.ir_data_model import RetrieverType
from processor.core.ir_system.ir_state import AbstractDocument
from processor.core.ir_system.retriever.abstract_retriever import AbstractRetriever


class WebSearch(AbstractRetriever):
    """Represents a web searcher."""

    def retriever_type(self) -> RetrieverType:
        """
        Defines the type of the retriever.
        """
        return RetrieverType.WEB_SEARCH

    def load(self):
        """
        Loads the retriever, including its dependencies (e.g., its model).
        """
        pass

    def retrieve(self, query: str) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        pass

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        pass
