# services/core/api/db.py
from logging import Logger
from typing import Any

import pandas as pd
from pandas import DataFrame

from pneuma_seeker.provenance.graph import ProvenanceGraph, ProvenanceNode
from pneuma_seeker.services.db.main import PneumaDB
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.core.conductor import InformationNeedState
from pneuma_seeker.shared.schemas.core.ir_system import (
    AbstractDocument,
    RetrieverType,
    Table,
)
from pneuma_seeker.shared.schemas.db.table_type import TableType


class DBAPI:
    """
    DBAPI communicates with DB Service for datasets and workspaces management.
    """

    def __init__(
        self,
        config: Config,
        logger: Logger,
        dataset_db_path: str | None = None,
        workspace_db_path: str | None = None,
    ) -> None:
        self.config = config
        self.logger = logger
        self.pneuma_db = PneumaDB(self.logger, dataset_db_path, workspace_db_path)

    # ------------------------------------------------------------------
    # Dataset Management (one .db per dataset)
    # ------------------------------------------------------------------
    def register_dataset_table(self, dataset_name: str, dataset_path: str):
        """
        Stores CSV files inside the dataset's own DuckDB file.
        - table name = cleaned(Path(csv_file).stem)
        - cleans column names
        - only reads file once for ingestion (fast path)
        """
        self.pneuma_db.register_dataset_table(dataset_name, dataset_path)

    # ------------------------------------------------------------------
    # Register External Tables (from DataFrame)
    # ------------------------------------------------------------------
    def register_external_table(
        self, user_id: str, chat_id: str, table_name: str, df: DataFrame
    ):
        """
        Uploads an external table (DataFrame) into the workspace DB.
        """
        self.pneuma_db.register_external_table(user_id, chat_id, table_name, df)

    def register_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: pd.DataFrame,
    ) -> None:
        """Registers a temporary table in the workspace DB."""
        self.pneuma_db.register_temporary_table(user_id, chat_id, table_name, df)

    def unregister_temporary_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
    ) -> None:
        self.pneuma_db.unregister_temporary_table(user_id, chat_id, table_name)

    def get_tables_of_type_as_dfs(
        self,
        user_id: str,
        chat_id: str,
        table_type: TableType,
        use_sample: bool = False,
        sample_size: int = 5,
    ) -> dict[str, pd.DataFrame]:
        """
        Returns a dictionary of table_name -> DataFrame for all tables of the given type.
        If use_sample is True, returns only a sample of rows from each table.
        """
        return self.pneuma_db.get_tables_of_type_as_dfs(
            user_id, chat_id, table_type, use_sample, sample_size
        )

    # ------------------------------------------------------------------
    # Dataset DB Linking into Workspace DB
    # ------------------------------------------------------------------
    def link_dataset_tables(self, user_id: str, chat_id: str, dataset_name: str):
        """
        Attach a dataset DB into the workspace connection under a safe alias.
        The alias is the cleaned dataset_name.
        This is idempotent (no error if already attached).
        """
        self.pneuma_db.link_dataset_tables(user_id, chat_id, dataset_name)

    # ------------------------------------------------------------------
    # Intermediate & Target Tables Registration
    # ------------------------------------------------------------------
    def register_table(
        self,
        user_id: str,
        chat_id: str,
        table_name: str,
        df: DataFrame,
        table_type: TableType = TableType.INTERMEDIATE,
    ):
        """Stores an intermediate or target result (from pandas DataFrame)."""
        self.pneuma_db.register_table(user_id, chat_id, table_name, df, table_type)

    # ------------------------------------------------------------------
    # Query Execution
    # ------------------------------------------------------------------
    def execute_query(
        self, user_id: str, chat_id: str, sql: str, sql_params: dict = {}
    ) -> DataFrame:
        """
        Execute SQL in the context of the workspace DB connection.
        Note: workspace connection is cached so ATTACH persists between calls.
        """
        return self.pneuma_db.execute_query(user_id, chat_id, sql, sql_params)

    # ------------------------------------------------------------------
    # Execute SELECT query into intermediate table
    # ------------------------------------------------------------------
    def execute_query_into_table(
        self,
        user_id: str,
        chat_id: str,
        query: str,
        dest_table: str,
        sample_size: int = 5,
        table_type: TableType = TableType.INTERMEDIATE,
    ) -> DataFrame:
        """
        Executes a SQL SELECT query, saves its result into dest_table (overwriting if exists),
        and returns sample rows of the resulting table.

        For safety, `query` must start with SELECT (simple heuristic).
        """
        return self.pneuma_db.execute_query_into_table(
            user_id,
            chat_id,
            query,
            dest_table,
            sample_size,
            table_type,
        )

    # ------------------------------------------------------------------
    # Delete all tables of a specific type in workspace
    # ------------------------------------------------------------------
    def delete_all_tables_of_type(
        self, user_id: str, chat_id: str, table_type: TableType
    ):
        """
        Deletes all tables of the given table_type in a workspace DB, and
        removes the corresponding metadata entries.
        Returns number of tables removed (metadata rows).
        """
        return self.pneuma_db.delete_all_tables_of_type(user_id, chat_id, table_type)

    # ------------------------------------------------------------------
    # State Persistence (info_need_state, retrieved_tables, provenance graph)
    # ------------------------------------------------------------------
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
        Saves the chat state into the chat_state table (overwrites previous).
        """

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
        info_need_state_json = {
            "T": serialized_T,
            "is_T_materialized": info_need_state.is_T_materialized,
            "column_descriptions": info_need_state.column_descriptions,
            "S": info_need_state.S,
            "is_S_executed": info_need_state.is_S_executed,
        }

        retrieved_tables_json = [
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

        provenance_graph_json = self.__serialize_provenance_graph(provenance_graph)

        self.pneuma_db.save_state(
            user_id,
            chat_id,
            info_need_state_json,
            retrieved_tables_json,
            enumerated_table_ids,
            provenance_graph_json,
        )

    def __serialize_provenance_graph(self, graph: ProvenanceGraph) -> dict[str, Any]:
        """Serializes the ProvenanceGraph into a JSON-serializable dictionary."""
        nodes = [
            {
                "id": node.id,
                "source_retriever": getattr(
                    node.source_retriever, "value", str(node.source_retriever)
                ),
                "python_code": node.python_code,
                "description": node.description,
                "parents": [parent.id for parent in node.parents],
                "children": [child.id for child in node.children],
            }
            for node in graph.nodes.values()
        ]

        return {"nodes": nodes, "meta": {"node_count": len(nodes)}}

    def load_state(
        self,
        user_id: str,
        chat_id: str,
    ) -> tuple[
        InformationNeedState, list[AbstractDocument], list[str], ProvenanceGraph
    ]:
        """
        Loads the latest chat state from the chat_state table.
        Returns (info_need_state, retrieved_tables, enumerated_table_ids, provenance_graph).
        If no state is found, returns empty structures.
        """
        self.link_dataset_tables(user_id, chat_id, self.config.DATA_SOURCES[0])

        state_data, retr_data, enumerated_table_ids, prov_data = (
            self.pneuma_db.load_state(user_id, chat_id)
        )

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

            # Always re-fetch table from workspace DB
            content = self.execute_query(
                user_id,
                chat_id,
                f'SELECT * FROM {self.config.DATA_SOURCES[0]}."{T_id}";',
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
        info_state.S = state_data.get("S", "")
        info_state.is_S_executed = state_data.get("is_S_executed", False)

        # ---- rebuild retrieved tables ----
        retrieved_tables: list[AbstractDocument] = []

        for doc in retr_data:
            content = self.execute_query(
                user_id,
                chat_id,
                f'SELECT * FROM "{self.config.DATA_SOURCES[0]}"."{doc["doc_id"]}";',
            )

            retrieved_tables.append(
                Table(
                    doc_id=doc.get("doc_id", ""),
                    retriever_type=RetrieverType.PNEUMA_RETRIEVER,
                    content=content,
                    metadata=doc.get("metadata", {}),
                    path=doc.get("path"),
                    last_node_id=doc.get("last_node_id"),
                )
            )

        provenance_graph = self.__deserialize_provenance_graph(prov_data)
        return info_state, retrieved_tables, enumerated_table_ids, provenance_graph

    def __deserialize_provenance_graph(self, obj: dict[str, Any]) -> ProvenanceGraph:
        if not obj or not obj.get("nodes"):
            self.logger.info(
                "[PERSISTENCE] No provenance nodes found in serialized data; initializing default root graph."
            )
            return ProvenanceGraph(self.logger)

        graph = ProvenanceGraph(self.logger, create_default_root=False)
        id_to_node: dict[str, ProvenanceNode] = {}

        # 1. create all nodes first
        for n in obj.get("nodes", []):
            # Recreate RetrieverType from the canonical Enum defined in ir_system schemas
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
