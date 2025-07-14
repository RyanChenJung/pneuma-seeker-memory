import bm25s
import os

from Stemmer import Stemmer

from processor.core.ir_system.ir_data_model import (
    AbstractDocument,
    Knowledge,
    RetrieverType,
)
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

    def retrieve(
        self, query: str, sources: list[str], k: int
    ) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        return []

    def index(self, documents: list[Knowledge]):
        """
        Indexes a list of documents to the retriever.
        """
        # Future-TODO: Handle possibility of conflicts (LLM required here!)
        RETRIEVER_PATH = "indices/kb/knowledge_base"
        stemmer = Stemmer("english")
        corpus_json: list[dict[str, str]] = []

        if os.path.exists(RETRIEVER_PATH):
            retriever = bm25s.BM25.load(RETRIEVER_PATH, load_corpus=True)
            corpus_json.extend(retriever.corpus)
            os.rmdir(RETRIEVER_PATH)

        for document in documents:
            corpus_json.append(
                {
                    "text": document.content,
                    "metadata": {
                        "type": document.metadata["type"],  # Either local or global
                        "user": document.metadata["user"],
                    },
                }
            )

        corpus_text = [doc["text"] for doc in corpus_json]
        corpus_tokens = bm25s.tokenize(
            corpus_text, stopwords="en", stemmer=stemmer, show_progress=False
        )

        retriever = bm25s.BM25(corpus=corpus_json)
        retriever.index(corpus_tokens, show_progress=True)
        retriever.save(RETRIEVER_PATH, corpus=corpus_json)
