# src/pneuma_seeker/shared/table_reader.py
import os
import requests
import pandas as pd
from pneuma_seeker.services.core.ir_system.data_model import (
    AbstractDocument,
    Table,
    RetrieverType,
)
from pneuma_seeker.shared.str_processor import clean_column_table_name


class TableReader:
    """Handles loading and parsing external tables (CSV or Excel) from local paths or APIs."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        os.makedirs("temp", exist_ok=True)

    def process_external_tables(
        self, external_table_paths: list[str]
    ) -> list[AbstractDocument]:
        """Entry point: read all external tables and return Table documents."""
        external_docs: list[AbstractDocument] = []
        for path in external_table_paths:
            try:
                if path.startswith("/api") or path.startswith("api"):
                    local_path = self._download_from_api(path)
                    try:
                        external_docs.extend(self._read_table_content(local_path))
                    finally:
                        if local_path.startswith("temp") and os.path.exists(local_path):
                            os.remove(local_path)
                else:
                    external_docs.extend(self._read_table_content(path))
            except Exception as e:
                # You can log or handle specific exceptions here
                continue
        return external_docs

    def _download_from_api(self, data_path: str) -> str:
        """Download file from OpenWebUI API, return local file path."""
        # Normalize path and build full URL
        if self.base_url.endswith("/") and data_path.startswith("/"):
            data_path = data_path[1:]
        if data_path.endswith("/content"):
            data_path = data_path[: -len("/content")]
        data_url = self.base_url + data_path

        resp = requests.get(
            data_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=(10, 40),
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()
        if "csv" in content_type or "excel" in content_type:
            ext = ".csv" if "csv" in content_type else ".xlsx"
            local_path = os.path.join("temp", f"downloaded{ext}")
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return local_path
        elif "json" in content_type:
            meta = resp.json()
            file_path = meta.get("path")
            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"Invalid API response, no usable file path: {meta}")
            return file_path
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    def _read_table_content(self, path: str) -> list[AbstractDocument]:
        """Read a CSV or Excel file and return a list of Table documents."""
        retriever_type = RetrieverType.USER
        tables: list[AbstractDocument] = []

        def stem(filepath: str) -> str:
            return os.path.splitext(filepath)[0].split("/")[-1]

        if path.endswith((".xls", ".xlsx")):
            excel_name = stem(path)
            sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
            for original_name, df in sheets.items():
                standardized_name = f"{clean_column_table_name(excel_name)}_{clean_column_table_name(original_name)}"
                standardized_df = df.rename(columns=clean_column_table_name)
                tables.append(
                    Table(
                        doc_id=standardized_name,
                        retriever_type=retriever_type,
                        content=standardized_df,
                        metadata={"sheet_name": original_name},
                        path=path,
                    )
                )
        elif path.endswith(".csv"):
            file_stem = clean_column_table_name(stem(path))
            df = pd.read_csv(path).rename(columns=clean_column_table_name)
            tables.append(
                Table(
                    doc_id=file_stem,
                    retriever_type=retriever_type,
                    content=df,
                    metadata={},
                    path=path,
                )
            )
        else:
            raise ValueError(f"Unsupported file format: {path}")

        return tables
