from abc import ABC, abstractmethod
from typing import Any, Generator, Hashable, Iterator


class SourceConnector(ABC):
	"""Base interface for source connectors used by IndexingService."""

	def __init__(self, config: dict[str, Any]):
		self.config = config

	@property
	@abstractmethod
	def source_type(self) -> str:
		"""Returns connector type identifier."""

	@abstractmethod
	def check_connection(self) -> bool:
		"""Validates whether the source can be accessed with current config."""

	@abstractmethod
	def discover(self) -> list[dict[str, Any]]:
		"""Discovers available streams/tables and associated metadata."""

	@abstractmethod
	def read(self, stream: str) -> Generator[dict[Hashable, Any], None, None]:
		"""Yields records from the given stream/table."""
