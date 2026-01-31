from logging import Logger
from typing import Any

import duckdb
from pandas import DataFrame

from pneuma_seeker.services.core.api.db import DBAPI
from pneuma_seeker.services.core.api.language_model import LanguageModelAPI
from pneuma_seeker.shared.schemas.core.ir_system import (
    AbstractDocument,
    RetrieverType,
)
from pneuma_seeker.services.core.ir_system.main import IRSystem
from pneuma_seeker.services.core.toolkit.implementations.python_executor import PythonExecutor
from pneuma_seeker.services.core.toolkit.implementations.semantic_operator import (
    SemanticOperator,
    SyntacticSimMetric,
)
from pneuma_seeker.services.core.toolkit.implementations.sql_executor import SQLExecutor
from pneuma_seeker.provenance.graph import ProvenanceGraph
from pneuma_seeker.shared.config import Config


class Toolkit:
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
        self.python_executor = PythonExecutor(self.logger)
        self.sql_executor = SQLExecutor()
        self.semantic_operator = SemanticOperator(
            self.config, self.db_api, self.language_model_api
        )

    def retrieve_documents(
        self,
        prompt: str,
        retriever_type: RetrieverType,
        k=10,
        sample_only=False,
        sample_size=None,
    ):
        return self.ir_system.retrieve_documents(
            retriever_type, prompt, k, sample_only, sample_size
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
                                    f"Error encountered when executing this SQL: ```{sql}``` on the target schemas: {e}. Please proceed with internal_reasoning to think what causes the issue (e.g., referencing non-existent tables, non-standard SQL, etc.) and how to fix it."
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
        return self.sql_executor.execute_sql(sql_query, tables)

    def execute_code(self, tables: dict[str, DataFrame], code: str):
        return self.python_executor.execute_code(tables, code)

    def semantic_join(
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
        return self.semantic_operator.semantic_join(
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

    def generate_semantic_column(
        self,
        source_table: DataFrame,
        new_column_name: str,
        instruction: str,  # Explanation includes the possible values, i.e., the domain
    ) -> list[Any]:
        return self.semantic_operator.generate_semantic_column(
            source_table, new_column_name, instruction
        )

    def generate_read_external_tables_code(
        self, table_number: int, doc: AbstractDocument
    ):
        return self.python_executor.generate_read_external_tables_code(
            table_number, doc
        )

    def generate_pandas_read_csv_code(self, doc: AbstractDocument):
        return self.python_executor.generate_pandas_read_csv_code(doc)

    def generate_view_textual_document_code(self, doc: AbstractDocument):
        return self.python_executor.generate_view_textual_document_code(doc)

    def generate_pandas_read_multi_doc_code(self, docs: list[AbstractDocument]):
        return self.python_executor.generate_pandas_read_multi_doc_code(docs)

    def generate_table_select_code(
        self, target_var_name: str, source_id: str, relevant_cols: list[str]
    ):
        return self.python_executor.generate_table_select_code(
            target_var_name, source_id, relevant_cols
        )

    def generate_semantic_col_generator_code(
        self,
        conditioned_cols: list[str],
        doc: AbstractDocument,
        new_col_name: str,
        new_col_values: list[Any],
        path: str,
    ):
        return self.python_executor.generate_semantic_col_generator_code(
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
        return self.python_executor.generate_semantic_join_generator_code(
            doc_1, doc_2, relevant_left_cols, relevant_right_cols, top_k, path
        )

    def append_comment_to_existing_code(self, code: str, comment: str):
        return self.python_executor.append_comment_to_existing_code(code, comment)

    def generate_sql_executor_code(
        self,
        sql_query: str,
        id_dfs: dict[str, DataFrame],
        path: str,
    ):
        return self.python_executor.generate_sql_executor_code(
            sql_query,
            id_dfs,
            path,
        )
