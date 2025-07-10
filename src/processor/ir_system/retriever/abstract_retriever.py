from abc import ABC, abstractmethod
from processor.ir_system.state import AbstractDocument
from processor.ir_system.retriever.retriever_factory import RetrieverType


class AbstractRetriever(ABC):
    def __init__(self):
        """
        Initialize the Retriever class
        """
        self.is_loaded = False

    @property
    @abstractmethod
    def retriever_type(self) -> RetrieverType:
        """
        Defines the type of the retriever.
        """
        pass

    @abstractmethod
    def load(self):
        """
        Loads the retriever, including its dependencies (e.g., its model).
        """
        pass

    @abstractmethod
    def retrieve(self, query: str) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        pass

    @abstractmethod
    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        pass
