import os
import re

import pandas as pd


from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    Table,
)


def clean_column(col):
    col = col.lower()
    # Replace spaces and hyphens with underscores
    col = col.replace("-", "_").replace(" ", "_")
    # Replace "(" and ")" with underscores
    col = col.replace("(", "_").replace(")", "_")
    # Remove anything that's not a letter, digit, or underscore
    col = re.sub(r"[^0-9a-z_]", "_", col)
    # Collapse multiple underscores into one
    col = re.sub(r"_+", "_", col)
    # Remove leading/trailing underscores
    col = col.strip("_")
    return col


def table_enumerator(pattern: str, data_sources: list[str]) -> list[AbstractDocument]:
    results: list[AbstractDocument] = []
    for data_src in data_sources:
        dataset_path = f"../../data_src/{data_src}/dataset"
        all_table_paths = os.listdir(dataset_path)
        regex = re.compile(pattern)

        match_table_paths = [path for path in all_table_paths if regex.match(path[:-4])]
        for table_path in match_table_paths:
            print(f"DEBUGGY: TABLE ENUMERATOR: Found table_path: {table_path} (cleaned: {table_path[:-4]})")
            actual_table = pd.read_csv(f"{dataset_path}/{table_path}")
            actual_table.rename(columns=clean_column, inplace=True)
            results.append(
                Table(
                    doc_id=table_path[:-4],
                    retriever_type=RetrieverType.PNEUMA,
                    content=actual_table,
                    metadata=dict(),
                )
            )
        
    print(f"DEBUGGY: results: {results}")
    return results
