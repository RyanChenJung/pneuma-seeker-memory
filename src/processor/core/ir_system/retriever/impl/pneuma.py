from collections import defaultdict
import ast
from enum import Enum
import gc
from math import ceil
import os
from typing import Optional
from bm25s.tokenization import convert_tokenized_to_string_list
import time
import Stemmer
import bm25s
import chromadb_deterministic as chromadb
import pandas as pd
from scipy.spatial.distance import cosine
from torch import cuda

from processor.core.ir_system.ir_data_model import (
    RetrieverType,
    Table,
    TableContext,
    Text,
)
from processor.core.ir_system.ir_data_model import AbstractDocument
from processor.core.ir_system.retriever.abstract_retriever import AbstractRetriever
from tqdm import tqdm
from chromadb_deterministic.api import ClientAPI
from chromadb_deterministic.api.models.Collection import Collection

from processor.model.interface.abstract_model import AbstractModel
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import EmbeddingModelOption, LLMOption


class Pneuma(AbstractRetriever):
    """Represents a tabular data retriever."""

    def __init__(self, models):
        super().__init__(models)
        self.llm = models["llm"]
        self.embed_model = models["embed_model"]
        self.EMBEDDING_MAX_TOKENS = 768
        self.hybrid_retriever = HybridRetriever(
            self.llm,
            RerankingMode.NONE,  # Alternative: RerankingMode.LLM
        )
        self.stemmer = Stemmer.Stemmer("english")
        self.index_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "indices", "pneuma"
        )

    @property
    def retriever_type(self) -> RetrieverType:
        """
        Defines the type of the retriever.
        """
        return RetrieverType.PNEUMA

    def load(self):
        """
        Currently, we do not need to load the retriever's models.
        """
        pass

    def retrieve(
        self, query: str, sources: list[str], k: int
    ) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        retrieval_results: list[AbstractDocument] = []
        increased_k = k * 5
        for dataset in sources:
            client = chromadb.PersistentClient(
                os.path.join(self.index_path, f"vector-index-{dataset}")
            )
            collection = client.get_collection("benchmark")
            retriever = bm25s.BM25.load(
                os.path.join(self.index_path, f"fulltext-index-{dataset}"),
                load_corpus=True,
            )

            dictionary_id_bm25 = dict()
            if retriever.corpus is not None:
                if len(retriever.corpus) < increased_k:
                    print(f"Reducing increased_k from {increased_k} to {len(retriever.corpus)}")
                    increased_k = len(retriever.corpus)
                dictionary_id_bm25 = {
                    datum["metadata"]["table"]: datum_idx
                    for datum_idx, datum in enumerate(retriever.corpus)
                }
            question_embedding = self.embed_model.encode(query)[0].tolist()
            query_tokens = bm25s.tokenize(
                query, stemmer=self.stemmer, show_progress=False
            )

            results, scores = retriever.retrieve(
                query_tokens, k=increased_k, show_progress=False
            )
            bm25_res = (results, scores)
            vec_res = collection.query(
                query_embeddings=[question_embedding], n_results=increased_k
            )

            all_nodes = self.hybrid_retriever.retrieve(
                retriever,
                collection,
                bm25_res,
                vec_res,
                increased_k,
                query,
                0.5,
                query_tokens,
                question_embedding,
                dictionary_id_bm25,
            )
            seen_tables: list[str] = []
            for table, _, _ in all_nodes[:k]:
                table = table.split("_SEP_")[0]

                if table not in seen_tables:
                    seen_tables.append(table)
                else:
                    continue

                retrieval_results.append(
                    Table(
                        doc_id=table[:-4],
                        retriever_type=RetrieverType.PNEUMA,
                        content=pd.read_csv(table),
                        metadata=dict(),
                    )
                )
        return retrieval_results

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever. Assume the documents are
        from a certain dataset only.
        """
        if len(documents) > 0:
            dataset = documents[0].metadata["dataset_name"]
            table_context = [i for i in documents if isinstance(i, TableContext)]
            tables = [i for i in documents if isinstance(i, Table)]

            schema_summaries: list[Text] = self.__get_schema_summaries(
                tables, table_context
            )
            sample_rows: list[Text] = self.__get_sample_rows(tables)

            schema_summaries = self.__split_schema_summaries(schema_summaries)
            sample_rows = self.__merge_sample_rows(sample_rows)
            table_context = self.__merge_table_context(table_context)

            print(f"[VECTOR INDEX] Indexing dataset: {dataset}")
            start = time.time()
            client = chromadb.PersistentClient(
                os.path.join(self.index_path, f"vector-index-{dataset}")
            )
            self.__indexing_vector(
                client, self.embed_model, schema_summaries, sample_rows, table_context
            )
            end = time.time()
            print(f"[VECTOR INDEX] Indexing time: {end-start} seconds")

            print(f"[FULL-TEXT INDEX] Indexing dataset: {dataset}")
            start = time.time()
            stemmer = Stemmer.Stemmer("english")
            self.__indexing_full_text(
                stemmer,
                schema_summaries,
                sample_rows,
                table_context,
                dataset,
            )
            end = time.time()
            print(f"[FULL-TEXT INDEX] Indexing time: {end-start} seconds")

    def __indexing_vector(
        self,
        client: ClientAPI,
        embedding_model: AbstractModel,
        schema_summaries: list[Text],
        sample_rows: list[Text],
        contexts: list[Text] = [],
        collection_name="benchmark",
        reindex=False,
    ):
        if not reindex:
            try:
                collection = client.get_collection(collection_name)
                return collection
            except:
                pass
        try:
            client.delete_collection(collection_name)
        except:
            pass
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:random_seed": 42,
                "hnsw:M": 48,
            },
        )

        documents = []
        ids = []

        if sample_rows is not None:
            tables = sorted({content.metadata["table_name"] for content in sample_rows})
        else:
            tables = sorted(
                {content.metadata["table_name"] for content in schema_summaries}
            )
        for table in tables:
            if schema_summaries is not None:
                table_schema_summaries = [
                    content
                    for content in schema_summaries
                    if content.metadata["table_name"] == table
                ]

                for content_idx, schema_summary in enumerate(table_schema_summaries):
                    documents.append(schema_summary.content)
                    ids.append(f"{table}_SEP_contents_SEP_schema-{content_idx}")

            if sample_rows is not None:
                table_sample_rows = [
                    content
                    for content in sample_rows
                    if content.metadata["table_name"] == table
                ]

                for content_idx, sample_row in enumerate(table_sample_rows):
                    documents.append(sample_row.content)
                    ids.append(f"{table}_SEP_contents_SEP_row-{content_idx}")

            if len(contexts) > 0:
                table_contexts = [
                    context
                    for context in contexts
                    if context.metadata["table_name"] == table
                ]
                for context_idx, context in enumerate(table_contexts):
                    documents.append(context.content)
                    ids.append(f"{table}_SEP_contexts-{context_idx}")

        for i in range(0, len(documents), 30000):
            embeddings = embedding_model.encode(
                documents[i : i + 30000], EmbeddingModelOption(batch_size=100)
            )

            collection.add(
                embeddings=[embed.tolist() for embed in embeddings],
                documents=documents[i : i + 30000],
                ids=ids[i : i + 30000],
            )
        return collection

    def __indexing_full_text(
        self,
        stemmer,
        schema_summaries: list[Text],
        sample_rows: list[Text],
        contexts: list[Text],
        dataset: str,
    ):
        corpus_json = []

        if sample_rows is not None:
            tables = sorted({content.metadata["table_name"] for content in sample_rows})
        else:
            tables = sorted(
                {content.metadata["table_name"] for content in schema_summaries}
            )

        for table in tables:
            if schema_summaries is not None:
                table_schema_summaries = [
                    content
                    for content in schema_summaries
                    if content.metadata["table_name"] == table
                ]

                for content_idx, schema_summary in enumerate(table_schema_summaries):
                    corpus_json.append(
                        {
                            "text": schema_summary.content,
                            "metadata": {
                                "table": f"{table}_SEP_contents_SEP_schema-{content_idx}"
                            },
                        }
                    )

            if sample_rows is not None:
                table_sample_rows = [
                    content
                    for content in sample_rows
                    if content.metadata["table_name"] == table
                ]

                for content_idx, sample_row in enumerate(table_sample_rows):
                    corpus_json.append(
                        {
                            "text": sample_row.content,
                            "metadata": {
                                "table": f"{table}_SEP_contents_SEP_row-{content_idx}"
                            },
                        }
                    )

            if contexts is not None:
                table_contexts = [
                    context
                    for context in contexts
                    if context.metadata["table_name"] == table
                ]
                for context_idx, context in enumerate(table_contexts):
                    corpus_json.append(
                        {
                            "text": context.content,
                            "metadata": {
                                "table": f"{table}_SEP_contexts-{context_idx}"
                            },
                        }
                    )

        corpus_text = [doc["text"] for doc in corpus_json]
        corpus_tokens = bm25s.tokenize(
            corpus_text, stopwords="en", stemmer=stemmer, show_progress=False
        )

        retriever = bm25s.BM25(corpus=corpus_json)
        retriever.index(corpus_tokens, show_progress=True)
        retriever.save(os.path.join(self.index_path, f"fulltext-index-{dataset}"))

    def __get_schema_summaries(
        self, tables: list[Table], table_context: list[TableContext]
    ) -> list[Text]:
        summaries: list[Text] = []
        conversations, conv_tables, conv_cols = self.__parse_tables(
            tables, table_context
        )
        # Still need adjustments; we set the value to 20 for now.
        # optimal_batch_size = self.__get_optimal_batch_size(conversations)
        optimal_batch_size = 20
        sorted_indices = self.__get_special_indices(conversations, optimal_batch_size)

        conversations = [conversations[i] for i in sorted_indices]
        conv_tables = [conv_tables[i] for i in sorted_indices]
        conv_cols = [conv_cols[i] for i in sorted_indices]

        if len(conversations) > 0:
            outputs: list[str] = []
            max_batch_size = optimal_batch_size
            same_batch_size_counter = 0
            for i in tqdm(range(0, len(conversations), max_batch_size)):
                llm_output = self.llm.batch_chat(
                    conversations[i : i + max_batch_size],
                    LLMOption(max_new_tokens=400, batch_size=optimal_batch_size),
                )
                outputs += llm_output[0]

                if llm_output[1] == optimal_batch_size:
                    same_batch_size_counter += 1
                    if same_batch_size_counter % 10 == 0:
                        optimal_batch_size = min(optimal_batch_size + 2, max_batch_size)
                else:
                    optimal_batch_size = llm_output[1]
                    same_batch_size_counter = 0

            col_narrations: dict[str, list[str]] = defaultdict(list)
            for output_idx, output in enumerate(outputs):
                col_narrations[conv_tables[output_idx]] += [
                    f"{conv_cols[output_idx]}: {output}"
                ]

            # Sample code to load created narrations
            # path = os.path.dirname(os.path.abspath(__file__))
            # col_narrations_path = os.path.join(path, "pneuma_col_narrations.txt")
            # with open(col_narrations_path, 'r') as file:
            #     content = file.read()
            #     col_narrations = ast.literal_eval(content)

            for table in tables:
                summaries.append(
                    Text(
                        doc_id=f"{table.metadata['table_name']}_schema_summary",
                        retriever_type=RetrieverType.PNEUMA,
                        content=" | ".join(
                            col_narrations[table.metadata["table_name"]]
                        ),
                        metadata={"table_name": table.metadata["table_name"]},
                    )
                )
        summaries = sorted(summaries, key=lambda x: x.metadata["table_name"])
        return summaries

    def __get_special_indices(self, texts: list[list[LLMMessage]], batch_size: int):
        # Step 1: Sort the conversations (indices) in decreasing order
        sorted_indices = sorted(
            range(len(texts)), key=lambda x: len(texts[x][0]["content"]), reverse=True
        )

        # Step 2: Interleave the indices (longest, shortest, second longest, second shortest, ...)
        final_indices: list[int] = []
        i, j = 0, len(sorted_indices) - 1

        while i <= j:
            if i == j:
                final_indices.append(sorted_indices[i])
                break

            final_indices.append(sorted_indices[i])
            i += 1

            for _ in range(batch_size - 1):
                if i <= j:
                    final_indices.append(sorted_indices[j])
                    j -= 1
                else:
                    break
        return final_indices

    def __is_fit_in_memory(
        self, conversations: list[list[LLMMessage]], batch_size: int
    ):
        special_indices = self.__get_special_indices(conversations, batch_size)
        adjusted_conversations = [conversations[i] for i in special_indices]

        conv_low_idx = len(adjusted_conversations) // 2 - batch_size // 2
        conv_high_idx = conv_low_idx + batch_size

        output = self.llm.batch_chat(
            adjusted_conversations[conv_low_idx:conv_high_idx],
            LLMOption(max_new_tokens=1, batch_size=batch_size),
        )

        cuda.empty_cache()
        gc.collect()

        if output[0] == "":
            del output
            return False
        else:
            del output
            return True

    def __get_optimal_batch_size(self, conversations):
        print("Looking for an optimal batch size")
        max_batch_size = 50  # Change to a higher value if you have more capacity to explore batch size
        min_batch_size = 1
        while min_batch_size < max_batch_size:
            mid_batch_size = (min_batch_size + max_batch_size) // 2
            print(f"Current mid batch size: {mid_batch_size}")
            if self.__is_fit_in_memory(conversations, mid_batch_size):
                min_batch_size = mid_batch_size + 1
            else:
                max_batch_size = mid_batch_size - 1
        optimal_batch_size = min_batch_size
        print(f"Optimal batch size: {optimal_batch_size}")
        return optimal_batch_size

    def __parse_tables(self, tables: list[Table], table_context: list[TableContext]):
        conversations: list[list[LLMMessage]] = []
        conv_tables: list[str] = []
        conv_cols: list[str] = []

        table_names = [i.metadata["table_name"] for i in tables]
        for table in tqdm(table_names):
            try:
                df = pd.read_csv(table, nrows=0)
            except pd.errors.EmptyDataError:
                continue

            table_desc = None
            relevant_table_context = [
                i
                for i in table_context
                if i.metadata["table_name"] == table
                and i.metadata["type"] == "description"
            ]
            if len(relevant_table_context) > 0:
                table_desc = relevant_table_context[0].content

            cols = df.columns
            for col in cols:
                prompt = self.__get_col_description_prompt(
                    table, " | ".join(cols), col, table_desc
                )
                conversations.append(
                    [LLMMessage(role=Role.SYSTEM.value, content=prompt)]
                )
                conv_tables.append(table)
                conv_cols.append(col)
        return conversations, conv_tables, conv_cols

    def __get_col_description_prompt(
        self, table_name: str, columns: str, column: str, table_description: Optional[str] = None
    ):
        if table_description is not None:
            return f"""A table with the name {table_name}, which represents ```{table_description}```, has the following columns:
/*
{columns}
*/
Describe very briefly what the ```{column}``` column represents. Consider the table name as well if relevant to contextualize the description. If not possible, simply state "No description.\""""
        else:
            return f"""A table with the name {table_name} has the following columns:
/*
{columns}
*/
Describe very briefly what the ```{column}``` column represents. Consider the table name as well to contextualize the description. If not possible, simply state "No description.\""""

    def __get_sample_rows(self, tables: list[Table]) -> list[Text]:
        sample_rows: list[Text] = []
        for table_idx, table in enumerate(tqdm(tables)):
            try:
                df = pd.read_csv(
                    table.metadata["table_name"], on_bad_lines="skip", nrows=100
                )
            except pd.errors.EmptyDataError:
                continue
            sample_size = ceil(min(len(df), 5))

            selected_df = df.sample(n=sample_size, random_state=table_idx).reset_index(
                drop=True
            )
            for _, row in selected_df.iterrows():
                formatted_row = " | ".join(
                    [f"{col}: {val}" for col, val in row.items()]
                )
                sample_rows.append(
                    Text(
                        doc_id=f"{table.doc_id}_sample_row",
                        retriever_type=RetrieverType.PNEUMA,
                        content=formatted_row,
                        metadata={"table_name": table.metadata["table_name"]},
                    )
                )
        return sample_rows

    def __split_schema_summaries(self, schema_summaries: list[Text]) -> list[Text]:
        """
        Split schema summaries to fit the constraint of the embedding model.
        """
        processed_schema_summaries: list[Text] = []
        unique_tables = sorted(
            set([summary.metadata["table_name"] for summary in schema_summaries])
        )
        self.embed_model.load_model()
        tokenizer = self.embed_model.model.tokenizer
        for table in tqdm(unique_tables):
            table_schema_summary = [
                summary.content
                for summary in schema_summaries
                if summary.metadata["table_name"] == table
            ][0]
            column_summaries = table_schema_summary.split(" | ")
            col_idx = 0
            while col_idx < len(column_summaries):
                processed_summary = column_summaries[col_idx]

                while (col_idx + 1) < len(column_summaries):
                    temp = processed_summary + " | " + column_summaries[col_idx + 1]
                    if len(tokenizer.encode(temp)) < self.EMBEDDING_MAX_TOKENS:
                        processed_summary = temp
                        col_idx += 1
                    else:
                        break

                col_idx += 1
                processed_schema_summaries.append(
                    Text(
                        doc_id=f"{table}_schema_summaries_{col_idx}",
                        retriever_type=RetrieverType.PNEUMA,
                        content=processed_summary,
                        metadata={"table_name": table},
                    )
                )
        print(f"Num of schema summaries (BEFORE): {len(schema_summaries)}")
        print(f"Num of schema summaries (AFTER): {len(processed_schema_summaries)}")
        return processed_schema_summaries

    def __merge_sample_rows(self, sample_rows: list[Text]) -> list[Text]:
        unique_tables = sorted(set([row.metadata["table_name"] for row in sample_rows]))
        processed_sample_rows: list[Text] = []
        self.embed_model.load_model()
        tokenizer = self.embed_model.model.tokenizer
        for table in tqdm(unique_tables):
            table_rows = [
                row for row in sample_rows if row.metadata["table_name"] == table
            ]

            rows_idx = 0
            while rows_idx < len(table_rows):
                processed_sample_row = table_rows[rows_idx].content

                while (rows_idx + 1) < len(table_rows):
                    temp = (
                        processed_sample_row + " || " + table_rows[rows_idx + 1].content
                    )
                    if len(tokenizer.encode(temp)) < self.EMBEDDING_MAX_TOKENS:
                        processed_sample_row = temp
                        rows_idx += 1
                    else:
                        break

                rows_idx += 1
                processed_sample_rows.append(
                    Text(
                        doc_id=f"{table}_sample_row_{rows_idx}",
                        retriever_type=RetrieverType.PNEUMA,
                        content=processed_sample_row,
                        metadata={"table_name": table},
                    )
                )

        print(f"Num of rows summaries (BEFORE): {len(sample_rows)}")
        print(f"Num of rows summaries (AFTER): {len(processed_sample_rows)}")
        return processed_sample_rows

    def __merge_table_context(self, table_context: list[TableContext]) -> list[Text]:
        unique_tables = sorted(
            set([context.metadata["table_name"] for context in table_context])
        )
        processed_table_context: list[Text] = []
        self.embed_model.load_model()
        tokenizer = self.embed_model.model.tokenizer
        for table in tqdm(unique_tables):
            table_contexts = [
                context
                for context in table_context
                if context.metadata["table_name"] == table
            ]
            context_idx = 0
            while context_idx < len(table_contexts):
                processed_context = table_contexts[context_idx].content
                while (context_idx + 1) < len(table_contexts):
                    temp = (
                        processed_context
                        + " || "
                        + table_contexts[context_idx + 1].content
                    )
                    if len(tokenizer.encode(temp)) < self.EMBEDDING_MAX_TOKENS:
                        processed_context = temp
                        context_idx += 1
                    else:
                        break

                context_idx += 1
                processed_table_context.append(
                    Text(
                        doc_id=f"{table}_context_{context_idx}",
                        retriever_type=RetrieverType.PNEUMA,
                        content=processed_context,
                        metadata={"table_name": table},
                    )
                )
        print(f"Num of context summaries (BEFORE): {len(table_context)}")
        print(f"Num of context summaries (AFTER): {len(processed_table_context)}")
        return processed_table_context


class RerankingMode(Enum):
    NONE = 0
    LLM = 1


class HybridRetriever:

    def __init__(self, reranker: AbstractModel, reranking_mode: RerankingMode) -> None:
        self.reranker = reranker
        self.reranking_mode = reranking_mode

    def _process_nodes_bm25(
        self,
        items,
        all_ids: list,
        dictionary_id_bm25,
        bm25_retriever: bm25s.BM25,
        query_tokens,
    ):
        if bm25_retriever.corpus is None:
            raise ValueError(
                "BM25 retriever corpus is not loaded. Please ensure the corpus is loaded before processing nodes."
            )
        results = [node for node in items[0][0]]
        scores = [node for node in items[1][0]]

        extra_results = [
            bm25_retriever.corpus[dictionary_id_bm25[one_id]] for one_id in all_ids
        ]
        extra_scores = [
            bm25_retriever.get_scores(
                convert_tokenized_to_string_list(query_tokens)[0]
            )[dictionary_id_bm25[one_id]]
            for one_id in all_ids
        ]

        results.extend(extra_results)
        scores.extend(extra_scores)

        max_score = max(scores)
        min_score = min(scores)
        processed_nodes = {
            node["metadata"]["table"]: (
                (
                    1
                    if min_score == max_score
                    else (scores[i] - min_score) / (max_score - min_score)
                ),
                node["text"],
            )
            for i, node in enumerate(results)
        }
        return processed_nodes

    def _process_nodes_vec(
        self, items, missing_ids, collection: Collection, question_embedding
    ):
        extra_information = collection.get_fast(
            ids=missing_ids, limit=len(missing_ids), include=["documents", "embeddings"]
        )
        items["ids"][0].extend(extra_information["ids"])
        items["documents"][0].extend(extra_information["documents"])
        items["distances"][0].extend(
            cosine(question_embedding, extra_information["embeddings"][i])
            for i in range(len(missing_ids))
        )

        scores: list[float] = [1 - dist for dist in items["distances"][0]]
        documents: list[str] = items["documents"][0]
        ids: list[str] = items["ids"][0]

        max_score = max(scores)
        min_score = min(scores)
        processed_nodes = {
            ids[idx]: (
                (
                    1
                    if min_score == max_score
                    else (scores[idx] - min_score) / (max_score - min_score)
                ),
                documents[idx],
            )
            for idx in range(len(scores))
        }
        return processed_nodes

    def _llm_rerank(self, nodes: list[tuple[str, float, str]], question: str):
        # Each node is of the form (name, score, doc)
        node_tables = [node[0] for node in nodes]

        relevance_prompts = [
            [
                LLMMessage(
                    role=Role.USER.value,
                    content=self._get_relevance_prompt(
                        node[2],
                        (
                            "content"
                            if node[0].split("_SEP_")[1].startswith("contents")
                            else "context"
                        ),
                        question,
                    ),
                )
            ]
            for node in nodes
        ]

        arguments = self.reranker.batch_chat(
            relevance_prompts,
            LLMOption(
                max_new_tokens=2,
                batch_size=2,
            ),
        )[0]

        tables_relevance = {
            node_tables[arg_idx]: argument.lower().startswith("yes")
            for arg_idx, argument in enumerate(arguments)
        }

        new_nodes = [
            (table_name, score, doc)
            for table_name, score, doc in nodes
            if tables_relevance[table_name]
        ] + [
            (table_name, score, doc)
            for table_name, score, doc in nodes
            if not tables_relevance[table_name]
        ]
        return new_nodes

    def _get_relevance_prompt(self, desc: str, desc_type: str, question: str):
        if desc_type == "content":
            return f"""Given a table with the following columns:
*/
{desc}
*/
and this question:
/*
{question}
*/
Is the table relevant to answer the question? Begin your answer with yes/no."""
        else:  # Must be context
            return f"""Given this context describing a table:
*/
{desc}
*/
and this question:
/*
{question}
*/
Is the table relevant to answer the question? Begin your answer with yes/no."""

    def retrieve(
        self,
        bm25_retriever: bm25s.BM25,
        vec_retriever,
        bm25_res,
        vec_res,
        k: int,
        question: str,
        alpha=0.5,
        query_tokens=None,
        question_embedding=None,
        dictionary_id_bm25=None,
    ):
        vec_ids = {vec_id for vec_id in vec_res["ids"][0]}
        bm25_ids = {node["metadata"]["table"] for node in bm25_res[0][0]}
        processed_nodes_bm25 = self._process_nodes_bm25(
            bm25_res,
            list(vec_ids - bm25_ids),
            dictionary_id_bm25,
            bm25_retriever,
            query_tokens,
        )
        processed_nodes_vec = self._process_nodes_vec(
            vec_res, list(bm25_ids - vec_ids), vec_retriever, question_embedding
        )

        all_nodes: list[tuple[str, float, str]] = []
        for node_id in sorted(vec_ids | bm25_ids):
            bm25_score_doc = processed_nodes_bm25.get(node_id)
            vec_score_doc = processed_nodes_vec.get(node_id)
            combined_score = alpha * bm25_score_doc[0] + (1 - alpha) * vec_score_doc[0]
            if bm25_score_doc[1] is None:
                doc = vec_score_doc[1]
            else:
                doc = bm25_score_doc[1]
            all_nodes.append((node_id, combined_score, doc))

        sorted_nodes = sorted(all_nodes, key=lambda node: (-node[1], node[0]))[:k]
        if self.reranking_mode == RerankingMode.LLM:
            sorted_nodes = self._llm_rerank(sorted_nodes, question)
        return sorted_nodes
