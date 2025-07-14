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
        self, retriever_type: RetrieverType, content: Any, metadata: dict[str, str]
    ):
        self.retriever_type = retriever_type
        self.content = content
        self.metadata = metadata


class Table(AbstractDocument):
    """
    Represents a table.

    - retriever_type: RetrieverType.PNEUMA (Pneuma is the current table discovery system)
    - content: DataFrame
    - metadata: {"table_name": "...", "dataset_name": "..."}
    """

    def __init__(
        self,
        retriever_type: RetrieverType,
        content: DataFrame,
        metadata: dict[str, str],
    ):
        super().__init__(retriever_type, content, metadata)


class TableContext(AbstractDocument):
    """
    Represents table context.

    - retriever_type: RetrieverType.PNEUMA (Pneuma is the current table discovery system)
    - content: str
    - metadata: {"table_name": "...", "dataset_name": "...", "type": "..."}
    """

    def __init__(
        self,
        retriever_type: RetrieverType,
        content: str,
        metadata: dict[str, str],
    ):
        super().__init__(retriever_type, content, metadata)


class Text(AbstractDocument):
    """
    Represents textual document.
    """

    def __init__(
        self, retriever_type: RetrieverType, content: str, metadata: dict[str, str]
    ):
        super().__init__(retriever_type, content, metadata)
