from logging import Logger
from typing import Optional

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
        Indexes documents on a retriever.
        """
        self.__log(f"Indexing documents on the retriever {retriever_type}.")
        self.retriever_factory.get_retriever(retriever_type).index(documents)
        self.__log("Indexing process is done.")

    def retrieve_multisource_documents(
        self,
        prompt: str,
        sources: list[str],
        k: int = 10,
        retriever_types: Optional[list[RetrieverType]] = None,
    ) -> dict[RetrieverType, list[AbstractDocument]]:
        """
        Retrieves documents from multiple retrievers as defined.
        """
        if retriever_types is not None:
            relevant_retrievers = retriever_types
        else:
            relevant_retrievers = [RetrieverType.PNEUMA, RetrieverType.DOCUMENT_DB]
        self.__log(
            f"Starting document retrieval from {[i.value for i in relevant_retrievers]} for this prompt: {prompt}..."
        )

        all_retrieval_results: dict[RetrieverType, list[AbstractDocument]] = dict()
        for retriever_type in relevant_retrievers:
            self.__log(f"=> Retrieving from: {retriever_type}")
            curr_retrieval_results = self.retrieve_documents(
                retriever_type, prompt, sources, k
            )
            self.__log(f"==> Retrieved documents ({len(curr_retrieval_results)} docs):")
            for retrieved_document in curr_retrieval_results:
                self.__log(f"===> {retrieved_document}")
            self.__log("=" * 50)
            all_retrieval_results[retriever_type] = curr_retrieval_results
        self.__log("Document retrieval completed")
        return all_retrieval_results

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
