# core_service/api/db.py
import json
from enum import Enum
from logging import Logger
from typing import Any

import pandas as pd
import requests
from shared.config.settings import Config
from shared.provenance.provenance_graph import ProvenanceGraph, ProvenanceNode
from shared.schemas.core.conductor import InformationNeedState
from shared.schemas.core.ir_system import AbstractDocument, RetrieverType, Table
from shared.schemas.db.table_type import TableType
from shared.utils.table_reader import df_to_table_preview, table_preview_to_df


class DBAPI:
    """API client for interacting with the DB Service."""

    def __init__(self, config: Config, logger: Logger) -> None:
        self.config = config
        self.logger = logger

    def load_state(
        self,
        user_id: str,
        chat_id: str,
        dataset_name: str,
    ) -> tuple[
        InformationNeedState,
        list[AbstractDocument],
        list[str],
        ProvenanceGraph,
    ]:
        """
        Loads state from DB service and fully rehydrate domain objects.
        """

        r = requests.get(
            f"{self.config.DB_SERVICE_URL}/workspace/state",
            params={"user_id": user_id, "chat_id": chat_id},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        if not data or not data.get("info_need_state"):
            return InformationNeedState(), [], [], ProvenanceGraph(self.logger)

        state_data: dict[str, Any] = data["info_need_state"]
        retr_data: list[dict[str, Any]] = data["retrieved_tables"]
        prov_data: dict[str, Any] = data["provenance_graph"]
        enumerated_table_ids: list[str] = data.get("enumerated_table_ids", [])

        info_state = InformationNeedState()

        # ---- rebuild T ----
        raw_T: dict[str, dict[str, Any]] = state_data.get("T", {})
        T: dict[str, AbstractDocument] = {}

        for T_id, T_dict in raw_T.items():
            doc_id = T_dict.get("doc_id", "")
            retriever_type = RetrieverType(
                T_dict.get("retriever_type", RetrieverType.PNEUMA_RETRIEVER.value)
            )
            path = T_dict.get("path", "") or ""
            last_node_id = T_dict.get("last_node_id")

            # Always re-fetch table preview from workspace DB
            content = self.execute_query(
                user_id, chat_id, f'SELECT * FROM "{T_id}" LIMIT 5;'
            )

            if content is None:
                self.logger.info(
                    f"[PERSISTENCE] Skipping T entry {T_id} (no valid content)."
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

        # ---- rebuild retrieved tables ----
        retrieved_tables: list[AbstractDocument] = []

        self.link_dataset_tables(user_id, chat_id, dataset_name)

        for doc in retr_data:
            content = self.execute_query(
                user_id,
                chat_id,
                f'SELECT * FROM "{dataset_name}"."{doc["doc_id"]}" LIMIT 5;',
            )

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

        provenance_graph = self._deserialize_provenance_graph(prov_data)

        return info_state, retrieved_tables, enumerated_table_ids, provenance_graph

    def save_state(
        self,
        user_id: str,
        chat_id: str,
        info_need_state: InformationNeedState,
        retrieved_tables: list[AbstractDocument],
        enumerated_table_ids: list[str],
        provenance_graph: ProvenanceGraph,
    ):
        """
        Serialize complex domain state and persist via DB service.
        """

        def serializable_content(content):
            if content is None:
                return None
            if isinstance(content, pd.DataFrame):
                return content.to_dict(orient="records")
            return content

        # ---- serialize T ----
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

        info_need_state_payload = {
            "T": serialized_T,
            "is_T_materialized": info_need_state.is_T_materialized,
            "column_descriptions": info_need_state.column_descriptions,
            "S": info_need_state.S,
            "is_S_executed": info_need_state.is_S_executed,
        }

        retrieved_tables_payload = [
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

        provenance_graph_payload = self._serialize_provenance_graph(provenance_graph)

        payload = {
            "info_need_state": info_need_state_payload,
            "retrieved_tables": retrieved_tables_payload,
            "enumerated_table_ids": enumerated_table_ids,
            "provenance_graph": provenance_graph_payload,
        }
        json_payload = json.dumps(payload, default=self._serialize)
        r = requests.post(
            f"{self.config.DB_SERVICE_URL}/workspace/state",
            params={"user_id": user_id, "chat_id": chat_id},
            data=json_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()

    def _serialize_provenance_graph(self, graph: ProvenanceGraph) -> dict[str, Any]:
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

    def _deserialize_provenance_graph(self, obj: dict[str, Any]) -> ProvenanceGraph:
        if not obj or not obj.get("nodes"):
            self.logger.info(
                "[PERSISTENCE] No provenance nodes found in serialized data; initializing default root graph."
            )
            return ProvenanceGraph(self.logger)

        graph = ProvenanceGraph(self.logger, create_default_root=False)
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
                    self.logger.warning(
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

    def _serialize(self, obj):
        if obj is None:
            return None

        if isinstance(obj, Enum):
            return obj.value

        return str(obj)

    def execute_query(
        self,
        user_id: str,
        chat_id: str,
        sql: str,
        sample_size: int = 5,
        query_params: dict[str, Any] = {},
    ) -> pd.DataFrame:
        for key in query_params:
            if isinstance(query_params[key], pd.DataFrame):
                query_params[key] = df_to_table_preview(
                    table_name=key, df=query_params[key]
                )
        r = requests.post(
            f"{self.config.DB_SERVICE_URL}/workspace/query",
            params={"user_id": user_id, "chat_id": chat_id},
            json={
                "sql": sql,
                "query_params": query_params,
                "sample_size": sample_size,
            },
            timeout=10,
        )
        r.raise_for_status()

        preview = r.json()
        return table_preview_to_df(preview)

    def register_external_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: pd.DataFrame,
    ):
        table_preview = df_to_table_preview(table_name, df)

        r = requests.post(
            f"{self.config.DB_SERVICE_URL}/workspace/tables/register",
            params={"user_id": user_id, "chat_id": chat_id},
            json={
                "table_name": table_name,
                "table_type": TableType.EXTERNAL.value,
                "table": table_preview.model_dump(),
            },
            timeout=10,
        )
        r.raise_for_status()

    def register_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: pd.DataFrame,
        table_type: TableType = TableType.INTERMEDIATE,
    ):
        table_preview = df_to_table_preview(table_name, df)

        r = requests.post(
            f"{self.config.DB_SERVICE_URL}/workspace/tables/register",
            params={"user_id": user_id, "chat_id": chat_id},
            json={
                "table_name": table_name,
                "table_type": table_type.value,
                "table": table_preview.model_dump(),
            },
            timeout=10,
        )
        r.raise_for_status()

    def register_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: pd.DataFrame,
    ):
        table_preview = df_to_table_preview(table_name, df)

        r = requests.post(
            f"{self.config.DB_SERVICE_URL}/workspace/tables/temporary",
            params={"user_id": user_id, "chat_id": chat_id},
            json={
                "table_name": table_name,
                "table": table_preview.model_dump(),
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def unregister_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
    ):
        r = requests.delete(
            f"{self.config.DB_SERVICE_URL}/workspace/tables/temporary/{table_name}",
            params={"user_id": user_id, "chat_id": chat_id},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def delete_tables_of_type(
        self,
        user_id: str,
        chat_id: str,
        table_type: TableType,
    ):
        r = requests.delete(
            f"{self.config.DB_SERVICE_URL}/workspace/tables/by-type",
            params={
                "user_id": user_id,
                "chat_id": chat_id,
                "table_type": table_type.value,
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def execute_query_into_table(
        self,
        user_id: str,
        chat_id: str,
        query: str,
        dest_table: str,
        sample_size: int = 5,
        table_type: TableType = TableType.INTERMEDIATE,
    ) -> pd.DataFrame:
        r = requests.post(
            f"{self.config.DB_SERVICE_URL}/workspace/query/into-table",
            params={"user_id": user_id, "chat_id": chat_id},
            json={
                "sql": query,
                "dest_table": dest_table,
                "sample_size": sample_size,
                "table_type": table_type.value,
            },
            timeout=10,
        )
        r.raise_for_status()

        preview = r.json()
        return table_preview_to_df(preview)

    def link_dataset_tables(
        self,
        user_id: str,
        chat_id: str,
        dataset_name: str,
    ):
        r = requests.post(
            f"{self.config.DB_SERVICE_URL}/datasets/{dataset_name}/link",
            params={"user_id": user_id, "chat_id": chat_id},
            timeout=10,
        )
        r.raise_for_status()
