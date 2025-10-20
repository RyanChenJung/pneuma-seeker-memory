from logging import Logger

from pneuma_seeker.core.ir_system.data_model import AbstractDocument
from pneuma_seeker.core.ir_system.prompt_factory import PromptFactory
from pneuma_seeker.core.ir_system.retriever.retriever_factory import (
    RetrieverFactory,
    RetrieverModel,
    RetrieverType,
)
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.utils.logger import formatted_log


class IRSystem:
    """
    Information Retrieval System that manages multiple retrievers
    and handles document indexing and retrieval.
    """
    def __init__(self, llm: AbstractModel, embed_model: AbstractModel, logger: Logger):
        self.prompt_factory = PromptFactory()
        self.llm = llm
        self.embed_model = embed_model
        self.logger = logger
        self.retriever_factory = RetrieverFactory(
            RetrieverModel(llm=self.llm, embed_model=self.embed_model)
        )

    def index_documents(
        self, retriever_type: RetrieverType, documents: list[AbstractDocument]
    ):
        """
        Indexes documents into a retriever.
        """
        self.__log(f"Indexing documents on the retriever {retriever_type}.")
        self.retriever_factory.get_retriever(retriever_type).index(documents)
        self.__log("Indexing process is done.")

    def retrieve_documents(
        self,
        retriever_type: RetrieverType,
        prompt: str,
        sources: list[str],
        k: int = 10,
    ) -> list[AbstractDocument]:
        """
        Retrieves documents from the specified retriever.

        - prompt (str): The query to be given to the retriever.
        """
        retriever = self.retriever_factory.get_retriever(retriever_type)
        documents = retriever.retrieve(prompt, sources, k)
        return documents

    def __log(self, text: str):
        formatted_log(self.logger, "IR System", text)
