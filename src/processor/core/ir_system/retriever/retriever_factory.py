from enum import Enum
from typing import Type
from processor.ir_system.retriever.abstract_retriever import AbstractRetriever
from processor.ir_system.retriever.impl.pneuma import Pneuma
from processor.ir_system.retriever.impl.knowledge_base import KnowledgeBase
from processor.ir_system.retriever.impl.web_search import WebSearch


class RetrieverType(Enum):
    PNEUMA = "Pneuma"
    KNOWLEDGE_BASE = "Knowledge Base"
    WEB_SEARCH = "Web Search"


def get_retriever(retriever_type: RetrieverType) -> Type[AbstractRetriever]:
    """Factory function to return the correct Retriever instance."""
    if retriever_type == RetrieverType.PNEUMA:
        return Pneuma
    elif retriever_type == RetrieverType.KNOWLEDGE_BASE:
        return KnowledgeBase
    elif retriever_type == RetrieverType.WEB_SEARCH:
        return WebSearch
    else:
        raise ValueError(f"No retriever is of type {retriever_type}.")
