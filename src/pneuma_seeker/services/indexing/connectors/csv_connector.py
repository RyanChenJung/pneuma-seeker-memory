from pathlib import Path
from typing import Any, Generator, Hashable

from pandas import read_csv

from pneuma_seeker.services.indexing.connectors.base import SourceConnector
from pneuma_seeker.shared.str_processor import clean_column_table_name


class CSVConnector(SourceConnector):
    """Source connector for CSV files."""

    def __init__(self, config: dict[str, Any]):
        """Initializes the CSV connector with the given configuration."""
        super().__init__(config)

        path = config.get("directory_path")
        if not path:
            raise ValueError("CSV connector requires 'directory_path'.")

        self.directory_path = Path(path)

        if not self.directory_path.exists():
            raise ValueError(f"Path does not exist: {self.directory_path}")

        if not self.directory_path.is_dir():
            raise ValueError(f"Not a directory: {self.directory_path}")

    @property
    def source_type(self) -> str:
        """Returns connector type identifier."""
        return "csv"

    def check_connection(self) -> bool:
        """Validates whether the source can be accessed with current config."""
        try:
            stream_map = self.__resolve_stream_map()
            if not stream_map:
                return False
            return all(path.exists() and path.is_file() for path in stream_map.values())
        except Exception:
            return False

    def discover(self) -> list[dict[str, Any]]:
        """Discovers available streams/tables and associated metadata."""
        stream_map = self.__resolve_stream_map()
        return [
            {
                "stream": stream,
                "table_name": stream,
                "path": path.as_posix(),
            }
            for stream, path in stream_map.items()
        ]

    def read(self, stream: str) -> Generator[dict[Hashable, Any], None, None]:
        """Yields records from the given stream."""
        stream_map = self.__resolve_stream_map()
        if stream not in stream_map:
            raise KeyError(f"Unknown CSV stream: {stream}")

        table = read_csv(stream_map[stream])
        for row in table.to_dict(orient="records"):
            yield row

    def __resolve_stream_map(self) -> dict[str, Path]:
        """Resolves the mapping of stream names to CSV file paths based on the directory configuration."""
        stream_map: dict[str, Path] = {}

        directory = self.directory_path.expanduser().resolve()
        csv_files = sorted(directory.rglob("*.csv"))

        dedupe: dict[str, int] = {}
        for file in csv_files:
            base_name = clean_column_table_name(file.stem)
            if base_name not in dedupe:
                dedupe[base_name] = 0
                stream_name = base_name
            else:
                dedupe[base_name] += 1
                stream_name = f"{base_name}_{dedupe[base_name]}"
            stream_map[stream_name] = file

        return stream_map
