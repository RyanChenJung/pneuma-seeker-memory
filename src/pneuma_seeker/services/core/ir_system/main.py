from logging import Logger

from pneuma_seeker.services.core.ir_system.data_model import AbstractDocument
from pneuma_seeker.services.core.ir_system.prompt_factory import PromptFactory
from pneuma_seeker.services.core.ir_system.retriever.retriever_factory import (
    RetrieverFactory,
    RetrieverModel,
    RetrieverType,
)
from pneuma_seeker.services.language_model.abstract_model import AbstractModel
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.logger import formatted_log


class IRSystem:
    """
    Information Retrieval System that manages multiple retrievers
    and handles document indexing and retrieval.
    """

    def __init__(
        self,
        llm: AbstractModel,
        embed_model: AbstractModel,
        logger: Logger,
        config: Config,
    ):
        self.prompt_factory = PromptFactory()
        self.llm = llm
        self.embed_model = embed_model
        self.logger = logger
        self.config = config
        self.retriever_factory = RetrieverFactory(
            RetrieverModel(llm=self.llm, embed_model=self.embed_model), config
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
        sample_only: bool = False,
        sample_size: int | None = None,
    ) -> list[AbstractDocument]:
        """
        Retrieves documents from the specified retriever.

        - prompt (str): The query to be given to the retriever.
        - sample_only (bool): Whether to retrieve only a sample of documents.
        - sample_size (int | None): The number of documents to retrieve if sample_only is True.
        """
        retriever = self.retriever_factory.get_retriever(retriever_type)
        documents = retriever.retrieve(prompt, sources, k, sample_only, sample_size)
        return documents

    def __log(self, text: str):
        formatted_log(self.logger, "IR System", text)
