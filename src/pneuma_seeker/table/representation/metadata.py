from enum import Enum
from typing import TypedDict


class TableMetadataType(Enum):
    TABLE_DESCRIPTION = 'table description'


class Metadata(TypedDict):
    db_schema: str
    table_id: str
    type: TableMetadataType
    information: str
