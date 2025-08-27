import os
import re


DATASET_PATH = "../../data_src/environment/dataset"


def table_enumerator(pattern: str) -> list[str]:
    all_table_paths = os.listdir(DATASET_PATH)
    regex = re.compile(pattern)
    match_table_paths = [path for path in all_table_paths if regex.match(path[:-4])]
    results: list[str] = []
    for table_path in match_table_paths:
        results.append(table_path[:-4])
    return results
