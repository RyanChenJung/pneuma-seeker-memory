from pathlib import Path
import re
import os

import duckdb
from tqdm import tqdm


def clean_column_table_name(name):
    """Cleans and normalizes column/table names."""
    name = name.lower()
    # Replace spaces and hyphens with underscores
    name = name.replace("-", "_").replace(" ", "_")
    # Replace "(" and ")" with underscores
    name = name.replace("(", "_").replace(")", "_")
    # Remove anything that's not a letter, digit, or underscore
    name = re.sub(r"[^0-9a-z_]", "_", name)
    # Collapse multiple underscores into one
    name = re.sub(r"_+", "_", name)
    # Remove leading/trailing underscores
    name = name.strip("_")
    return name


DATASET_NAME = "buysite"
DATASET_PATH = f"../{DATASET_NAME}/dataset"

if os.path.exists(f"{DATASET_NAME}.db"):
    raise FileExistsError(
        f"{DATASET_NAME}.db already exists. Aborting to prevent overwrite."
    )
else:
    print(f"Ingesting CSV files from {DATASET_PATH} into {DATASET_NAME}.db")

    with duckdb.connect(f"{DATASET_NAME}.db") as con:

        for table_file_name in tqdm(sorted(os.listdir(DATASET_PATH))):
            if not table_file_name.endswith(".csv"):
                continue

            table_id = clean_column_table_name(Path(table_file_name).stem)
            table_id_sql = f'"{table_id}"'

            file_path = (Path(DATASET_PATH) / table_file_name).as_posix()

            rel = con.read_csv(
                file_path, auto_detect=True, sample_size=-1, parallel=False
            )

            original_cols = rel.columns
            cleaned_cols = [clean_column_table_name(c) for c in original_cols]

            select_clause = ", ".join(
                f'"{orig}" AS "{cleaned}"'
                for orig, cleaned in zip(original_cols, cleaned_cols)
            )

            con.execute(
                f"""
                CREATE TABLE {table_id_sql} AS
                SELECT {select_clause}
                FROM read_csv(
                    '{file_path}',
                    auto_detect=true,
                    sample_size=-1,
                    parallel=false
                )
            """
            )
