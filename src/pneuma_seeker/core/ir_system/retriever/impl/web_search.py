from pneuma_seeker.core.ir_system.ir_data_model import RetrieverType
from pneuma_seeker.core.ir_system.ir_state import AbstractDocument
from pneuma_seeker.core.ir_system.retriever.abstract_retriever import AbstractRetriever


class WebSearch(AbstractRetriever):
    """Represents a web searcher."""

    @property
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

    def retrieve(self, query: str, sources: list[str], k: int) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        return []

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        pass
