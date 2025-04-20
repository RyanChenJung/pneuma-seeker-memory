# schema_processor.py
from ast import literal_eval

from tqdm import tqdm

from processor.computation_graph import Node
from processor.conductor_state import ConductorState
from processor.models.message import LLMMessage
from processor.models.prompts import schema_processor_prompts
from processor.utils.string_processor import parse_code_string


class SchemaProcessor:
    """
    SchemaProcessor is a core service of Processor. It provides methods for
    producing target schema for a given question and enhancing the schemas of
    tables related to the question (e.g., output of data discovery system).
    """

    def get_target_schema(
        self,
        ctx: ConductorState,
        question: str,
        input_computation_nodes: list[Node] = [],
    ) -> list[str]:
        """
        Produces a target schema given a question.

        Args:
            ctx (ConductorState): Conductor state object.
            question (str): The question posed to based the target schema on.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        """
        ctx.logger.info(f"Getting target schema for the question {question}")
        messages = [
            {
                "role": "system",
                "content": schema_processor_prompts["schema_generator_system_prompt"],
            },
            {"role": "user", "content": f"Question: {question}"},
        ]
        target_schema = ctx.llm.chat(messages=messages)
        ctx.logger.info(f"=> Target schema: {target_schema}")
        try:
            target_schema = parse_code_string(target_schema)
            ctx.computation_graph.create_node(
                computation_description="Produce target schema for the given question.",
                computation_output=target_schema,
                input_nodes=input_computation_nodes,
            )
            return target_schema
        except ValueError:
            ctx.logger.error(
                "Error encountered during target schema parsing, returning `[]`"
            )
            return []

    def get_table_descriptions(
        self,
        ctx: ConductorState,
        schema: str,
        num_sampling=3,
        num_sampled_rows=3,
    ) -> dict[str, str]:
        """
        Describes all tables within a schema.

        - num_sampling (int): Number of different samples to consider.
        - num_sampled_rows (int): Number of rows to sample for each sampling process.
        - redescribe (bool): Redescribe tables that have already been described.
        """
        table_mapping = ctx.table_store.get_all_tables_in_db_schema(schema)
        table_descriptions: dict[str, str] = dict()
        for table_id, table in tqdm(table_mapping.items(), desc="Describing tables"):
            ctx.logger.info(
                "Step 1: Sample rows multiple times to get different perspectives."
            )
            sample_descriptions: list[str] = []
            for i in range(num_sampling):
                msg: list[LLMMessage] = [
                    {
                        "role": "system",
                        "content": schema_processor_prompts["table_descriptor"],
                    },
                    {
                        "role": "user",
                        "content": table.get_representation(
                            num_rows=num_sampled_rows, random_seed=42 + i
                        ),
                    },
                ]
                sample_description = ctx.llm.chat(msg)
                ctx.logger.debug(f"=> Perspective {i+1}: {sample_description}")
                sample_descriptions.append(sample_description)

            ctx.logger.info("Step 2: Combine all perspectives.")
            all_descs = ""
            for j in range(len(sample_descriptions)):
                all_descs += f"Description {j}: {sample_descriptions[j]}\n"
            all_descs = all_descs.strip()
            msg: list[LLMMessage] = [
                {
                    "role": "system",
                    "content": schema_processor_prompts["description_combinator"],
                },
                {"role": "user", "content": all_descs},
            ]
            table_description = ctx.llm.chat(msg)
            ctx.logger.info(
                f"Overall description of table '{table_id}': {table_description}"
            )
            table_descriptions[table_id] = table_description

        return table_descriptions

    def get_enhanced_schemas(
        self,
        ctx: ConductorState,
        schema: str,
        table_descriptions: dict[str, str],
        num_rows=3,
    ) -> dict[str, list[str]]:
        """Enhances table schemas."""
        results: dict[str, list[str]] = []
        table_mapping = ctx.table_store.get_all_tables_in_db_schema(schema)

        for table_id, table in table_mapping.items():
            ctx.logger.info(f"Enhancing schema of table '{table_id}'")
            table_description = table_descriptions[table_id]
            ctx.logger.info(f"=> Table description: {table_description}")
            ctx.logger.info(
                f"=> Schema before enhancement: {table.get_representation(0)}"
            )

            new_columns: list[str] = []
            for col in ctx.table_reader.get_table_schema(table):
                ctx.logger.info(f"==> Renaming column {col}")
                msg: list[LLMMessage] = [
                    {
                        "role": "system",
                        "content": schema_processor_prompts["column_renamer"],
                    },
                    {
                        "role": "user",
                        "content": f"""- Schema: {table.get_representation(num_rows, 42)}

- Description: {table_description}
- Column to be renamed: {col}""",
                    },
                ]

                new_col_name = ctx.llm.chat(msg).split("New column name:")[-1].strip()
                new_col_name = new_col_name.split(":")[0]
                if new_col_name.endswith("\n"):
                    new_col_name = new_col_name.split("\n")[0]
                new_col_name = new_col_name.replace(" ", "_")
                ctx.logger.info(f"==> New column name {new_col_name}")
                new_columns.append(new_col_name)
            results[table_id] = new_columns
        return results
