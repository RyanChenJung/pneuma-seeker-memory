from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pyxdameraulevenshtein import damerau_levenshtein_distance
from sklearn.feature_extraction.text import CountVectorizer
from tqdm.auto import tqdm

from pneuma_seeker.services.language_model.abstract_model import AbstractModel
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.role import Role
from pneuma_seeker.shared.parser import augmented_literal_eval


class SyntacticSimMetric(Enum):
    NONE = None
    EDIT_DIST = "Edit Distance"
    JACCARD_QGRAM = "Jaccard QGram"


class SemanticOperator:
    def __init__(
        self, llm: AbstractModel, embed_model: AbstractModel, batch_size: int = 10
    ) -> None:
        self.llm = llm
        self.embed_model = embed_model
        self.batch_size = max(1, batch_size)

    def generate_semantic_column(
        self,
        source_table: pd.DataFrame,
        new_column_name: str,
        instruction: str,  # Explanation includes the possible values, i.e., the domain
    ) -> list[Any]:
        """
        Produces a new semantically-induced column using the values from
        `source_table` based on the specified instruction.

        **Assumption**:
            - All columns in the source table are relevant to get values of the new column
              (meaning that the irrelevant columns have been removed)
            - The instruction already includes the expected values

        Parameters:
            source_table: The table to generate a new column for.
            new_column_name: The name of the new column.
            instruction: The instruction for the LLM to produce values for the new column.
        """
        if len(source_table) == 0:
            return []

        cached_values: dict[str, str] = {}
        formatted_values = self.__format_values(source_table)

        unique_values = list(dict.fromkeys(formatted_values))
        for i in range(0, len(unique_values), self.batch_size):
            batch = unique_values[i : i + self.batch_size]
            encoded_prompt = [
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content="You are given a list of values from a table, and your task is to generate a new column. Output the values directly as a Python list of strings/integers/floats WITHOUT any extra formatting or explanation.",
                ),
                LLMMessage(
                    role=Role.USER.value,
                    content=f"User-defined instruction to form the new column named {new_column_name}: {instruction}",
                ),
                LLMMessage(
                    role=Role.USER.value,
                    content=f"Values to transform: {batch}",
                ),
            ]

            raw_output = "".join(self.llm.chat(encoded_prompt)).strip()
            start = raw_output.find("[")
            end = raw_output.rfind("]")

            if start != -1 and end != -1 and start < end:
                list_str = raw_output[start : end + 1]  # include the closing bracket
                try:
                    transformed_values = augmented_literal_eval(list_str)
                except (SyntaxError, ValueError):
                    # fallback if the content is not valid Python literal
                    transformed_values = []
            else:
                # no valid list delimiters found
                transformed_values = []

            for val_idx, value in enumerate(transformed_values):
                cached_values[batch[val_idx]] = value

        return [cached_values[val] for val in formatted_values]

    def __format_values(self, table: pd.DataFrame):
        formatted_values: list[str] = []
        for _, row in table.iterrows():
            row_values: list[str] = []
            for col_name in table.columns:
                row_values.append(f"{col_name}: {row[col_name]}")
            formatted_values.append("; ".join(row_values))
        return formatted_values

    def semantic_join(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        left_cols: list[str],
        right_cols: list[str],
        alpha: float = 0.5,
        top_k: int = 3,
        delimiter: str = " [SEP] ",
        embed_batch_size=30,
        syntactic_sim_metric: SyntacticSimMetric = SyntacticSimMetric.EDIT_DIST,
        use_llm=False,
    ) -> pd.DataFrame:
        """
        Join rows from left_df and right_df using semantic similarity.

        Parameters:
            left_cols / right_cols: columns to use for semantic comparison
            alpha: weight for cosine vs edit similarity (0 to 1)
            top_k: number of best matches to keep for each row in left_df
            delimiter: used when concatenating text
            embed_batch_size: outer batching size for embeddings (progress via tqdm).
                          Set to None or <=0 to disable outer batching.

        Returns:
            DataFrame of joined rows with similarity_score column.
        """

        # Ensure left_df is the smaller one (to minimize LLM calls later)
        if len(left_df) > len(right_df):
            left_df, right_df = right_df, left_df
            left_cols, right_cols = right_cols, left_cols

        # Edge case: at least one of the tables has no rows
        if len(left_df) == 0 or len(right_df) == 0:
            return pd.DataFrame(
                columns=[
                    *(f"left_{c}" for c in left_df.columns),
                    *(f"right_{c}" for c in right_df.columns),
                    "similarity_score",
                ]
            )

        # Concatenate relevant values from left_df and right_df
        left_values = self.__concat_relevant_values(left_df, left_cols, delimiter)
        right_values = self.__concat_relevant_values(right_df, right_cols, delimiter)

        # Produce embeddings for the concatenated values
        left_emb = self.__embed_texts(
            left_values,
            "Embedding left (concat)",
            embed_batch_size,
        )
        right_emb = self.__embed_texts(
            right_values,
            "Embedding right (concat)",
            embed_batch_size,
        )

        # Compute pairwise cosine similarities (L x R)
        cos_mat = self.__pairwise_cosine_sim_matrix(left_emb, right_emb)

        # Compute pairwise edit similarities (L x R)
        if syntactic_sim_metric == SyntacticSimMetric.NONE:
            score_mat = cos_mat
        elif syntactic_sim_metric == SyntacticSimMetric.EDIT_DIST:
            edit_mat = self.__pairwise_edit_sim_matrix(
                left_values, right_values, desc="Edit similarity (concat)"
            )
            score_mat = alpha * cos_mat + (1.0 - alpha) * edit_mat
        else:
            jaccard_qgram_mat = self.__pairwise_jaccard_qgram_matrix(
                left_values, right_values
            )
            score_mat = alpha * cos_mat + (1.0 - alpha) * jaccard_qgram_mat

        # For each left row, take top-k right matches
        joined_rows: list[dict[str, object]] = []

        if use_llm:
            for li in tqdm(range(score_mat.shape[0]), desc="Materializing joined rows"):
                row_scores = score_mat[li, :]
                top_indices = np.argsort(-row_scores)[:top_k]  # descending order

                lrow = left_df.iloc[int(li)]
                candidate_rrows = [right_df.iloc[int(ri)] for ri in top_indices]

                mask = self.__llm_filter_pairs(lrow, candidate_rrows)
                for keep, ri in zip(mask, top_indices):
                    if keep == 1:
                        rrow = right_df.iloc[int(ri)]
                        joined_rows.append(
                            {
                                **{f"left_{k}": lrow[k] for k in left_df.columns},
                                **{f"right_{k}": rrow[k] for k in right_df.columns},
                                "similarity_score": float(row_scores[ri]),
                            }
                        )
        else:
            for li in tqdm(range(score_mat.shape[0]), desc="Materializing joined rows"):
                row_scores = score_mat[li, :]
                top_indices = np.argsort(-row_scores)[:top_k]  # descending order

                lrow = left_df.iloc[int(li)]
                for ri in top_indices:
                    rrow = right_df.iloc[int(ri)]
                    joined_rows.append(
                        {
                            **{f"left_{k}": lrow[k] for k in left_df.columns},
                            **{f"right_{k}": rrow[k] for k in right_df.columns},
                            "similarity_score": float(row_scores[ri]),
                        }
                    )

        return pd.DataFrame(joined_rows)

    def __concat_relevant_values(
        self, df: pd.DataFrame, relevant_cols: list[str], delimiter: str
    ) -> list[str]:
        """Builds per-row concatenated values of the relevant columns once."""
        texts: list[str] = []
        for _, row in df.iterrows():
            texts.append(
                self.__concat_for_embedding(
                    relevant_cols, row.to_dict(), delimiter=delimiter
                )
            )
        return texts

    def __concat_for_embedding(
        self,
        fields: list[str],
        row: dict[str, str | float | int],
        delimiter: str,
    ) -> str:
        """Concatenates values as 'col: value' chunks to preserve structure."""
        chunks: list[str] = []
        for col in fields:
            val = row.get(col, "")
            sval = str(val).strip()
            chunks.append(f"{col}: {sval}")
        return delimiter.join(chunks)

    def __embed_texts(
        self,
        texts: list[str],
        desc="Embedding",
        embed_batch_size: int = 256,
    ) -> np.ndarray:
        """
        Embeds texts with optional outer-level batching.

        Returns a (N, D) ndarray.
        """
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        if embed_batch_size is None or embed_batch_size <= 0:
            embs = self.embed_model.encode(texts)
            return np.asarray(embs)

        chunks: list[np.ndarray] = []
        n = len(texts)
        num_chunks = (n + embed_batch_size - 1) // embed_batch_size
        for i in tqdm(range(0, n, embed_batch_size), total=num_chunks, desc=desc):
            chunk = texts[i : i + embed_batch_size]
            emb_chunk = self.embed_model.encode(chunk)
            chunks.append(np.asarray(emb_chunk))
        return np.vstack(chunks)

    def __pairwise_cosine_sim_matrix(
        self, Left: np.ndarray, Right: np.ndarray
    ) -> np.ndarray:
        """
        Computes pairwise cosine similarity matrix between two sets of embeddings.

        Left: (L, D), Right: (R, D) -> returns (L, R), clipped to [0, 1] (negatives -> 0).
        """
        if Left.size == 0 or Right.size == 0:
            return np.zeros((Left.shape[0], Right.shape[0]), dtype=np.float32)

        # L2-normalize rows
        def _safe_row_norm(X: np.ndarray) -> np.ndarray:
            norms = np.linalg.norm(X, axis=1, keepdims=True)
            norms[norms == 0.0] = 1.0  # avoid div-by-zero
            return X / norms

        L = _safe_row_norm(Left.astype(np.float32, copy=False))
        R = _safe_row_norm(Right.astype(np.float32, copy=False))
        S = L @ R.T  # cosine similarity in [-1, 1]
        np.clip(S, 0.0, 1.0, out=S)
        return S

    def __pairwise_edit_sim_matrix(
        self,
        left_texts: list[str],
        right_texts: list[str],
        desc: str = "Edit similarity",
    ) -> np.ndarray:
        """
        Computes pairwise normalized Damerau-Levenshtein similarity matrix (L x R).
        """
        L = len(left_texts)
        R = len(right_texts)
        M = np.zeros((L, R), dtype=np.float32)
        for i in tqdm(range(L), desc=desc, total=L):
            a = left_texts[i]
            row_vals = []
            for b in right_texts:
                row_vals.append(self.__normalized_damerau_levenshtein(a, b))
            M[i, :] = row_vals
        return M

    def __normalized_damerau_levenshtein(self, a: str, b: str) -> float:
        """Normalize edit distance to a similarity score in [0,1]."""
        if not a and not b:
            return 1.0
        max_len = max(len(a), len(b))
        d = float(damerau_levenshtein_distance(a, b))
        return max(0.0, min(1.0, 1.0 - (d / max_len)))

    def __pairwise_jaccard_qgram_matrix(
        self,
        left_texts: list[str],
        right_texts: list[str],
        q: int = 3,
        pad: bool = False,
        dtype=np.float32,
    ):
        """
        Compute the pairwise Jaccard similarity matrix between two lists of strings
        using character q-grams.

        Args:
            left_texts: List of strings (rows of the similarity matrix).
            right_texts: List of strings (columns of the similarity matrix).
            q: Length of character n-grams (default=3).
            pad: Whether to pad strings with start/end markers before extracting q-grams.
            dtype: Data type of the returned similarity matrix.

        Returns:
            A (len(left_texts), len(right_texts)) NumPy array of Jaccard similarities.
        """

        # Helper: optionally pad text so prefixes and suffixes contribute q-grams
        def maybe_pad(text: str) -> str:
            if pad:
                return ("^" * (q - 1)) + text + ("$" * (q - 1))
            return text

        # Preprocess texts
        left_texts = [maybe_pad(s) for s in left_texts]
        right_texts = [maybe_pad(s) for s in right_texts]

        # Build q-gram vocabulary across both sets
        vectorizer = CountVectorizer(
            analyzer="char",  # extract character-level features
            ngram_range=(q, q),  # fixed q-gram size
            binary=True,  # treat q-grams as sets (presence/absence) instead of count
        )
        all_texts = left_texts + right_texts
        all_vectors = vectorizer.fit_transform(all_texts)

        # Split back into left and right subsets
        left_matrix = all_vectors[: len(left_texts), :]  # type: ignore # shape (L, vocab_size)
        right_matrix = all_vectors[len(left_texts) :, :]  # type: ignore # shape (R, vocab_size)

        # Intersection counts: |A ∩ B| for each pair (via sparse dot product)
        intersections = (left_matrix @ right_matrix.T).toarray().astype(np.float32)  # type: ignore # shape (L, R)

        # Set sizes: |A| and |B| for each string
        left_sizes = np.array(left_matrix.sum(axis=1)).ravel()  # shape (L,)
        right_sizes = np.array(right_matrix.sum(axis=1)).ravel()  # shape (R,)

        # Broadcast to compute unions: |A ∪ B| = |A| + |B| - |A ∩ B|
        unions = left_sizes[:, None] + right_sizes[None, :] - intersections

        # Jaccard index: |A ∩ B| / |A ∪ B| (avoid division by zero)
        similarities = np.divide(
            intersections, unions, out=np.zeros_like(intersections), where=unions > 0
        )

        return similarities.astype(dtype)

    def __llm_filter_pairs(self, left_row, right_rows) -> list[int]:
        """
        Calls LLM to classify which right_rows are valid matches for left_row.
        Returns a Python list of 0/1 of length len(right_rows).
        """
        prompt = f"""You are given one reference item from the LEFT table and several candidate items from the RIGHT table.  
Decide which RIGHT items refer to the same or very closely equivalent entity as the LEFT item.

Output your answer as a Python list of integers without any extra explanations, one per RIGHT item, where:  
- 1 means the RIGHT item matches/is equivalent to the LEFT item.  
- 0 means it does not match.  

LEFT item:
{left_row.to_dict()}

RIGHT candidates:
{[r.to_dict() for r in right_rows]}"""

        response = "".join(
            self.llm.chat([LLMMessage(role=Role.SYSTEM.value, content=prompt)])
        )
        return augmented_literal_eval(response)
