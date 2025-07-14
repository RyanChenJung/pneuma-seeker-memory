from processor.core.ir_system.ir_data_model import RetrieverType
from processor.core.ir_system.ir_state import AbstractDocument
from processor.core.ir_system.retriever.abstract_retriever import AbstractRetriever

class KnowledgeBase(AbstractRetriever):
    """Represents a local knowledge retriever."""
    # TODO: Think of user preferences, global knowledge, session knowledge, and so on. Model them effectively.
    def retriever_type(self) -> RetrieverType:
        """
        Defines the type of the retriever.
        """
        return RetrieverType.KNOWLEDGE_BASE

    def load(self):
        """
        Loads the retriever, including its dependencies (e.g., its model).
        """
        pass

    def retrieve(self, query: str) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        return []

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        pass


