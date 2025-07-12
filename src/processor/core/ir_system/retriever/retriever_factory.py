from enum import Enum
from typing import Type
from processor.core.ir_system.retriever.abstract_retriever import AbstractRetriever
from processor.core.ir_system.retriever.impl.pneuma import Pneuma
from processor.core.ir_system.retriever.impl.knowledge_base import KnowledgeBase
from processor.core.ir_system.retriever.impl.web_search import WebSearch


class RetrieverType(Enum):
    PNEUMA = "Pneuma"
    KNOWLEDGE_BASE = "Knowledge Base"
    WEB_SEARCH = "Web Search"


class RetrieverFactory:
    def __init__(self):
        self.retriever_instances = {
            RetrieverType.PNEUMA: Pneuma(),
            RetrieverType.KNOWLEDGE_BASE: KnowledgeBase(),
            RetrieverType.WEB_SEARCH: WebSearch(),
        }

    def get_retriever(self, retriever_type: RetrieverType) -> AbstractRetriever:
        """Factory function to return the correct Retriever instance."""
        return self.retriever_instances[retriever_type]
