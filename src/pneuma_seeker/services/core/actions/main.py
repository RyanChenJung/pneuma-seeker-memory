from logging import Logger
from typing import Any

import duckdb
from pandas import DataFrame

from pneuma_seeker.provenance.provenance_helper import (
    append_comment_to_existing_code,
    generate_pandas_read_csv_code,
    generate_pandas_read_multi_doc_code,
    generate_read_external_tables_code,
    generate_semantic_col_generator_code,
    generate_semantic_join_generator_code,
    generate_sql_executor_code,
    generate_table_select_code,
    generate_view_textual_document_code,
)
from pneuma_seeker.services.core.actions.executors.python_executor import PythonExecutor
from pneuma_seeker.services.core.actions.operators.semantic_column_generation import (
    SemanticColumnGeneration,
)
from pneuma_seeker.services.core.actions.operators.semantic_join import (
    SemanticJoin,
    SyntacticSimMetric,
)
from pneuma_seeker.services.core.actions.executors.sql_executor import SQLExecutor
from pneuma_seeker.services.core.actions.operators.table_projection import (
    TableProjection,
)
from pneuma_seeker.services.core.actions.retrievers.join_path_extraction import (
    JoinPathExtraction,
)
from pneuma_seeker.services.core.actions.retrievers.table_enumeration import (
    TableEnumeration,
)
from pneuma_seeker.services.core.actions.retrievers.table_retrieve import TableRetrieve
from pneuma_seeker.services.core.actions.retrievers.web_crawl import WebCrawl
from pneuma_seeker.services.core.actions.retrievers.web_search import WebSearch
from pneuma_seeker.services.core.api.db import DBAPI
from pneuma_seeker.services.core.api.language_model import LanguageModelAPI
from pneuma_seeker.shared.schemas.core.ir_system import (
    AbstractDocument,
    RetrieverType,
)
from pneuma_seeker.services.core.ir_system.main import IRSystem
from pneuma_seeker.provenance.graph import ProvenanceGraph
from pneuma_seeker.shared.config import Config


class ActionSet:
    def __init__(
        self,
        config: Config,
        logger: Logger,
        prov_graph: ProvenanceGraph,
        db_api: DBAPI,
        language_model_api: LanguageModelAPI,
    ) -> None:
        self.config = config
        self.logger = logger
        self.prov_graph = prov_graph
        self.db_api = db_api
        self.language_model_api = language_model_api

        self.ir_system = IRSystem(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.table_retrieve = TableRetrieve(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.table_enumeration = TableEnumeration(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.web_search = WebSearch(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.web_crawl = WebCrawl(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.join_path_extraction = JoinPathExtraction(
            self.config, self.logger, self.db_api, self.language_model_api
        )

        self.python_executor = PythonExecutor(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.sql_executor = SQLExecutor(
            self.config, self.logger, self.db_api, self.language_model_api
        )

        self.semantic_join = SemanticJoin(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.semantic_column_generation = SemanticColumnGeneration(
            self.config, self.logger, self.db_api, self.language_model_api
        )
        self.table_projection = TableProjection(
            self.config, self.logger, self.db_api, self.language_model_api
        )

    def retrieve_documents(
        self,
        prompt: str,
        retriever_type: RetrieverType,
        k=10,
        sample_only=False,
        sample_size=None,
    ) -> list[AbstractDocument]:
        return self.ir_system.retrieve_documents(
            retriever_type, prompt, k, sample_only, sample_size
        )

    def retrieve_multi_topic_documents(
        self,
        prompts: list[str],
        retriever_type: RetrieverType,
        k=10,
        sample_only=False,
        sample_size=None,
    ) -> list[AbstractDocument]:
        multi_topic_docs: dict[str, list[AbstractDocument]] = (
            self.ir_system.retrieve_multi_topic_documents(
                retriever_type, prompts, k, sample_only, sample_size
            )
        )

        aggregated_docs: list[AbstractDocument] = []
        for topic, docs in multi_topic_docs.items():
            for doc in docs:
                doc.metadata["topic"] = topic
            aggregated_docs.extend(docs)
        return aggregated_docs

    def discover_join_paths(self, tables: list[AbstractDocument]) -> str:
        tables_df: dict[str, DataFrame] = {doc.doc_id: doc.content for doc in tables}
        return self.join_path_extraction.discover_join_paths(tables_df)

    def project_table(self, table: DataFrame, relevant_columns: list[str]) -> DataFrame:
        return self.table_projection.apply(
            {
                "table": table,
                "relevant_columns": relevant_columns,
            }
        )

    def execute_sql(self, T: dict[str, AbstractDocument], Q: list[str]):
        """
        Executes the SQLs (sequentially) over the target schemas.
        """
        with duckdb.connect(database=":memory:") as con:
            tables: dict[str, DataFrame] = {
                T_id: T_doc.content for T_id, T_doc in T.items()
            }

            for table_name, df in tables.items():
                con.register(table_name, df)

            results: list[DataFrame] = []
            for sql_idx, sql in enumerate(Q):
                try:
                    result = con.execute(sql).fetchdf()
                    results.append(result)
                except Exception as e:
                    results = [
                        DataFrame(
                            columns=["error"],
                            data=[
                                [
                                    f"Error encountered when executing this SQL: ```{sql}``` on the target schemas: {e}."
                                ]
                            ],
                        )
                    ]
                    print(e)
                    break

            final_output: list[str] = []
            for result in results:
                if result.shape == (1, 1):
                    final_output.append(str(result.iat[0, 0]))
                else:
                    final_output.append(str(result))
            return final_output

    def execute_sql_df(self, sql_query: str, tables: dict[str, DataFrame]):
        return self.sql_executor.execute({"sql_query": sql_query, "tables": tables})

    def execute_code(self, tables: dict[str, DataFrame], code: str):
        return self.python_executor.execute({"tables": tables, "code": code})

    def extract_table_ids_from_code(self, code: str) -> list[str]:
        return self.python_executor.extract_table_ids(code)

    def extract_table_ids_from_sql(self, sql_query: str) -> list[str]:
        return self.sql_executor.extract_table_ids(sql_query)

    def join_semantic(
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
        return self.semantic_join.apply(
            {
                "left_df": left_df,
                "right_df": right_df,
                "left_cols": left_cols,
                "right_cols": right_cols,
                "alpha": alpha,
                "top_k": top_k,
                "delimiter": delimiter,
                "embed_batch_size": embed_batch_size,
                "syntactic_sim_metric": syntactic_sim_metric,
                "use_llm": use_llm,
            }
        )

    def generate_semantic_column(
        self,
        source_table: DataFrame,
        new_column_name: str,
        instruction: str,  # Explanation includes the possible values, i.e., the domain
    ) -> DataFrame:
        return self.semantic_column_generation.apply(
            {
                "table": source_table,
                "column_name": new_column_name,
                "description": instruction,
            }
        )

    def generate_read_external_tables_code(
        self, table_number: int, doc: AbstractDocument
    ):
        return generate_read_external_tables_code(table_number, doc)

    def generate_pandas_read_csv_code(self, doc: AbstractDocument):
        return generate_pandas_read_csv_code(doc)

    def generate_view_textual_document_code(self, doc: AbstractDocument):
        return generate_view_textual_document_code(doc)

    def generate_pandas_read_multi_doc_code(self, docs: list[AbstractDocument]):
        return generate_pandas_read_multi_doc_code(docs)

    def generate_table_select_code(
        self, target_var_name: str, source_id: str, relevant_cols: list[str]
    ):
        return generate_table_select_code(target_var_name, source_id, relevant_cols)

    def generate_semantic_col_generator_code(
        self,
        conditioned_cols: list[str],
        doc: AbstractDocument,
        new_col_name: str,
        new_col_values: list[Any],
        path: str,
    ):
        return generate_semantic_col_generator_code(
            conditioned_cols, doc, new_col_name, new_col_values, path
        )

    def generate_semantic_join_generator_code(
        self,
        doc_1: AbstractDocument,
        doc_2: AbstractDocument,
        relevant_left_cols: list[str],
        relevant_right_cols: list[str],
        top_k: int,
        path: str,
    ):
        return generate_semantic_join_generator_code(
            doc_1, doc_2, relevant_left_cols, relevant_right_cols, top_k, path
        )

    def append_comment_to_existing_code(self, code: str, comment: str):
        return append_comment_to_existing_code(code, comment)

    def generate_sql_executor_code(
        self,
        sql_query: str,
        id_dfs: dict[str, DataFrame],
        path: str,
    ):
        return generate_sql_executor_code(
            sql_query,
            id_dfs,
            path,
        )
