from enum import Enum


class ActionNames(Enum):
    PYTHON_EXECUTOR = "python_executor"
    SQL_EXECUTOR = "sql_executor"
    SEMANTIC_COLUMN_GENERATION = "semantic_column_generation"
    SEMANTIC_JOIN = "semantic_join"
    TABLE_RETRIEVE = "table_retrieve"
    TABLE_ENUMERATION = "table_enumeration"
    TABLE_PROJECTION = "table_projection"
    WEB_SEARCH = "web_search"
    WEB_CRAWL = "web_crawl"


class ActionExecutionStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
