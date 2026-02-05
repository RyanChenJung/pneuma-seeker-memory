from enum import Enum
from typing import Any

import numpy as np
from pandas import DataFrame
from pyxdameraulevenshtein import damerau_levenshtein_distance
from sklearn.feature_extraction.text import CountVectorizer
from tqdm import tqdm

from pneuma_seeker.shared.schemas.core.action import ActionNames
from pneuma_seeker.services.core.actions.interfaces.abstract_action import Action
from pneuma_seeker.services.core.actions.interfaces.applicable import Applicable
from pneuma_seeker.shared.parser import augmented_literal_eval
from pneuma_seeker.shared.schemas.language_model.message import LLMMessage
from pneuma_seeker.shared.schemas.language_model.role import Role


class SyntacticSimMetric(Enum):
    NONE = None
    EDIT_DIST = "Edit Distance"
    JACCARD_QGRAM = "Jaccard QGram"


class SemanticJoin(Action, Applicable):
    def get_name(self) -> str:
        return ActionNames.SEMANTIC_JOIN.value

    def get_description(self) -> str:
        return "Join two tables based on semantic similarity between specified columns."

    def get_input_schema(self) -> dict[str, str]:
        return {
            "left_df": "Pandas DataFrame representing the left table.",
            "right_df": "Pandas DataFrame representing the right table.",
            "left_cols": "List of column names from left_df to use for semantic comparison.",
            "right_cols": "List of column names from right_df to use for semantic comparison.",
            "alpha": "Float (0 to 1) weighting cosine vs syntactic similarity (default=0.5).",
            "top_k": "Integer number of best matches to keep per left row (default=3).",
            "delimiter": "String delimiter used when concatenating text (default=' [SEP] ').",
            "embed_batch_size": "Integer batch size for embedding calls (default=30).",
            "syntactic_sim_metric": "Syntactic similarity metric to use: NONE, EDIT_DIST, or JACCARD_QGRAM (default=EDIT_DIST).",
            "use_llm": "Boolean indicating whether to use LLM filtering for matches (default=False).",
        }

    def get_notes(self) -> str:
        return """
        This action performs a semantic join between two pandas DataFrames based on specified columns.
        It computes semantic similarity using embeddings and optionally syntactic similarity metrics.
        The result is a DataFrame containing joined rows along with their similarity scores.
        """

    def apply(self, input: dict[str, Any]) -> DataFrame:
        left_df: DataFrame | None = input.get("left_df")
        right_df: DataFrame | None = input.get("right_df")
        left_cols: list[str] | None = input.get("left_cols")
        right_cols: list[str] | None = input.get("right_cols")
        alpha: float = input.get("alpha", 0.5)
        top_k: int = input.get("top_k", 3)
        delimiter: str = input.get("delimiter", " [SEP] ")
        embed_batch_size: int = input.get("embed_batch_size", 30)
        syntactic_sim_metric: SyntacticSimMetric = input.get(
            "syntactic_sim_metric", SyntacticSimMetric.EDIT_DIST
        )
        use_llm: bool = input.get("use_llm", False)

        if not isinstance(left_df, DataFrame):
            raise ValueError("left_df must be a pandas DataFrame.")
        if not isinstance(right_df, DataFrame):
            raise ValueError("right_df must be a pandas DataFrame.")
        if not isinstance(left_cols, list) or not all(
            isinstance(c, str) for c in left_cols
        ):
            raise ValueError("left_cols must be a list of strings.")
        if not isinstance(right_cols, list) or not all(
            isinstance(c, str) for c in right_cols
        ):
            raise ValueError("right_cols must be a list of strings.")
        return self.join(
            left_df,
            right_df,
            left_cols,
            right_cols,
            alpha,
            top_k,
            delimiter,
            embed_batch_size,
            syntactic_sim_metric,
            use_llm,
        )

    def join(
        self,
        left_df: DataFrame,
        right_df: DataFrame,
        left_cols: list[str],
        right_cols: list[str],
        alpha: float = 0.5,
        top_k: int = 3,
        delimiter: str = " [SEP] ",
        embed_batch_size=30,
        syntactic_sim_metric: SyntacticSimMetric = SyntacticSimMetric.EDIT_DIST,
        use_llm=False,
    ) -> DataFrame:
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
            return DataFrame(
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

        return DataFrame(joined_rows)

    def __concat_relevant_values(
        self, df: DataFrame, relevant_cols: list[str], delimiter: str
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
            return self.language_model_api.encode(texts)

        chunks: list[np.ndarray] = []
        n = len(texts)
        num_chunks = (n + embed_batch_size - 1) // embed_batch_size
        for i in tqdm(range(0, n, embed_batch_size), total=num_chunks, desc=desc):
            chunk = texts[i : i + embed_batch_size]
            chunks.append(self.language_model_api.encode(chunk))
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
            self.language_model_api.chat(
                [LLMMessage(role=Role.SYSTEM.value, content=prompt)]
            )
        )
        return augmented_literal_eval(response)
