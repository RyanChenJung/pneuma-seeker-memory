import os

import duckdb
from tqdm import tqdm


DATASET_NAME = "buysite"
DATASET_PATH = f"../{DATASET_NAME}/dataset"

if os.path.exists(f"{DATASET_NAME}.db"):
    raise FileExistsError(f"{DATASET_NAME}.db already exists. Aborting to prevent overwrite.")
con = duckdb.connect(f"{DATASET_NAME}.db")

for table_file_name in tqdm(os.listdir(DATASET_PATH)):
    if table_file_name.endswith(".csv"):
        table_id = table_file_name[:-4]
        con.execute(
            f"""CREATE TABLE {table_id} AS FROM read_csv("{DATASET_PATH}/{table_file_name}\", ignore_errors = true)""",
        )

con.close()
