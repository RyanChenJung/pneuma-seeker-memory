import datetime
import json
import os

from logging import Logger
from typing import Any

import duckdb
import pandas as pd

from pneuma_seeker.core.conductor.main import (
    AbstractDocument,
    InformationNeedState,
    RetrieverType,
)
from pneuma_seeker.core.ir_system.data_model import Table
from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.utils.str_processor import clean_column_table_name

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pneuma_seeker.duckdb"
)


def init_db():
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_state (
        user_id TEXT,
        chat_id TEXT,
        info_need_state_json TEXT,
        retrieval_results_json TEXT,
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
    retrieval_results: dict[RetrieverType, list[AbstractDocument]],
    enumerated_table_ids: list[str],
    provenance_graph: ProvenanceGraph,
):
    """
    Persists info_need_state and retrieval_results as JSON.
    """
    serialized_T = {
        doc_id: {
            "doc_id": doc.doc_id,
            "retriever_type": doc.retriever_type.value,
            "content": None if doc.path else doc.content,
            "metadata": doc.metadata,
            "path": doc.path,
            "last_node_id": doc.last_node_id,
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

    retrieval_results_json = json.dumps(
        {
            rt.value: [
                {
                    "doc_id": doc.doc_id,
                    "retriever_type": doc.retriever_type.value,
                    "content": None if doc.path else doc.content,
                    "metadata": doc.metadata,
                    "path": doc.path,
                    "last_node_id": doc.last_node_id,
                }
                for doc in docs
            ]
            for rt, docs in retrieval_results.items()
        }
    )

    provenance_graph_json = json.dumps(_serialize_provenance_graph(provenance_graph))

    con = duckdb.connect(DB_PATH)
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
            retrieval_results_json,
            provenance_graph_json,
            ts
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            chat_id,
            info_need_state_json,
            retrieval_results_json,
            provenance_graph_json,
            datetime.datetime.now(datetime.timezone.utc),
        ),
    )
    con.close()


def load_state(user_id: str, chat_id: str, logger: Logger) -> tuple[
    InformationNeedState,
    dict[RetrieverType, list[AbstractDocument]],
    list[str],
    ProvenanceGraph,
]:
    con = duckdb.connect(DB_PATH)
    row = con.execute(
        """
        SELECT info_need_state_json, retrieval_results_json, provenance_graph_json
        FROM chat_state
        WHERE user_id = ? AND chat_id = ?
        ORDER BY ts DESC
        LIMIT 1
        """,
        (user_id, chat_id),
    ).fetchone()
    con.close()

    if not row:
        return InformationNeedState(), {}, [], ProvenanceGraph(logger)

    state_json, retr_json, prov_json = row
    state_data: dict[str, Any] = json.loads(state_json)
    retr_data: dict[str, list[dict[str, Any]]] = json.loads(retr_json)
    prov_data = json.loads(prov_json)

    info_state = InformationNeedState()

    enumerated_table_ids: list[str] = state_data.get("enumerated_table_ids", [])

    raw_T: dict[str, dict[str, Any]] = state_data.get("T", {})
    T: dict[str, AbstractDocument] = {}
    for T_id, T_dict in raw_T.items():
        doc_id: str = T_dict.get("doc_id", "")
        retriever_type = RetrieverType(
            T_dict.get("retriever_type", RetrieverType.PNEUMA.value)
        )
        path: str = T_dict.get("path", "")
        if len(path) == 0 or not os.path.isfile(path):
            continue
        content = pd.read_csv(path)
        metadata: dict[str, str] = T_dict.get("metadata", {})
        last_node_id: str | None = T_dict.get("last_node_id", None)

        T[T_id] = Table(
            doc_id=doc_id,
            retriever_type=retriever_type,
            content=content,
            metadata=metadata,
            path=path,
            last_node_id=last_node_id,
        )

    info_state.T = T
    info_state.is_T_materialized = state_data.get("is_T_materialized", False)
    info_state.column_descriptions = state_data.get("column_descriptions", {})
    info_state.S = state_data.get("S", [])
    info_state.is_S_executed = state_data.get("is_S_executed", False)

    retrieval_results: dict[RetrieverType, list[AbstractDocument]] = {}
    for retriever_type, docs in retr_data.items():
        retriever_type = RetrieverType(retriever_type)
        retrieval_results[retriever_type] = []
        for doc in docs:
            content = None
            if doc.get("path"):
                try:
                    content = pd.read_csv(doc["path"])
                    content.rename(columns=clean_column_table_name, inplace=True)
                except Exception:
                    continue
            else:
                content = doc.get("content", "")
            retrieval_results[retriever_type].append(
                AbstractDocument(
                    doc_id=doc["doc_id"],
                    retriever_type=retriever_type,
                    content=content,
                    metadata=doc["metadata"],
                    path=doc.get("path"),
                    last_node_id=doc.get("last_node_id"),
                )
            )

    provenance_graph = _deserialize_provenance_graph(prov_data, logger)

    return info_state, retrieval_results, enumerated_table_ids, provenance_graph


def _serialize_provenance_graph(graph: ProvenanceGraph) -> dict[str, Any]:
    return {
        "nodes": [
            {
                "id": node.id,
                "source_retriever": node.source_retriever.value,
                "python_code": node.python_code,
                "children": [child.id for child in node.children],
                "parents": [parent.id for parent in node.parents],
            }
            for node in graph.nodes.values()
        ]
    }


def _deserialize_provenance_graph(
    obj: dict[str, Any], logger: Logger
) -> ProvenanceGraph:
    if not obj:
        return ProvenanceGraph(logger)

    graph = ProvenanceGraph(logger)
    id_to_node: dict[str, ProvenanceNode] = {}

    # 1. create all nodes first
    for n in obj.get("nodes", []):
        node = ProvenanceNode(
            source_retriever=RetrieverType(n["source_retriever"]),
            python_code=n["python_code"]
        )
        node.id = n["id"]
        graph.add_node(node)
        id_to_node[node.id] = node

    # 2. reconnect edges
    for n in obj.get("nodes", []):
        node = id_to_node[n["id"]]
        for child_id in n.get("children", []):
            if child_id in id_to_node:
                node.add_child(id_to_node[child_id])

    return graph
