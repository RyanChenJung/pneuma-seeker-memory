from pneuma_seeker.services.core.ir_system.data_model import RetrieverModel, RetrieverType
from pneuma_seeker.services.core.ir_system.retriever.abstract_retriever import AbstractRetriever
from pneuma_seeker.services.core.ir_system.retriever.impl.enumerator import Enumerator
from pneuma_seeker.services.core.ir_system.retriever.impl.pneuma_retriever import PneumaRetriever
from pneuma_seeker.services.core.ir_system.retriever.impl.document_db import DocumentDB
from pneuma_seeker.services.core.ir_system.retriever.impl.web_crawler import WebCrawler
from pneuma_seeker.services.core.ir_system.retriever.impl.web_search import WebSearch
from pneuma_seeker.shared.config import Config


class RetrieverFactory:
    """Factory class to create Retriever instances based on the RetrieverType."""

    def __init__(self, models: RetrieverModel, config: Config):
        """Initialize the RetrieverFactory with available retriever instances."""
        self.retriever_instances = {
            RetrieverType.PNEUMA_RETRIEVER: PneumaRetriever(models, config),
            RetrieverType.DOCUMENT_DB: DocumentDB(models, config),
            RetrieverType.WEB_SEARCH: WebSearch(models, config),
            RetrieverType.ENUMERATOR: Enumerator(models, config),
            RetrieverType.WEB_CRAWL: WebCrawler(models, config),
        }

    def get_retriever(self, retriever_type: RetrieverType) -> AbstractRetriever:
        """Factory function to return the correct Retriever instance."""
        return self.retriever_instances[retriever_type]
