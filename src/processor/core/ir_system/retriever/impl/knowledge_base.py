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

        curr_file_path = os.path.dirname(os.path.abspath(__file__))
        self.LOCAL_INDEX_PATH = os.path.join(
            curr_file_path, "indices", "kb", "local"
        )
        self.GLOBAL_INDEX_PATH = os.path.join(
            curr_file_path, "indices", "kb", "global"
        )
        self.stemmer = Stemmer("english")

    @property
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
            try:
                self.local_retriever = bm25s.BM25.load(
                    self.LOCAL_INDEX_PATH, load_corpus=True
                )
            except:
                pass
        if self.global_retriever is None:
            try:
                self.global_retriever = bm25s.BM25.load(
                    self.GLOBAL_INDEX_PATH, load_corpus=True
                )
            except:
                pass

    def retrieve(
        self, query: str, sources: list[str], k: int
    ) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        self.load()
        if self.local_retriever is None and self.global_retriever is None:
            print("Both the local and global retrievers have not been initialized.")
            return []
        retrieval_results: list[AbstractDocument] = []
        if self.local_retriever is not None:
            retrieval_results.extend(self.__actual_retrieve(query, self.local_retriever, k))
        if self.global_retriever is not None:
            retrieval_results.extend(
                self.__actual_retrieve(query, self.global_retriever, k)
            )

        self.local_retriever = None
        self.global_retriever = None
        return retrieval_results

    def __actual_retrieve(
        self, query: str, retriever: bm25s.BM25, k: int
    ) -> list[AbstractDocument]:
        if retriever.corpus is None:
            raise ValueError("Both the retriever or its corpus cannot be None.")
        max_k = min(len(retriever.corpus), k)
        query_tokens = bm25s.tokenize(query, stemmer=self.stemmer, show_progress=False)
        results, _ = retriever.retrieve(query_tokens, k=max_k, show_progress=False)
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

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        # Future-TODO: Handle possibility of conflicts (LLM required here!)
        corpus_json_local: list[dict] = []
        corpus_json_global: list[dict] = []

        new_global_document = False
        new_local_document = False
        for item in documents:
            if not isinstance(item, Knowledge):
                raise ValueError("All documents must be of type Knowledge.")
            if item.metadata["type"] == "local":
                new_local_document = True
            elif item.metadata["type"] == "global":
                new_global_document = True

        if new_local_document and os.path.exists(self.LOCAL_INDEX_PATH):
            retriever = bm25s.BM25.load(self.LOCAL_INDEX_PATH, load_corpus=True)
            if retriever.corpus is not None:
                corpus_json_local.extend(retriever.corpus)
            os.rmdir(self.LOCAL_INDEX_PATH)
        
        if new_global_document and os.path.exists(self.GLOBAL_INDEX_PATH):
            retriever = bm25s.BM25.load(self.GLOBAL_INDEX_PATH, load_corpus=True)
            if retriever.corpus is not None:
                corpus_json_global.extend(retriever.corpus)
            os.rmdir(self.GLOBAL_INDEX_PATH)

        for doc_id, document in enumerate(documents):
            if document.metadata["type"] == "local":
                corpus_json_local.append(
                    {
                        "text": document.content,
                        "metadata": {
                            "doc_id": f"kb_{doc_id}",
                            "type": document.metadata["type"],  # Either local or global
                            "user": document.metadata["user"],
                        },
                    }
                )
            elif document.metadata["type"] == "global":
                corpus_json_global.append(
                    {
                        "text": document.content,
                        "metadata": {
                            "doc_id": f"kb_{doc_id}",
                            "type": document.metadata["type"],  # Either local or global
                            "user": document.metadata["user"],
                        },
                    }
                )
        
        if new_global_document:
            corpus_text = [doc["text"] for doc in corpus_json_global]
            corpus_tokens = bm25s.tokenize(
                corpus_text, stopwords="en", stemmer=self.stemmer, show_progress=False
            )

            retriever = bm25s.BM25(corpus=corpus_json_global)
            retriever.index(corpus_tokens, show_progress=True)
            retriever.save(self.GLOBAL_INDEX_PATH, corpus=corpus_json_global)
        
        if new_local_document:
            corpus_text = [doc["text"] for doc in corpus_json_local]
            corpus_tokens = bm25s.tokenize(
                corpus_text, stopwords="en", stemmer=self.stemmer, show_progress=False
            )

            retriever = bm25s.BM25(corpus=corpus_json_local)
            retriever.index(corpus_tokens, show_progress=True)
            retriever.save(self.LOCAL_INDEX_PATH, corpus=corpus_json_local)
