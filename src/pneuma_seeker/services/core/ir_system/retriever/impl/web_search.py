from openai import OpenAI
from pneuma_seeker.services.core.ir_system.data_model import RetrieverType, Text
from pneuma_seeker.services.core.ir_system.data_model import AbstractDocument
from pneuma_seeker.services.core.ir_system.retriever.abstract_retriever import AbstractRetriever


class WebSearch(AbstractRetriever):
    """Represents a web search interface."""

    def __init__(self, models, config):
        # Note: For now, we assume OpenAI model
        super().__init__(models, config)
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    @property
    def retriever_type(self) -> RetrieverType:
        """
        Defines the type of the retriever.
        """
        return RetrieverType.WEB_SEARCH

    def load(self):
        """
        Loads the retriever, including its dependencies (e.g., its model).
        """
        pass

    def retrieve(
        self,
        query: str,
        sources: list[str],
        k: int,
        sample_only: bool,
        sample_size: int | None = None,
    ) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        response = self.client.responses.create(
            model="o4-mini", tools=[{"type": "web_search"}], input=query
        )
        return [Text("web_search", RetrieverType.WEB_SEARCH, response.output_text, {})]

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever.
        """
        pass
