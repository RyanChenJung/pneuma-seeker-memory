import duckdb
import pandas as pd
from pathlib import Path
from typing import Union, Dict, List

class TableStore:
    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        """Initialize TableStore with a DuckDB database.
        
        Args:
            db_path: Path to the database file or ":memory:" for in-memory database
        """
        self.conn = duckdb.connect(str(db_path))
        self._table_metadata: Dict[str, str] = {}

    def store_csv(self, csv_path: Union[str, Path], table_name: str) -> None:
        """Store a CSV file in the database.
        
        Args:
            csv_path: Path to the CSV file
            table_name: Name to assign to the table
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Create table from CSV
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} AS 
            SELECT * FROM read_csv_auto('{str(csv_path)}')
        """)
        self._table_metadata[table_name] = str(csv_path)

    def get_table(self, table_name: str) -> pd.DataFrame:
        """Retrieve a table as a pandas DataFrame.
        
        Args:
            table_name: Name of the table to retrieve
            
        Returns:
            pandas DataFrame containing the table data
        """
        if table_name not in self.list_tables():
            raise KeyError(f"Table not found: {table_name}")
        
        return self.conn.execute(f"SELECT * FROM {table_name}").df()

    def list_tables(self) -> List[str]:
        """List all available tables in the store.
        
        Returns:
            List of table names
        """
        return list(self._table_metadata.keys())

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
