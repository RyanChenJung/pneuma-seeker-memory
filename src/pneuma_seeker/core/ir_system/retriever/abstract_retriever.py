from abc import ABC, abstractmethod
from pneuma_seeker.core.ir_system.data_model import AbstractDocument, RetrieverModel
from pneuma_seeker.core.ir_system.data_model import RetrieverType
from pneuma_seeker.utils.config import Config


class AbstractRetriever(ABC):
    def __init__(self, models: RetrieverModel, config: Config):
        """
        Initialize the Retriever class
        """
        self.models = models
        self.is_loaded = False
        self.config = config

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
    def retrieve(
        self,
        query: str,
        sources: list[str],
        k: int,
        sample_only: bool,
        sample_size: int | None = None,
    ) -> list[AbstractDocument]:
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
