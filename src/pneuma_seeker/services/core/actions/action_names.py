from enum import Enum


class ActionNames(Enum):
    PYTHON_EXECUTOR = "python_executor"
    SQL_EXECUTOR = "sql_executor"
    TABLE_RETRIEVE = "table_retrieve"
    TABLE_ENUMERATION = "table_enumeration"
    WEB_SEARCH = "web_search"
    WEB_CRAWL = "web_crawl"
    ASSUMPTION_CHECK = "assumption_check"
    SITUATIONAL_ANALYSIS = "situational_analysis"
    JOIN_PATH_EXTRACTION = "join_path_extraction"

    # Materializer-only actions
    SEMANTIC_COLUMN_GENERATION = "semantic_column_generation"
    SEMANTIC_JOIN = "semantic_join"
    TABLE_PROJECTION = "table_projection"

    # Conductor-only actions
    STATE_MANIPULATION = "state_manipulation"
    MATERIALIZER = "materializer"
    USER_FACING_COMMUNICATION = "user_facing_communication"


class ActionExecutionStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
