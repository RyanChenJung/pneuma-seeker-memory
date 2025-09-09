from pneuma_seeker.core.ir_system.data_model import RetrieverModel, RetrieverType
from pneuma_seeker.core.ir_system.retriever.abstract_retriever import AbstractRetriever
from pneuma_seeker.core.ir_system.retriever.impl.enumerator import Enumerator
from pneuma_seeker.core.ir_system.retriever.impl.pneuma import Pneuma
from pneuma_seeker.core.ir_system.retriever.impl.document_db import DocumentDB
from pneuma_seeker.core.ir_system.retriever.impl.web_search import WebSearch


class RetrieverFactory:
    def __init__(self, models: RetrieverModel):
        self.retriever_instances = {
            RetrieverType.PNEUMA: Pneuma(models),
            RetrieverType.DOCUMENT_DB: DocumentDB(models),
            RetrieverType.WEB_SEARCH: WebSearch(models),
            RetrieverType.ENUMERATOR: Enumerator(models),
        }

    def get_retriever(self, retriever_type: RetrieverType) -> AbstractRetriever:
        """Factory function to return the correct Retriever instance."""
        return self.retriever_instances[retriever_type]
