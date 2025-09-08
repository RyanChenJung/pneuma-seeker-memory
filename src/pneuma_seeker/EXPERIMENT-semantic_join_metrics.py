import os
import sys
import pandas as pd
from dotenv import load_dotenv
from torch.backends import cudnn

from pneuma_seeker.core.materializer.operation.semantic_joiner import SemanticJoiner
from pneuma_seeker.model.interface.model_factory import get_embed_model

import numpy as np
from pyxdameraulevenshtein import damerau_levenshtein_distance
from typing import Callable

embed_model_path = "model/weight/bge-base"
embed_model = get_embed_model()(embed_model_path)

# enforce more deterministic behavior
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
cudnn.deterministic = True
cudnn.benchmark = False

sys.path.append("..")
load_dotenv("../../.env")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity in [0,1]."""
    if np.all(a == 0) or np.all(b == 0):
        return 0.0
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return max(0.0, float(np.dot(a, b)))

def edit_similarity(a: str, b: str) -> float:
    """Normalized Damerau-Levenshtein similarity in [0,1]."""
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    d = float(damerau_levenshtein_distance(a, b))
    return max(0.0, min(1.0, 1.0 - (d / max_len)))

def hybrid_similarity_cosine_edit_dist(
    text_a: str,
    text_b: str,
    embed_func: Callable[[list[str]], np.ndarray],
    alpha: float = 0.5,
) -> dict:
    """
    Compute embedding, edit, and hybrid similarity scores.
    
    alpha = weight for embedding (cosine), (1-alpha) for edit distance.
    """
    # Get embeddings
    emb_a, emb_b = embed_func([text_a, text_b])
    cos = cosine_similarity(emb_a, emb_b)
    edit = edit_similarity(text_a, text_b)
    hybrid = alpha * cos + (1 - alpha) * edit
    
    return {
        "cosine": cos,
        "edit": edit,
        "hybrid": hybrid
    }


# Dummy embedder: convert string to vector of character ord values
def get_embed(texts: list[str]):
    return embed_model.encode(texts)

# Test
print(hybrid_similarity_cosine_edit_dist("kitten", "sitten", get_embed, alpha=0.7))
print(hybrid_similarity_cosine_edit_dist("apple", "appl", get_embed, alpha=0.7))
print(hybrid_similarity_cosine_edit_dist("apple", "banana", get_embed, alpha=0.7))

import numpy as np
import hashlib
from typing import Callable
from collections import Counter

# ---------------- q-grams ----------------
def qgrams(s: str, q: int = 3, pad: bool = False):
    if pad:
        s = '^'*(q-1) + s + '$'*(q-1)
    if len(s) < q:
        return [s]
    return [s[i:i+q] for i in range(len(s)-q+1)]

def jaccard_qgram(a: str, b: str, q: int = 3, pad: bool = False):
    A = set(qgrams(a, q, pad))
    B = set(qgrams(b, q, pad))
    if not A and not B:
        return 1.0
    return len(A & B) / len(A | B)

def cosine_qgram(a: str, b: str, q: int = 3, pad: bool = False):
    A = Counter(qgrams(a, q, pad))
    B = Counter(qgrams(b, q, pad))
    shared = set(A.keys()) & set(B.keys())
    dot = sum(A[k]*B[k] for k in shared)
    na = np.sqrt(sum(v*v for v in A.values()))
    nb = np.sqrt(sum(v*v for v in B.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na*nb)

# ---------------- MinHash ----------------
class MinHash:
    def __init__(self, num_perm: int = 128):
        self.num_perm = num_perm
        self.salts = [str(i).encode("utf8") for i in range(num_perm)]

    @staticmethod
    def _hash_bytes(b: bytes):
        return int(hashlib.sha256(b).hexdigest(), 16) & ((1<<64)-1)

    def signature(self, tokens):
        token_bytes = [t.encode("utf8") for t in tokens]
        sig = []
        for salt in self.salts:
            minv = (1<<64) - 1
            for tb in token_bytes:
                h = self._hash_bytes(salt + b"|" + tb)
                if h < minv:
                    minv = h
            sig.append(minv)
        return sig

def minhash_jaccard_est(sig1, sig2):
    equal = sum(1 for a, b in zip(sig1, sig2) if a == b)
    return equal / len(sig1)

# ---------------- SimHash ----------------
def _hash_to_int(x: str, bits: int = 64):
    h = int(hashlib.sha256(x.encode("utf8")).hexdigest(), 16)
    return h & ((1<<bits)-1)

def simhash(s: str, q: int = 3, bits: int = 64, pad: bool = False):
    grams = qgrams(s, q, pad)
    freqs = Counter(grams)
    v = [0]*bits
    for token, weight in freqs.items():
        h = _hash_to_int(token, bits)
        for i in range(bits):
            bit = (h >> i) & 1
            v[i] += weight if bit else -weight
    fp = 0
    for i, val in enumerate(v):
        if val >= 0:
            fp |= (1 << i)
    return fp

def hamming(a: int, b: int):
    return (a ^ b).bit_count()

# ---------------- Hybrid functions ----------------
def hybrid_similarity_cosine_jaccard_qgram(
    text_a: str, text_b: str, embed_func: Callable[[list[str]], np.ndarray], alpha: float = 0.5
):
    emb_a, emb_b = embed_func([text_a, text_b])
    cos = cosine_similarity(emb_a, emb_b)
    jacc = jaccard_qgram(text_a, text_b)
    hybrid = alpha * cos + (1 - alpha) * jacc
    return {"cosine": cos, "jaccard_qgram": jacc, "hybrid": hybrid}

def hybrid_similarity_cosine_cosine_qgram(
    text_a: str, text_b: str, embed_func: Callable[[list[str]], np.ndarray], alpha: float = 0.5
):
    emb_a, emb_b = embed_func([text_a, text_b])
    cos = cosine_similarity(emb_a, emb_b)
    cosq = cosine_qgram(text_a, text_b)
    hybrid = alpha * cos + (1 - alpha) * cosq
    return {"cosine": cos, "cosine_qgram": cosq, "hybrid": hybrid}

def hybrid_similarity_cosine_minhash(
    text_a: str, text_b: str, embed_func: Callable[[list[str]], np.ndarray], alpha: float = 0.5
):
    emb_a, emb_b = embed_func([text_a, text_b])
    cos = cosine_similarity(emb_a, emb_b)
    mh = MinHash(num_perm=64)
    sig_a = mh.signature(qgrams(text_a))
    sig_b = mh.signature(qgrams(text_b))
    mh_sim = minhash_jaccard_est(sig_a, sig_b)
    hybrid = alpha * cos + (1 - alpha) * mh_sim
    return {"cosine": cos, "minhash": mh_sim, "hybrid": hybrid}

def hybrid_similarity_cosine_simhash(
    text_a: str, text_b: str, embed_func: Callable[[list[str]], np.ndarray], alpha: float = 0.5
):
    emb_a, emb_b = embed_func([text_a, text_b])
    cos = cosine_similarity(emb_a, emb_b)
    fp_a = simhash(text_a)
    fp_b = simhash(text_b)
    simhash_sim = 1 - (hamming(fp_a, fp_b) / 64)
    hybrid = alpha * cos + (1 - alpha) * simhash_sim
    return {"cosine": cos, "simhash": simhash_sim, "hybrid": hybrid}

print(hybrid_similarity_cosine_jaccard_qgram("kitten", "sitten", get_embed, alpha=0.7))
print(hybrid_similarity_cosine_jaccard_qgram("apple", "appl", get_embed, alpha=0.7))
print(hybrid_similarity_cosine_jaccard_qgram("apple", "banana", get_embed, alpha=0.7))

# print(hybrid_similarity_cosine_cosine_qgram("kitten", "sitten", get_embed, alpha=0.7))
# print(hybrid_similarity_cosine_cosine_qgram("apple", "appl", get_embed, alpha=0.7))
# print(hybrid_similarity_cosine_cosine_qgram("apple", "banana", get_embed, alpha=0.7))

print(hybrid_similarity_cosine_minhash("kitten", "sitten", get_embed, alpha=0.7))
print(hybrid_similarity_cosine_minhash("apple", "appl", get_embed, alpha=0.7))
print(hybrid_similarity_cosine_minhash("apple", "banana", get_embed, alpha=0.7))

# print(hybrid_similarity_cosine_simhash("kitten", "sitten", get_embed, alpha=0.7))
# print(hybrid_similarity_cosine_simhash("apple", "appl", get_embed, alpha=0.7))
# print(hybrid_similarity_cosine_simhash("apple", "banana", get_embed, alpha=0.7))

# left_df = pd.DataFrame([
#     {"name": "MIT", "city": "Cambridge", "state": "MA", "country": "USA",
#      "founded": 1861, "students": 11466, "endowment_billion": 23.5,
#      "type": "Private", "colors": "Cardinal Red, Silver Gray", "nickname": "Engineers"},

#     {"name": "UChicago", "city": "Chicago", "state": "IL", "country": "USA",
#      "founded": 1890, "students": 17934, "endowment_billion": 10.3,
#      "type": "Private", "colors": "Maroon", "nickname": "Maroons"},

#     {"name": "Stanford", "city": "Stanford", "state": "CA", "country": "USA",
#      "founded": 1885, "students": 16164, "endowment_billion": 37.8,
#      "type": "Private", "colors": "Cardinal", "nickname": "Cardinal"},

#     {"name": "Cal Tech", "city": "Pasadena", "state": "CA", "country": "USA",
#      "founded": 1891, "students": 2237, "endowment_billion": 4.1,
#      "type": "Private", "colors": "Orange, White", "nickname": "Beavers"},

#     {"name": "Harvard Univ", "city": "Cambridge", "state": "MA", "country": "USA",
#      "founded": 1636, "students": 21900, "endowment_billion": 53.2,
#      "type": "Private", "colors": "Crimson", "nickname": "Crimson"},

#     {"name": "WashU", "city": "St. Louis", "state": "MO", "country": "USA",
#      "founded": 1853, "students": 16900, "endowment_billion": 15.3,
#      "type": "Private", "colors": "Red, Green", "nickname": "Bears"},

#     {"name": "UC Berkeley", "city": "Berkeley", "state": "CA", "country": "USA",
#      "founded": 1868, "students": 45700, "endowment_billion": 6.9,
#      "type": "Public", "colors": "Blue, Gold", "nickname": "Golden Bears"},

#     {"name": "Princeton", "city": "Princeton", "state": "NJ", "country": "USA",
#      "founded": 1746, "students": 8500, "endowment_billion": 37.7,
#      "type": "Private", "colors": "Orange, Black", "nickname": "Tigers"},

#     {"name": "Yale", "city": "New Haven", "state": "CT", "country": "USA",
#      "founded": 1701, "students": 14100, "endowment_billion": 42.3,
#      "type": "Private", "colors": "Yale Blue", "nickname": "Bulldogs"},

#     {"name": "University of Washington", "city": "Seattle", "state": "WA", "country": "USA",
#      "founded": 1861, "students": 49300, "endowment_billion": 4.9,
#      "type": "Public", "colors": "Purple, Gold", "nickname": "Huskies"}
# ])
# right_df = pd.DataFrame([
#     {"university": "Massachusetts Institute of Technology", "location_city": "Cambridge",
#      "location_state": "Massachusetts", "nation": "United States",
#      "year_established": 1861, "enrollment": 11500, "fund_billion": 23.7,
#      "control": "Private research", "school_colors": "Red and Gray", "sports_name": "MIT Engineers"},

#     {"university": "University of Chicago", "location_city": "Chicago",
#      "location_state": "Illinois", "nation": "US",
#      "year_established": 1890, "enrollment": 18000, "fund_billion": 10.2,
#      "control": "Private research university", "school_colors": "Maroon", "sports_name": "Chicago Maroons"},

#     {"university": "Leland Stanford Junior University", "location_city": "Stanford",
#      "location_state": "California", "nation": "U.S.",
#      "year_established": 1885, "enrollment": 16200, "fund_billion": 37.7,
#      "control": "Private research", "school_colors": "Cardinal", "sports_name": "Stanford Cardinal"},

#     {"university": "California Institute of Technology", "location_city": "Pasadena",
#      "location_state": "California", "nation": "United States",
#      "year_established": 1891, "enrollment": 2200, "fund_billion": 4.2,
#      "control": "Private research", "school_colors": "Orange and White", "sports_name": "Beavers"},

#     {"university": "Harvard University", "location_city": "Cambridge",
#      "location_state": "Massachusetts", "nation": "USA",
#      "year_established": 1636, "enrollment": 22000, "fund_billion": 53.3,
#      "control": "Private Ivy League", "school_colors": "Crimson", "sports_name": "Crimson"},

#     {"university": "Washington University in St. Louis", "location_city": "St. Louis",
#      "location_state": "Missouri", "nation": "United States",
#      "year_established": 1853, "enrollment": 17000, "fund_billion": 15.2,
#      "control": "Private research", "school_colors": "Red and Green", "sports_name": "Bears"},

#     {"university": "University of California, Berkeley", "location_city": "Berkeley",
#      "location_state": "California", "nation": "US",
#      "year_established": 1868, "enrollment": 46000, "fund_billion": 6.8,
#      "control": "Public research", "school_colors": "Blue and Gold", "sports_name": "Golden Bears"},

#     {"university": "Princeton University", "location_city": "Princeton",
#      "location_state": "New Jersey", "nation": "USA",
#      "year_established": 1746, "enrollment": 8600, "fund_billion": 37.6,
#      "control": "Private Ivy League", "school_colors": "Orange and Black", "sports_name": "Tigers"},

#     {"university": "Yale University", "location_city": "New Haven",
#      "location_state": "Connecticut", "nation": "US",
#      "year_established": 1701, "enrollment": 14000, "fund_billion": 42.4,
#      "control": "Private Ivy League", "school_colors": "Blue", "sports_name": "Bulldogs"},

#     {"university": "Washington State University", "location_city": "Pullman",
#      "location_state": "Washington", "nation": "United States",
#      "year_established": 1890, "enrollment": 31000, "fund_billion": 1.1,
#      "control": "Public research", "school_colors": "Crimson and Gray", "sports_name": "Cougars"}
# ])
