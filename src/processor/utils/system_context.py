from dataclasses import dataclass
from logging import Logger

from processor.llm.interface.model_interface import ModelProtocol
from processor.utils.dataframe_store import DataFrameStore


@dataclass
class SystemContext:
    df_store: DataFrameStore
    logger: Logger
    llm: ModelProtocol
    config: None  # May be supported in the future
