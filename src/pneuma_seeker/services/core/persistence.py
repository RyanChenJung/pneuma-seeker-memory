# src/pneuma_seeker/core/persistence.py
import datetime
import json
import os
from io import StringIO
from logging import Logger
from typing import Any

import duckdb
import pandas as pd

from pneuma_seeker.services.core.conductor.state import InformationNeedState
from pneuma_seeker.services.core.ir_system.data_model import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.shared.str_processor import clean_column_table_name

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pneuma_seeker.duckdb"
)


def init_db(db_path: str | None = None):
    if db_path is not None:
        con = duckdb.connect(db_path)
    else:
        con = duckdb.connect(DB_PATH)
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_state (
        user_id TEXT,
        chat_id TEXT,
        info_need_state_json TEXT,
        retrieved_tables_json TEXT,
        provenance_graph_json TEXT,
        ts TIMESTAMP
    )
    """
    )
    con.close()


def get_unique_user_chat_ids():
    con = duckdb.connect(DB_PATH)
    query = """
    SELECT DISTINCT user_id, chat_id
    FROM chat_state
    """
    rows = con.execute(query).fetchall()
    con.close()
    return rows


def save_state(
    user_id: str,
    chat_id: str,
    info_need_state: InformationNeedState,
    retrieved_tables: list[AbstractDocument],
    enumerated_table_ids: list[str],
    provenance_graph: ProvenanceGraph,
    db_path: str | None = None,
):
    """
    Persists info_need_state and retrieved_tables as JSON.
    """

    # NOTE: we try to store content only when there's no file path.
    # If content is a DataFrame, attempt to convert to dict (records) so it's JSON-serializable.
    def serializable_content(content):
        if content is None:
            return None
        if isinstance(content, pd.DataFrame):
            return content.to_dict(orient="records")
        return content

    serialized_T = {
        doc_id: {
            "doc_id": doc.doc_id,
            "retriever_type": doc.retriever_type.value,
            "content": (
                None
                if getattr(doc, "path", None)
                else serializable_content(getattr(doc, "content", None))
            ),
            "metadata": doc.metadata,
            "path": getattr(doc, "path", None),
            "last_node_id": getattr(doc, "last_node_id", None),
        }
        for doc_id, doc in info_need_state.T.items()
    }

    info_need_state_json = json.dumps(
        {
            "T": serialized_T,
            "is_T_materialized": info_need_state.is_T_materialized,
            "column_descriptions": info_need_state.column_descriptions,
            "S": info_need_state.S,
            "is_S_executed": info_need_state.is_S_executed,
            "enumerated_table_ids": enumerated_table_ids,
        }
    )

    retrieved_tables_json = json.dumps(
        [
            {
                "doc_id": doc.doc_id,
                "retriever_type": doc.retriever_type.value,
                "content": (
                    None
                    if getattr(doc, "path", None)
                    else serializable_content(getattr(doc, "content", None))
                ),
                "metadata": doc.metadata,
                "path": getattr(doc, "path", None),
                "last_node_id": getattr(doc, "last_node_id", None),
            }
            for doc in retrieved_tables
        ]
    )

    provenance_graph_json = json.dumps(_serialize_provenance_graph(provenance_graph))

    con = duckdb.connect(db_path) if db_path is not None else duckdb.connect(DB_PATH)
    con.execute(
        """DELETE FROM chat_state WHERE user_id = ? AND chat_id = ?""",
        (user_id, chat_id),
    )
    con.execute(
        """
        INSERT INTO chat_state (
            user_id,
            chat_id,
            info_need_state_json,
            retrieved_tables_json,
            provenance_graph_json,
            ts
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            chat_id,
            info_need_state_json,
            retrieved_tables_json,
            provenance_graph_json,
            datetime.datetime.now(datetime.timezone.utc),
        ),
    )
    con.close()


def load_state(
    user_id: str, chat_id: str, logger: Logger, db_path: str | None = None
) -> tuple[
    InformationNeedState,
    list[AbstractDocument],
    list[str],
    ProvenanceGraph,
]:
    con = duckdb.connect(db_path) if db_path is not None else duckdb.connect(DB_PATH)
    row = con.execute(
        """
        SELECT info_need_state_json, retrieved_tables_json, provenance_graph_json
        FROM chat_state
        WHERE user_id = ? AND chat_id = ?
        ORDER BY ts DESC
        LIMIT 1
        """,
        (user_id, chat_id),
    ).fetchone()
    con.close()

    if not row:
        return InformationNeedState(), [], [], ProvenanceGraph(logger)

    state_json, retr_json, prov_json = row
    state_data: dict[str, Any] = json.loads(state_json)
    retr_data: list[dict[str, Any]] = json.loads(retr_json)
    prov_data = json.loads(prov_json)

    info_state = InformationNeedState()

    enumerated_table_ids: list[str] = state_data.get("enumerated_table_ids", [])

    raw_T: dict[str, dict[str, Any]] = state_data.get("T", {})
    T: dict[str, AbstractDocument] = {}
    for T_id, T_dict in raw_T.items():
        doc_id: str = T_dict.get("doc_id", "")
        retriever_type = RetrieverType(
            T_dict.get("retriever_type", RetrieverType.PNEUMA_RETRIEVER.value)
        )
        path: str = T_dict.get("path", "") or ""
        content = None
        last_node_id: str | None = T_dict.get("last_node_id", None)

        # If path exists and file is present, read from CSV
        if path and os.path.isfile(path):
            try:
                content = pd.read_csv(path)
                content.rename(columns=clean_column_table_name, inplace=True)
            except Exception as e:
                logger.warning(
                    f"[PERSISTENCE] Failed to read T table from path {path}: {e}"
                )
                content = None
        else:
            # Try to reconstruct content from serialized JSON content (list-of-dicts) if present
            raw_content = T_dict.get("content", None)
            if raw_content is not None:
                try:
                    # If it was stored as list-of-dicts (records), convert to DataFrame
                    if isinstance(raw_content, (list, dict)):
                        content = pd.DataFrame(raw_content)
                        content.rename(columns=clean_column_table_name, inplace=True)
                    elif isinstance(raw_content, str):
                        # if someone stored CSV/JSON string, try to parse
                        try:
                            content = pd.read_csv(StringIO(raw_content))
                        except Exception:
                            try:
                                content = pd.read_json(raw_content)
                            except Exception:
                                content = None
                    else:
                        content = None
                except Exception as e:
                    logger.warning(
                        f"[PERSISTENCE] Failed to reconstruct T content for {T_id}: {e}"
                    )
                    content = None

        if content is None:
            # if no content after attempts, skip (log)
            logger.info(
                f"[PERSISTENCE] Skipping T entry {T_id} (no path and no valid inline content)."
            )
            continue

        T[T_id] = Table(
            doc_id=doc_id,
            retriever_type=retriever_type,
            content=content,
            metadata=T_dict.get("metadata", {}),
            path=path,
            last_node_id=last_node_id,
        )

    info_state.T = T
    info_state.is_T_materialized = state_data.get("is_T_materialized", False)
    info_state.column_descriptions = state_data.get("column_descriptions", {})
    info_state.S = state_data.get("S", [])
    info_state.is_S_executed = state_data.get("is_S_executed", False)

    retrieved_tables: list[AbstractDocument] = []
    for doc in retr_data:
        content = None
        if doc.get("path"):
            try:
                content = pd.read_csv(doc["path"])
                content.rename(columns=clean_column_table_name, inplace=True)
            except Exception:
                logger.warning(
                    f"[PERSISTENCE] Failed to read retrieved table from path {doc['path']}, skipping."
                )
                continue
        else:
            # content stored inline (maybe list-of-dicts or string)
            raw_content = doc.get("content", None)
            if raw_content is not None:
                try:
                    if isinstance(raw_content, (list, dict)):
                        content = pd.DataFrame(raw_content)
                        content.rename(columns=clean_column_table_name, inplace=True)
                    elif isinstance(raw_content, str):
                        try:
                            content = pd.read_csv(StringIO(raw_content))
                        except Exception:
                            try:
                                content = pd.read_json(raw_content)
                            except Exception:
                                content = raw_content
                except Exception as e:
                    logger.warning(
                        f"[PERSISTENCE] Failed to reconstruct retrieved table content: {e}"
                    )
                    content = raw_content

        retrieved_tables.append(
            AbstractDocument(
                doc_id=doc["doc_id"],
                retriever_type=RetrieverType(doc["retriever_type"]),
                content=content,
                metadata=doc.get("metadata", {}),
                path=doc.get("path"),
                last_node_id=doc.get("last_node_id"),
            )
        )

    provenance_graph = _deserialize_provenance_graph(prov_data, logger)

    return info_state, retrieved_tables, enumerated_table_ids, provenance_graph


def _serialize_provenance_graph(graph: ProvenanceGraph) -> dict[str, Any]:
    """Serializes the ProvenanceGraph into a JSON-serializable dictionary."""
    nodes = [
        {
            "id": node.id,
            "source_retriever": getattr(
                node.source_retriever, "value", str(node.source_retriever)
            ),
            "python_code": node.python_code,
            "description": node.description,
            "children": [child.id for child in node.children],
            "parents": [parent.id for parent in node.parents],
        }
        for node in graph.nodes.values()
    ]

    return {"nodes": nodes, "meta": {"node_count": len(nodes)}}


def _deserialize_provenance_graph(
    obj: dict[str, Any], logger: Logger
) -> ProvenanceGraph:
    if not obj or not obj.get("nodes"):
        logger.info(
            "[PERSISTENCE] No provenance nodes found in serialized data; initializing default root graph."
        )
        return ProvenanceGraph(logger)

    graph = ProvenanceGraph(logger, create_default_root=False)
    id_to_node: dict[str, ProvenanceNode] = {}

    # 1. create all nodes first
    for n in obj.get("nodes", []):
        # Recreate RetrieverType from the canonical Enum defined in ir_system.data_model
        source_val = n.get("source_retriever")
        try:
            source_enum = RetrieverType(source_val)
        except Exception:
            # fallback: try by name
            try:
                source_enum = RetrieverType[source_val]
            except Exception:
                logger.warning(
                    f"[PERSISTENCE] Unknown retriever type '{source_val}', using USER as fallback."
                )
                source_enum = RetrieverType.USER

        node = ProvenanceNode(
            source_retriever=source_enum,
            python_code=n.get("python_code", ""),
            description=n.get("description", ""),
        )
        node.id = n.get("id")
        # parents/children will be restored in step 2
        graph.add_node(node)
        id_to_node[node.id] = node

    # 2. reconnect edges (use add_child which will populate both sides)
    for n in obj.get("nodes", []):
        node = id_to_node.get(n.get("id"))
        if not node:
            continue
        for child_id in n.get("children", []):
            child_node = id_to_node.get(child_id)
            if child_node:
                graph.connect(node, child_node)

    return graph
