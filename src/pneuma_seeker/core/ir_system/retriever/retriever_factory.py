from pneuma_seeker.core.ir_system.ir_data_model import RetrieverType
from pneuma_seeker.core.ir_system.retriever.abstract_retriever import AbstractRetriever
from pneuma_seeker.core.ir_system.retriever.impl.pneuma import Pneuma
from pneuma_seeker.core.ir_system.retriever.impl.knowledge_base import KnowledgeBase
from pneuma_seeker.core.ir_system.retriever.impl.web_search import WebSearch
from pneuma_seeker.model.interface.abstract_model import AbstractModel


class RetrieverFactory:
    def __init__(self, models: dict[str, AbstractModel]):
        self.retriever_instances = {
            RetrieverType.PNEUMA: Pneuma(models),
            RetrieverType.KNOWLEDGE_BASE: KnowledgeBase(models),
            RetrieverType.WEB_SEARCH: WebSearch(models),
        }

    def get_retriever(self, retriever_type: RetrieverType) -> AbstractRetriever:
        """Factory function to return the correct Retriever instance."""
        return self.retriever_instances[retriever_type]
