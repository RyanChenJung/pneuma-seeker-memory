import string
import time

import bm25s
import requests
import Stemmer
from bs4 import BeautifulSoup


def index_docs(indexing_path: str, texts: list[str], urls: list[str]):
    stemmer = Stemmer.Stemmer("english")
    corpus_json: list[dict] = []

    for text, url in zip(texts, urls):
        corpus_json.append({
            "text": text,
            "metadata": {"url": url},
        })

    corpus_text = [doc["text"] for doc in corpus_json]
    corpus_tokens = bm25s.tokenize(
        corpus_text, stopwords="en", stemmer=stemmer, show_progress=False
    )

    retriever = bm25s.BM25(corpus=corpus_json)
    retriever.index(corpus_tokens, show_progress=True)
    retriever.save(indexing_path)

def crawl_and_split(url, max_tokens=300):
    # Step 1: Send HTTP request
    response = requests.get(url)
    response.raise_for_status()  # Raise exception for bad responses

    # Step 2: Parse HTML content with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Step 3: Extract text from relevant tags (e.g., <p>, <div>, <article>)
    text_elements = soup.find_all(['p', 'div', 'article', 'span', 'section'])
    full_text = ' '.join(elem.get_text(separator=' ', strip=True) for elem in text_elements)

    # Step 4: Remove punctuation and lowercase
    full_text = full_text.translate(str.maketrans('', '', string.punctuation)).lower()

    # Step 5: Tokenize by spaces
    tokens = full_text.split()

    # Step 6: Split into chunks of max_tokens
    chunks = [' '.join(tokens[i:i+max_tokens]) for i in range(0, len(tokens), max_tokens)]

    return chunks


if __name__ == "__main__":
    start = time.time()
    url = "https://kpmg.com/de/en/home/insights/2025/04/us-cell-consequences-for-german-companies.html"
    chunks = crawl_and_split(url, max_tokens=50)
    index_docs(
        "indices/demo-index", chunks, [url] * len(chunks)
    )
    end = time.time()
    print(f"Indexing time: {end-start} seconds")
