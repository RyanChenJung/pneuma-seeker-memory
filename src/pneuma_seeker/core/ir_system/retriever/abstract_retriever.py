from abc import ABC, abstractmethod
from pneuma_seeker.core.ir_system.ir_state import AbstractDocument
from pneuma_seeker.core.ir_system.ir_data_model import RetrieverType
from pneuma_seeker.model.interface.abstract_model import AbstractModel


class AbstractRetriever(ABC):
    def __init__(self, models: dict[str, AbstractModel]):
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
    def retrieve(self, query: str, sources: list[str], k: int) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query from certain sources.
        """
        pass

    @abstractmethod
    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        pass
