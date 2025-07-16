import bm25s
import os

from Stemmer import Stemmer

from processor.core.ir_system.ir_data_model import (
    AbstractDocument,
    Knowledge,
    RetrieverType,
    Text,
)
from processor.core.ir_system.retriever.abstract_retriever import AbstractRetriever


class KnowledgeBase(AbstractRetriever):
    """Represents a local knowledge retriever."""

    def __init__(self, models):
        super().__init__(models)
        self.local_retriever = None
        self.global_retriever = None
        self.LOCAL_INDEX_PATH = "indices/kb/local"
        self.GLOBAL_INDEX_PATH = "indices/kb/global"
        self.stemmer = Stemmer("english")

    def retriever_type(self) -> RetrieverType:
        """
        Defines the type of the retriever.
        """
        return RetrieverType.KNOWLEDGE_BASE

    def load(self):
        """
        Loads the retriever, including its dependencies (e.g., its model).
        """
        if self.local_retriever is None:
            self.local_retriever = bm25s.BM25.load(
                self.LOCAL_INDEX_PATH, load_corpus=True
            )
        if self.global_retriever is None:
            self.global_retriever = bm25s.BM25.load(
                self.GLOBAL_INDEX_PATH, load_corpus=True
            )

    def retrieve(
        self, query: str, sources: list[str], k: int
    ) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        self.load()
        retrieval_results: list[AbstractDocument] = []
        retrieval_results.extend(self.__actual_retrieve(query, self.local_retriever, k))
        retrieval_results.extend(
            self.__actual_retrieve(query, self.global_retriever, k)
        )

        self.local_retriever = None
        self.global_retriever = None
        return retrieval_results

    def __actual_retrieve(
        self, query: str, retriever: bm25s.BM25, k: int
    ) -> list[AbstractDocument]:
        max_k = min(len(retriever.corpus), k)
        query_tokens = bm25s.tokenize(query, stemmer=self.stemmer, show_progress=False)
        results, _ = self.retriever.retrieve(query_tokens, k=max_k, show_progress=False)
        retrieval_results: list[AbstractDocument] = []
        for result in results[0]:
            retrieval_results.append(
                Text(
                    doc_id=result["metadata"]["doc_id"],
                    retriever_type=RetrieverType.KNOWLEDGE_BASE,
                    content=result["text"],
                    metadata={
                        "type": result["metadata"]["type"],
                        "user": result["metadata"]["user"],
                    },
                )
            )
        return retrieval_results

    def index(self, documents: list[Knowledge]):
        """
        Indexes a list of documents to the retriever.
        """
        # Future-TODO: Handle possibility of conflicts (LLM required here!)
        corpus_json: list[dict[str, str]] = []

        if os.path.exists(self.RETRIEVER_PATH):
            retriever = bm25s.BM25.load(self.RETRIEVER_PATH, load_corpus=True)
            corpus_json.extend(retriever.corpus)
            os.rmdir(self.RETRIEVER_PATH)

        for doc_id, document in enumerate(documents):
            corpus_json.append(
                {
                    "text": document.content,
                    "metadata": {
                        "doc_id": f"kb_{doc_id}",
                        "type": document.metadata["type"],  # Either local or global
                        "user": document.metadata["user"],
                    },
                }
            )

        corpus_text = [doc["text"] for doc in corpus_json]
        corpus_tokens = bm25s.tokenize(
            corpus_text, stopwords="en", stemmer=self.stemmer, show_progress=False
        )

        retriever = bm25s.BM25(corpus=corpus_json)
        retriever.index(corpus_tokens, show_progress=True)
        retriever.save(self.RETRIEVER_PATH, corpus=corpus_json)
