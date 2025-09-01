import numpy as np
import pandas as pd

from typing import Optional, Union

from pyxdameraulevenshtein import damerau_levenshtein_distance
from tqdm.auto import tqdm

from pneuma_seeker.model.interface.abstract_model import AbstractModel


class SemanticJoiner:
    def __init__(self, embed_model: AbstractModel):
        self.embed_model = embed_model

    def semantic_join(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        left_cols: list[str],
        right_cols: list[str],
        alpha: float = 0.5,
        threshold: float = 0.75,
        delimiter: str = " [SEP] ",
        embed_batch_size: Optional[int] = 30,
    ) -> pd.DataFrame:
        """
        Join rows from left_df and right_df using semantic similarity.

        Parameters:
            left_cols / right_cols: columns to use for semantic comparison
            alpha: weight for cosine vs edit similarity (0 to 1)
            threshold: minimum similarity to join
            delimiter: used when concatenating text
            embed_batch_size: outer batching size for embeddings (progress via tqdm).
                          Set to None or <=0 to disable outer batching.

        Returns:
            DataFrame of joined rows with similarity_score column.
        """

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
        edit_mat = self.__pairwise_edit_sim_matrix(
            left_values, right_values, desc="Edit similarity (concat)"
        )

        # Linearly combine both similarity measures
        score_mat = alpha * cos_mat + (1.0 - alpha) * edit_mat

        # Find matches that exceed the threshold
        matches = np.where(score_mat >= float(threshold))
        left_indices = matches[0]
        right_indices = matches[1]

        # Materialize matching rows
        joined_rows: list[dict[str, object]] = []
        for li, ri in tqdm(
            zip(left_indices, right_indices),
            total=len(left_indices),
            desc="Materializing joined rows",
        ):
            lrow = left_df.iloc[int(li)]
            rrow = right_df.iloc[int(ri)]
            joined_rows.append(
                {
                    **{f"left_{k}": lrow[k] for k in left_df.columns},
                    **{f"right_{k}": rrow[k] for k in right_df.columns},
                    "similarity_score": float(score_mat[li, ri]),
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
        row: dict[str, Union[str, float, int]],
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
        embed_batch_size: Optional[int] = 256,
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
