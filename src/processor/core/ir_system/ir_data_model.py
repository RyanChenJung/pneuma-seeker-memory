from abc import ABC
from enum import Enum
from typing import Any

from pandas import DataFrame


class RetrieverType(Enum):
    PNEUMA = "Pneuma"
    KNOWLEDGE_BASE = "Knowledge Base"
    WEB_SEARCH = "Web Search"


class AbstractDocument(ABC):
    """
    Represents (abstractly) the unit of information in Processor.
    """

    def __init__(
        self, doc_id: str, retriever_type: RetrieverType, content: Any, metadata: dict[str, str]
    ):
        self.doc_id = doc_id
        self.retriever_type = retriever_type
        self.content = content
        self.metadata = metadata


class Knowledge(AbstractDocument):
    """
    Represents some form of knowledge from users.

    - retriever_type: RetrieverType.KNOWLEDGE_BASE
    - content: str
    - metadata: {"type": "local/global", "user": "..."}
    """

    def __init__(self, doc_id, retriever_type, content: str, metadata):
        super().__init__(doc_id, retriever_type, content, metadata)


class Table(AbstractDocument):
    """
    Represents a table.

    - retriever_type: RetrieverType.PNEUMA (Pneuma is the current table discovery system)
    - content: DataFrame
    - metadata: {"table_name": "...", "dataset_name": "..."}
    """

    def __init__(self, doc_id, retriever_type, content: DataFrame, metadata):
        super().__init__(doc_id, retriever_type, content, metadata)


class TableContext(AbstractDocument):
    """
    Represents table context.

    - retriever_type: RetrieverType.PNEUMA (Pneuma is the current table discovery system)
    - content: str
    - metadata: {"table_name": "...", "dataset_name": "...", "type": "..."}
    """

    def __init__(self, doc_id, retriever_type, content: str, metadata):
        super().__init__(doc_id, retriever_type, content, metadata)


class Text(AbstractDocument):
    """
    Represents textual document.
    """

    def __init__(self, doc_id, retriever_type, content: str, metadata):
        super().__init__(doc_id, retriever_type, content, metadata)
