import os
from sentence_transformers import SentenceTransformer

import time
import bm25s
import Stemmer

from transformers import set_seed
from chromadb_deterministic import PersistentClient
from chromadb_deterministic.api.models.Collection import Collection
from pneuma.hybrid_mechanism import HybridRetriever, RerankingMode


os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
set_seed(42, deterministic=True)

base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(base_dir, "models", "bge-base")
embed_model = SentenceTransformer(model_path, local_files_only=True)

stemmer = Stemmer.Stemmer("english")
reranker = None
reranking_mode = RerankingMode.NONE
hybrid_retriever = HybridRetriever(reranker, reranking_mode)
hitrates_data: list[dict[str, str]] = []


def evaluate_benchmark(
    benchmark: list[dict[str, str]],
    benchmark_type: str,
    k: int,
    collection: Collection,
    retriever,
    stemmer,
    dataset: str,
    n=3,
    alpha=0.5,
    use_rephrased_questions=False,
    dictionary_id_bm25=None,
):
    start = time.time()
    hitrate_sum = 0
    wrong_questions = []
    increased_k = k * n
    retrieved_tables = []

    questions = []
    for data in benchmark:
        questions.append(data["question"])
    
    idx = 0
    datum = benchmark[0]
    answer_tables = datum["answer_tables"]
    question_embedding = embed_model.encode(datum["question"]).tolist()

    query_tokens = bm25s.tokenize(
        questions[idx], stemmer=stemmer, show_progress=False
    )

    results, scores = retriever.retrieve(
        query_tokens, k=increased_k, show_progress=False
    )
    bm25_res = (results, scores)
    vec_res = collection.query(
        query_embeddings=[question_embedding], n_results=increased_k
    )

    all_nodes = hybrid_retriever.retrieve(
        retriever,
        collection,
        bm25_res,
        vec_res,
        increased_k,
        questions[idx],
        alpha,
        query_tokens,
        question_embedding,
        dictionary_id_bm25,
    )
    before = hitrate_sum
    for table, _, _ in all_nodes[:k]:
        table = table.split("_SEP_")[0]
        if table not in retrieved_tables:
            retrieved_tables.append(table)
        if table in answer_tables:
            hitrate_sum += 1
            break
    if before == hitrate_sum:
        wrong_questions.append(idx)
    return retrieved_tables


def retrieve_tables(question: str, k = 10):
    dataset = "buysite"
    n = 5
    alpha = 0.5
    content_benchmark = [
        {
            "id": "",
            "question": question,
            "answer_tables": [],
        }
    ]

    client = PersistentClient(
        os.path.join(base_dir, f"vector-index-{dataset}-schema_narrations-sample_rows-context")
    )
    collection = client.get_collection("benchmark")
    retriever = bm25s.BM25.load(
        os.path.join(base_dir, f"fulltext-index-{dataset}-schema_narrations-sample_rows-context"),
        load_corpus=True,
    )
    dictionary_id_bm25 = {
        datum["metadata"]["table"]: datum_idx
        for datum_idx, datum in enumerate(retriever.corpus)
    }

    return evaluate_benchmark(
        benchmark=content_benchmark,
        benchmark_type="content",
        k=k,
        collection=collection,
        retriever=retriever,
        stemmer=stemmer,
        dataset=dataset,
        n=n,
        alpha=alpha,
        use_rephrased_questions=False,
        dictionary_id_bm25=dictionary_id_bm25,
    )

