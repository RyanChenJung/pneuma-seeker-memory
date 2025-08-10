from abc import ABC
from enum import Enum
from typing import Any, Optional, TypedDict

from pandas import DataFrame


class RetrieverType(Enum):
    PNEUMA = "Pneuma"
    KNOWLEDGE_BASE = "Knowledge Base"
    WEB_SEARCH = "Web Search"


class IRFeedbackOutputType(TypedDict):
    irrelevant_doc_ids: list[str]
    feedback: str


class AbstractDocument(ABC):
    """
    Represents (abstractly) the unit of information in Processor.
    """

    def __init__(
        self,
        doc_id: str,
        retriever_type: RetrieverType,
        content: Any,
        metadata: dict[str, str],
        path: Optional[str] = None,
    ):
        self.doc_id = doc_id
        self.retriever_type = retriever_type
        self.content = content
        self.metadata = metadata
        self.path = path

    def __eq__(self, other):
        if not isinstance(other, AbstractDocument):
            return NotImplemented
        return (self.doc_id, self.retriever_type) == (
            other.doc_id,
            other.retriever_type,
        )

    def __hash__(self):
        return hash((self.doc_id, self.retriever_type))
    
    def __str__(self) -> str:
        return f"ID: {self.doc_id} ; Content: {self.content}"


class Knowledge(AbstractDocument):
    """
    Represents some form of knowledge from users.

    - retriever_type: RetrieverType.KNOWLEDGE_BASE
    - content: str
    - metadata: {"type": "local/global", "user": "..."}
    """

    def __init__(self, doc_id, retriever_type, content: str, metadata, path: Optional[str] = None):
        super().__init__(doc_id, retriever_type, content, metadata, path)


class Table(AbstractDocument):
    """
    Represents a table.

    - retriever_type: RetrieverType.PNEUMA (Pneuma is the current table discovery system)
    - content: DataFrame
    - metadata: {"table_name": "...", "dataset_name": "..."}
    """

    def __init__(self, doc_id, retriever_type, content: DataFrame, metadata, path: Optional[str] = None):
        super().__init__(doc_id, retriever_type, content, metadata, path)
    
    def __str__(self) -> str:
        content_representation = ""
        table: DataFrame = self.content
        content_representation += f"Table {self.doc_id}:\ncol: {" | ".join(table.columns)}"
        if len(table) > 0:
            # Sample 5 rows to represent the table
            sample_rows = table.sample(min(5, len(table)), random_state=42)
            sample_row_idx = 1
            for _, data in sample_rows.iterrows():
                str_data = [str(i) for i in data]
                content_representation += (
                    f"\nsample row {sample_row_idx}: {" | ".join(str_data)}"
                )
                sample_row_idx += 1
        return content_representation


class TableContext(AbstractDocument):
    """
    Represents table context.

    - retriever_type: RetrieverType.PNEUMA (Pneuma is the current table discovery system)
    - content: str
    - metadata: {"table_name": "...", "dataset_name": "...", "type": "..."}
    """

    def __init__(self, doc_id, retriever_type, content: str, metadata, path: Optional[str] = None):
        super().__init__(doc_id, retriever_type, content, metadata, path)


class Text(AbstractDocument):
    """
    Represents textual document.
    """

    def __init__(self, doc_id, retriever_type, content: str, metadata, path: Optional[str] = None):
        super().__init__(doc_id, retriever_type, content, metadata, path)


def convert_multi_retriever_results_to_str(retrieval_results: dict[RetrieverType, list[AbstractDocument]]):
    representation = ""
    for retriever_type in retrieval_results.keys():
        representation += f"Retriever {retriever_type}:\n{convert_retrieval_results_to_str(retrieval_results[retriever_type])}\n"
    return representation

def convert_retrieval_results_to_str(retrieval_results: list[AbstractDocument]):
    representation = ""
    for result in retrieval_results:
        representation += f"- ```{str(result)}```\n"
    return representation.strip()
