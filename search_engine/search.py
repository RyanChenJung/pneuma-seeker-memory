import bm25s
import Stemmer

from tqdm import tqdm

hitrates_data: list[dict[str, str]] = []


def search(
    question: str,
    k: int,
    index_path: str,
):
    retriever = bm25s.BM25.load(index_path, load_corpus=True)
    stemmer = Stemmer.Stemmer("english")

    query_tokens = bm25s.tokenize(question, stemmer=stemmer, show_progress=False)
    results, _ = retriever.retrieve(query_tokens, k=k, show_progress=False)
    for result_idx, result in enumerate(results[0]):
        print(f"=> Result {result_idx}: {result['text']}")


if __name__ == "__main__":
    index_path = "indices/demo-index"
    k = 5
    questions = [
        "What is the latest minimum tariff set by the U.S. government for Germany?"
    ]
    for question in questions:
        search(
            question,
            k,
            index_path,
        )
