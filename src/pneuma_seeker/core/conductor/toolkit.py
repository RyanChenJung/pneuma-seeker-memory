from logging import Logger

import duckdb
from pandas import DataFrame

from pneuma_seeker.core.conductor.prompt_factory import ConductorPromptFactory
from pneuma_seeker.core.ir_system.data_model import AbstractDocument, RetrieverType
from pneuma_seeker.core.ir_system.main import IRSystem
from pneuma_seeker.core.materializer.main import Materializer
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.provenance.graph import ProvenanceGraph
from pneuma_seeker.utils.logger import formatted_log


class Toolkit:
    def __init__(
        self,
        llm: AbstractModel,
        embed_model: AbstractModel,
        logger: Logger,
        data_sources: list[str],
        prov_graph: ProvenanceGraph,
        prompt_factory: ConductorPromptFactory,
    ) -> None:
        self.llm = llm
        self.embed_model = embed_model
        self.logger = logger
        self.data_sources = data_sources
        self.prov_graph = prov_graph
        self.prompt_factory = prompt_factory

        self.ir_system = IRSystem(self.llm, self.embed_model, self.logger)
        self.materializer = Materializer(
            self.llm, embed_model, self.logger, self.data_sources, self.prov_graph
        )

    def retrieve_multi_retriever_documents(
        self, prompt: str, k=10, retriever_types: list[RetrieverType] | None = None
    ):
        return self.ir_system.retrieve_multisource_documents(
            prompt,
            self.data_sources,
            k,
            retriever_types,
        )

    def retrieve_documents(self, prompt: str, retriever_type: RetrieverType, k=10):
        return self.ir_system.retrieve_documents(
            retriever_type, prompt, self.data_sources, k
        )

    def materialize_T(
        self,
        T: dict[str, AbstractDocument],
        col_descriptions: dict[str, dict[str, str]],
        Q: list[str],
        user_side_note: str,
        external_data: list[AbstractDocument],
        prefetched_ir_docs: dict[RetrieverType, list[AbstractDocument]],
    ):
        T_dfs: dict[str, DataFrame] = {}
        for T_id, T_doc in T.items():
            T_dfs[T_id] = T_doc.content

        materialized_T_dfs = self.materializer.materialize_T(
            T_dfs,
            col_descriptions,
            Q,
            user_side_note,
            external_data,
            prefetched_ir_docs,
        )

        materialized_T: dict[str, AbstractDocument] = {}
        for T_id, T_df in materialized_T_dfs.items():
            materialized_T[T_id] = T[T_id]
            materialized_T[T_id].content = T_df
        return materialized_T

    def execute_sql(self, T: dict[str, AbstractDocument], Q: list[str]):
        """
        Executes the SQLs (sequentially) over the target schemas.
        """
        with duckdb.connect(database=":memory:") as con:
            tables: dict[str, DataFrame] = {
                T_id: T_doc.content for T_id, T_doc in T.items()
            }

            self.__log(f"Executing these SQL statements on the (materialized) T: {Q}")

            for table_name, df in tables.items():
                con.register(table_name, df)

            results: list[DataFrame] = []
            for sql_idx, sql in enumerate(Q):
                try:
                    self.__log(f"=> ({sql_idx+1}) Executing {sql}")
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

    def __log(self, text):
        formatted_log(self.logger, "CONDUCTOR'S TOOLKIT", text)
