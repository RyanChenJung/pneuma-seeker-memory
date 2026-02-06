from enum import Enum


class DocumentType(Enum):
    INTERMEDIATE_TABLE = "intermediate_table"
    RETRIEVED_TABLE = "retrieved_table"
    TARGET_TABLE = "target_table"
    ENUMERATED_TABLE = "enumerated_table"
    EXTERNAL_TABLE = "external_table"
    WEB_SEARCH_RESULT = "web_search_result"
    WEB_CRAWL_RESULT = "web_crawl_result"
