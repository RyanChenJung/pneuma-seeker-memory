import os
import sys
import time
import bm25s
import Stemmer

import pandas as pd

from pandas import DataFrame
from tqdm import tqdm


def get_table_contents(table_path: str, table_name: str):
    documents: list[dict] = []
    table = pd.read_csv(table_path)
    for row_idx, row in table.iterrows():
        parts = [f"{col}: {row[col]}" for col in table.columns]
        documents.append(
            {
                "text": " | ".join(parts),
                "metadata": {"table": f"{table_name}_SEP_content_{row_idx}"},
            }
        )
    return documents


def get_table_contexts(contexts: DataFrame, table_name: str):
    documents: list[dict] = []
    for idx, context in contexts.iterrows():
        if context["table_name"] == f"{table_name}.csv":
            documents.append(
                {
                    "text": context["description"],
                    "metadata": {"table": f"{table_name}_SEP_context_{idx}"},
                }
            )
    return documents


def index_dataset(dataset_path: str, dataset_name: str):
    stemmer = Stemmer.Stemmer("english")
    corpus_json: list[dict] = []
    contexts = pd.read_csv(f"{dataset_path}/metadata.csv")

    for table in tqdm(sorted(os.listdir(f"{dataset_path}/dataset"))):
        table_contents = get_table_contents(
            f"{dataset_path}/dataset/{table}", table[:-4]
        )
        table_contexts = get_table_contexts(contexts, table[:-4])

        corpus_json.extend(table_contents)
        corpus_json.extend(table_contexts)

    corpus_text = [doc["text"] for doc in corpus_json]
    corpus_tokens = bm25s.tokenize(
        corpus_text, stopwords="en", stemmer=stemmer, show_progress=False
    )

    retriever = bm25s.BM25(corpus=corpus_json)
    retriever.index(corpus_tokens, show_progress=True)
    retriever.save(f"indices/keyword-index-{dataset_name}")


if __name__ == "__main__":
    DATASET_NAMES = ["biomedical", "environment", "archeology"]
    for dataset_name in DATASET_NAMES:
        start = time.time()
        index_dataset(f"../../../data_src/{dataset_name}", dataset_name)
        end = time.time()
        print(f"Indexing time for dataset {dataset_name}: {end-start} seconds")
