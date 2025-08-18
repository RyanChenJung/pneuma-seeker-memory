import os
import json
import duckdb
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pneuma_seeker.core.conductor.data_model import HumanConductorInteraction
from pneuma_seeker.core.conductor.main import (
    AbstractDocument,
    RetrieverType,
    InformationNeedState,
)

# new import
import pandas as pd

from pneuma_seeker.core.materializer.operation.table_enumerator import clean_column

DB_PATH = os.path.join(".", "pneuma_seeker_state.duckdb")


# -------------------- Helpers for DataFrame (target_schemas) --------------------
def _serialize_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Serialize a pandas DataFrame into a JSON-serializable dict:
      - columns: list of column names (preserve order)
      - data: list of row dicts (records)
      - dtypes: mapping column -> dtype string for best-effort reconstruction
    """
    return {
        "columns": df.columns.tolist(),
        "data": df.to_dict(orient="records"),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }


def _deserialize_dataframe(obj: Dict[str, Any]) -> pd.DataFrame:
    """
    Reconstruct a DataFrame from the serialized dict.
    Attempts to coerce back to original-ish dtypes (int/float/bool/datetime).
    """
    if obj is None:
        return pd.DataFrame()

    columns = obj.get("columns", None)
    data = obj.get("data", [])
    dtypes = obj.get("dtypes", {})

    # Build dataframe from records; pandas will infer types
    df = pd.DataFrame(data, columns=columns)

    # Attempt dtype restoration (best-effort)
    for col, dtype_str in (dtypes or {}).items():
        if col not in df.columns:
            continue
        try:
            if "datetime" in dtype_str or "Timestamp" in dtype_str:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif "int" in dtype_str and df[col].notna().all():
                # use pandas nullable integer if possible
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            elif "float" in dtype_str:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            elif "bool" in dtype_str:
                # pandas nullable boolean
                df[col] = df[col].astype("boolean")
            # else: leave as-is (string/object)
        except Exception:
            # best-effort only; ignore and leave column as-is
            pass

    return df


# -------------------- DB INIT --------------------
def init_db():
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS interactions (
        user_id TEXT,
        chat_id TEXT,
        idx INTEGER,
        human_input TEXT,
        llm_response TEXT,
        ts TIMESTAMP
    )
    """
    )
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_state (
        user_id TEXT,
        chat_id TEXT,
        info_need_state_json TEXT,
        retrieval_results_json TEXT,
        ts TIMESTAMP
    )
    """
    )
    con.close()


# -------------------- INTERACTIONS --------------------
def load_interactions(user_id: str, chat_id: str) -> List[HumanConductorInteraction]:
    con = duckdb.connect(DB_PATH)
    rows = con.execute(
        """
        SELECT human_input, llm_response
        FROM interactions
        WHERE user_id = ? AND chat_id = ?
        ORDER BY idx ASC
    """,
        (user_id, chat_id),
    ).fetchall()
    con.close()

    return [HumanConductorInteraction(h, r) for h, r in rows]


def get_unique_user_chat_ids():
    con = duckdb.connect(DB_PATH)
    query = """
    SELECT DISTINCT user_id, chat_id
    FROM interactions
    UNION
    SELECT DISTINCT user_id, chat_id
    FROM chat_state
    """
    rows = con.execute(query).fetchall()
    con.close()
    return rows


def save_interaction(
    user_id: str, chat_id: str, interaction: HumanConductorInteraction
):
    con = duckdb.connect(DB_PATH)
    next_idx = con.execute(
        """
        SELECT COALESCE(MAX(idx), -1) + 1
        FROM interactions
        WHERE user_id = ? AND chat_id = ?
    """,
        (user_id, chat_id),
    ).fetchone()[
        0
    ]  # type: ignore
    con.execute(
        """
        INSERT INTO interactions (user_id, chat_id, idx, human_input, llm_response, ts)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            user_id,
            chat_id,
            next_idx,
            interaction.human_input,
            interaction.llm_response,
            datetime.utcnow(),
        ),
    )
    con.close()


# -------------------- CHAT STATE --------------------
def save_state(
    user_id: str,
    chat_id: str,
    info_need_state: InformationNeedState,
    retrieval_results: Dict[RetrieverType, List[AbstractDocument]],
):
    """
    Persist info_need_state and retrieval_results as JSON.
    target_schemas (DataFrames) are serialized with _serialize_dataframe.
    """
    # Serialize target_schemas (DataFrame -> JSON-able dict)
    serialized_target_schemas: Dict[str, Any] = {}
    for k, v in info_need_state.target_schemas.items():
        if isinstance(v, pd.DataFrame):
            serialized_target_schemas[k] = _serialize_dataframe(v)
        else:
            # fallback: try to JSON-ize; if not possible, store str()
            try:
                json.dumps(v)
                serialized_target_schemas[k] = v
            except Exception:
                serialized_target_schemas[k] = str(v)

    info_need_state_json = json.dumps(
        {
            "target_schemas": serialized_target_schemas,
            "is_target_schemas_materialized": info_need_state.is_target_schemas_materialized,
            "column_descriptions": info_need_state.column_descriptions,
            "sqls": info_need_state.sqls,
            "is_sql_executed": info_need_state.is_sql_executed,
        }
    )

    # Serialize retrieval results, store path if present, otherwise serialize content
    retrieval_results_json = json.dumps(
        {
            rt.value: [
                {
                    "doc_id": doc.doc_id,
                    "retriever_type": doc.retriever_type.value,
                    "path": doc.path,  # Could be None
                    "content": None if doc.path else doc.content,
                    "metadata": doc.metadata,
                }
                for doc in docs
            ]
            for rt, docs in retrieval_results.items()
        }
    )

    con = duckdb.connect(DB_PATH)
    con.execute(
        """DELETE FROM chat_state WHERE user_id = ? AND chat_id = ?""",
        (user_id, chat_id),
    )
    con.execute(
        """
        INSERT INTO chat_state (user_id, chat_id, info_need_state_json, retrieval_results_json, ts)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            user_id,
            chat_id,
            info_need_state_json,
            retrieval_results_json,
            datetime.utcnow(),
        ),
    )
    con.close()


def load_state(
    user_id: str, chat_id: str
) -> Tuple[InformationNeedState, Dict[RetrieverType, List[AbstractDocument]]]:
    con = duckdb.connect(DB_PATH)
    row = con.execute(
        """
        SELECT info_need_state_json, retrieval_results_json
        FROM chat_state
        WHERE user_id = ? AND chat_id = ?
        ORDER BY ts DESC
        LIMIT 1
    """,
        (user_id, chat_id),
    ).fetchone()
    con.close()

    if not row:
        return InformationNeedState(), {}

    info_json, retr_json = row
    info_data = json.loads(info_json)
    retr_data = json.loads(retr_json)

    info_state = InformationNeedState()

    # Reconstruct target_schemas, deserializing DataFrames where appropriate
    raw_target_schemas = info_data.get("target_schemas", {})
    reconstructed: Dict[str, Any] = {}
    for k, v in raw_target_schemas.items():
        if isinstance(v, dict) and "data" in v and "columns" in v:
            # looks like our serialized DataFrame
            reconstructed[k] = _deserialize_dataframe(v)
        else:
            # fallback: keep as-is
            reconstructed[k] = v

    info_state.target_schemas = reconstructed
    info_state.is_target_schemas_materialized = info_data.get(
        "is_target_schemas_materialized", False
    )
    info_state.column_descriptions = info_data.get("column_descriptions", {})
    info_state.sqls = info_data.get("sqls", [])
    info_state.is_sql_executed = info_data.get("is_sql_executed", False)

    retr_results: Dict[RetrieverType, List[AbstractDocument]] = {}
    for rt_str, docs in retr_data.items():
        rt = RetrieverType(rt_str)
        retr_results[rt] = []
        for d in docs:
            content = None
            if d.get("path"):
                try:
                    content = pd.read_csv(d["path"])
                    content.rename(columns=clean_column, inplace=True)
                except Exception as e:
                    # Optional: log or handle missing/corrupt file gracefully
                    content = None
            else:
                content = d.get("content")
            retr_results[rt].append(
                AbstractDocument(
                    doc_id=d["doc_id"],
                    retriever_type=rt,
                    content=content,
                    metadata=d["metadata"],
                    path=d.get("path"),
                )
            )

    return info_state, retr_results
