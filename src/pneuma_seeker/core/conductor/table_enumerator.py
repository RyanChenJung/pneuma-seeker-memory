from collections import defaultdict
import os
import re
from pneuma_seeker.core.ir_system.ir_data_model import AbstractDocument


DATASET_PATH = "../../data_src/environment/dataset"


def make_signature(name):
    # Replace digits with \d+
    return re.sub(r"\d+", r"\\d+", name)


def table_id_enumerator(curr_retrieval_results: list[AbstractDocument]):
    all_table_paths = os.listdir(DATASET_PATH)
    retrieved_table_ids = [i.doc_id for i in curr_retrieval_results]

    groups = defaultdict(list)
    for retrieved_table_id in retrieved_table_ids:
        sig = make_signature(retrieved_table_id)
        groups[sig].append(retrieved_table_id)
    
    matches: dict[str, list[str]] = defaultdict(list)
    for sig, _ in groups.items():
        pattern = re.compile(f"^{sig}$")
        matches[sig] = sorted([t[:-4] for t in all_table_paths if pattern.match(t[:-4])])
    
    print(f"Matches in table id enumerator: {dict(matches)}")
    return dict(matches)
