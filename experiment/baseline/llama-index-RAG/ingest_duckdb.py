import os
import duckdb
from tqdm import tqdm


def ingest_duckdb(duckdb_name: str, dataset_path: str):
    con = duckdb.connect(f"index/{duckdb_name}")
    for table in tqdm([table[:-4] for table in os.listdir(dataset_path)]):
        con.execute(
            f"create table '{table}' as select * from read_csv('{dataset_path}/{table}.csv', ignore_errors=true)"
        )
    con.checkpoint()

if __name__ == "__main__":
    DATA_SRC = "../../../data_src"
    ARCHEOLOGY_DATASET_PATH = f"{DATA_SRC}/archeology/dataset"
    BIOMEDICAL_DATASET_PATH = f"{DATA_SRC}/biomedical/dataset"
    ENVIRONMENT_DATASET_PATH = f"{DATA_SRC}/environment/dataset"

    ingest_duckdb("archeology.duckdb", ARCHEOLOGY_DATASET_PATH)
    ingest_duckdb("biomedical.duckdb", BIOMEDICAL_DATASET_PATH)
    ingest_duckdb("environment.duckdb", ENVIRONMENT_DATASET_PATH)
