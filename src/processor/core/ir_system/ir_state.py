from abc import ABC
from typing import Any
from processor.core.ir_system.retriever.retriever_factory import RetrieverType


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


class TextDocument(AbstractDocument):
    """
    Represents textual document.
    """

    def __init__(
        self, retriever_type: RetrieverType, content: str, metadata: dict[str, str]
    ):
        super().__init__(retriever_type, content, metadata)

class IRState:
    def __init__(self):
        self.query = ""
        self.retrieved_results = []
