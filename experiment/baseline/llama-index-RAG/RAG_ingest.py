import os
import time
import pandas as pd


from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.database import DatabaseReader
from sqlalchemy import create_engine
from tqdm import tqdm
from transformers.trainer_utils import set_seed

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
set_seed(42, deterministic=True)


# Adjust names
DATASET = "archeology"
DATA_SRC_DIR = "../../../data_src"


def get_documents(path: str, duckdb_filename: str):
    engine = create_engine(f"duckdb:///index/{duckdb_filename}.duckdb")
    contexts = pd.read_csv(f"{path}/metadata.csv")
    db_reader = DatabaseReader(engine)
    final_documents = []

    for table in tqdm(
        sorted([table[:-4] for table in os.listdir(f"{path}/dataset")]),
        desc="Process tables",
    ):
        # Inserting contents
        documents = db_reader.load_data(f"select * from '{table}'")
        for i in range(len(documents)):
            documents[i].id_ = f"{table}.csv_part_{i}"
            documents[i].text = documents[i].id_ + f": {documents[i].text}"
            final_documents.append(documents[i])

        # Inserting contexts
        specific_contexts = [
            context["description"]
            for _, context in contexts.iterrows()
            if context["table_name"] == f"{table}.csv"
        ]
        base_id = len(documents)
        for j in range(len(specific_contexts)):
            document = Document(
                text=f"{table}.csv_part_{base_id+j}: " + specific_contexts[j],
                doc_id=f"{table}.csv_part_{base_id+j}",
            )
            final_documents.append(document)
    return final_documents


start_time = time.time()
documents = get_documents(f"{DATA_SRC_DIR}/{DATASET}", DATASET)
end_time = time.time()


Settings.embed_model = HuggingFaceEmbedding(
    model_name="../../../src/processor/model/weight/bge-base"
)


start_time = time.time()
index = VectorStoreIndex.from_documents(documents, show_progress=True)
end_time = time.time()


index.storage_context.persist(persist_dir=f"index/{DATASET}")
