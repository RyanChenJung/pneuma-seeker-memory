from collections import defaultdict
import gc
from math import ceil
from os import listdir
import time
import Stemmer
import bm25s
import chromadb_deterministic as chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer
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
from chromadb_deterministic.api.client import Client

from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption


class Pneuma(AbstractRetriever):
    """Represents a tabular data retriever."""

    def __init__(self, models):
        super().__init__(models)
        self.llm = models["llm"]
        self.embed_model = models["embed_model"]
        self.EMBEDDING_MAX_TOKENS = 768

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

    def retrieve(self, query: str) -> list[AbstractDocument]:
        """
        Retrieves a list of documents given a query.
        """
        return []

    def index(self, documents: list[AbstractDocument]):
        """
        Indexes a list of documents to the retriever. Assume the documents are
        from a certain dataset only.
        """
        if len(documents) > 0:
            dataset = documents[0].metadata["dataset_name"]
            table_context = [i for i in documents if isinstance(i, TableContext)]
            tables = [i for i in documents if isinstance(i, Table)]

            schema_summaries: list[Text] = self.__get_schema_summaries(tables)
            sample_rows: list[Text] = self.__get_sample_rows(tables)

            schema_summaries = self.__split_schema_summaries(schema_summaries)
            sample_rows = self.__merge_sample_rows(sample_rows)
            table_context = self.__merge_table_context(table_context)

            print(f"[VECTOR INDEX] Indexing dataset: {dataset}")
            start = time.time()
            client = chromadb.PersistentClient(f"indices/pneuma/vector-index-{dataset}")
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
        client: Client,
        embedding_model: SentenceTransformer,
        schema_summaries: list[Text],
        sample_rows: list[Text],
        contexts: list[Text] = None,
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

            if contexts is not None:
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
                documents[i : i + 30000],
                batch_size=100,
                show_progress_bar=True,
                device="cuda",
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
        retriever.save(f"indices/pneuma/fulltext-index-{dataset}")

    def __get_schema_summaries(
        self, tables: list[Table], table_context: list[TableContext]
    ) -> list[Text]:
        summaries: list[Text] = []
        conversations, conv_tables, conv_cols = self.__parse_tables(
            tables, table_context
        )
        optimal_batch_size = self.__get_optimal_batch_size(conversations)
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
                    f"{conv_cols[output_idx]}: {output[-1]["content"]}"
                ]

            for table in tables:
                summaries.append(
                    Text(
                        retriever_type=RetrieverType.PNEUMA,
                        content=" | ".join(col_narrations[table]),
                        metadata={"table_name": table},
                    )
                )
        summaries = sorted(summaries, key=lambda x: x.metadata["table_name"])
        return summaries

    def __get_special_indices(self, texts: list[str], batch_size: int):
        # Step 1: Sort the conversations (indices) in decreasing order
        sorted_indices = sorted(
            range(len(texts)), key=lambda x: len(texts[x]), reverse=True
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
                table_desc = relevant_table_context[0]

            cols = df.columns
            for col in cols:
                prompt = self.__get_col_description_prompt(
                    " | ".join(cols), col, table_desc
                )
                conversations.append([LLMMessage(role=Role.USER, content=prompt)])
                conv_tables.append(table)
                conv_cols.append(col)
        return conversations, conv_tables, conv_cols

    def __get_col_description_prompt(
        self, columns: str, column: str, table_description: str = None
    ):
        if table_description is not None:
            return f"""A table, which represents {table_description}, has the following columns:
/*
{columns}
*/
Describe very briefly what the {column} column represents. If not possible, simply state "No description.\""""
        else:
            return f"""A table has the following columns:
/*
{columns}
*/
Describe very briefly what the {column} column represents. If not possible, simply state "No description.\""""

    def __get_sample_rows(self, tables: list[Table]) -> list[Text]:
        sample_rows: list[Text] = []
        for table_idx, table in enumerate(tqdm(tables)):
            try:
                df = pd.read_csv(table.metadata["table_name"], on_bad_lines="skip")
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
                        retriever_type=RetrieverType.PNEUMA,
                        content=formatted_row,
                        metadata={"table_name": table},
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
        tokenizer = self.embed_model.tokenizer
        for table in tqdm(unique_tables):
            table_schema_summary = [
                summary.content
                for summary in schema_summaries
                if summary.metadata["table"] == table
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
        tokenizer = self.embed_model.tokenizer
        for table in tqdm(unique_tables):
            table_rows = [row for row in sample_rows if row.metadat["table_name"] == table]

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
                        retriever_type=RetrieverType.PNEUMA,
                        content=processed_sample_row,
                        metadata={"table_name": table}
                    )
                )

        print(f"Num of rows summaries (BEFORE): {len(sample_rows)}")
        print(f"Num of rows summaries (AFTER): {len(processed_sample_rows)}")
        return processed_sample_rows

    def __merge_table_context(self, table_context: list[Text]) -> list[Text]:
        unique_tables = sorted(set([context.metadata["table_name"] for context in table_context]))
        processed_table_context: list[Text] = []
        tokenizer = self.embed_model.tokenizer
        for table in tqdm(unique_tables):
            table_contexts = [
                context for context in table_context if context.metadata["table_name"] == table
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
                        retriever_type=RetrieverType.PNEUMA,
                        content=processed_context,
                        metadata={"table_name": table}
                    )
                )
        print(f"Num of context summaries (BEFORE): {len(table_context)}")
        print(f"Num of context summaries (AFTER): {len(processed_table_context)}")
        return processed_table_context
