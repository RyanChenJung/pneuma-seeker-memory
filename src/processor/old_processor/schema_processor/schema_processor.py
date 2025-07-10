from tqdm import tqdm

from processor.computation_graph import Node
from processor.conductor_state import ConductorState
from processor.model.message import LLMMessage
from processor.model.option import LLMOption
from processor.model.prompts import schema_processor_prompts
from processor.model.prompts import (
    schema_generator_system_prompt,
    sanity_check_system_prompt,
    overkill_check_prompt,
)
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
        schemas_to_produce=1,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Produces a target schema given a question.

        Args:
            ctx (ConductorState): Conductor state object.
            question (str): The question posed to based the target schema on.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[dict[str,str]]): Computation node consisting of list of strings as the target schema.
        """
        ctx.logger.info(f"Getting target schema for the question {question}")
        messages = [
            {
                "role": "system",
                "content": schema_generator_system_prompt,
            },
            {"role": "user", "content": f"Question: {question}"},
        ]
        target_schemas = []
        for i in range(schemas_to_produce):
            target_schema = ctx.llm.chat(
                messages=messages,
                llm_option=LLMOption(
                    seed=i,
                    do_sample=True,
                    temperature=0.6,
                ),
            )
            ctx.logger.info(f"=> Target schema: {target_schema}")
            try:
                target_schema = parse_code_string(target_schema)
                sanity_check_messages = [
                    {
                        "role": "system",
                        "content": sanity_check_system_prompt,
                    },
                    {
                        "role": "user",
                        "content": f"- Question: ```{question}```\n- Schema and SQL script: ```{target_schema}```",
                    },
                ]
                validated_target_schema = ctx.llm.chat(sanity_check_messages)
                validated_target_schema = parse_code_string(validated_target_schema)
                ctx.logger.info(
                    f"=> [SANITY CHECK] validated target schema: {validated_target_schema}"
                )

                target_schema = validated_target_schema["schema"]
                overkill_sql_check_msg = [
                    {"role": "system", "content": overkill_check_prompt},
                    {
                        "role": "user",
                        "content": f"- Question: ```{question}```\n- Schema: ```{validated_target_schema["schema"]}```\n- SQL Query: ```{validated_target_schema["sql_query"]}```",
                    },
                ]
                overkill_validated = ctx.llm.chat(overkill_sql_check_msg)
                overkill_validated = parse_code_string(overkill_validated)
                ctx.logger.info(
                    f"=> [OVERKILL CHECK] simplified query: {overkill_validated}"
                )

                target_schemas.append(
                    {
                        "schema": target_schema,
                        "reasoning": overkill_validated["reasoning"],
                        "sql_query": overkill_validated["simplified_sql_query"],
                    }
                )
            except ValueError:
                ctx.logger.error("Error encountered during target schema parsing.")
        return ctx.computation_graph.create_node(
            computation_description="Produced target schema(s) for the given question.",
            computation_output=target_schemas,
            input_nodes=input_computation_nodes,
        )

    def get_table_descriptions(
        self,
        ctx: ConductorState,
        db_schema: str,
        num_sampling=3,
        num_sampled_rows=3,
        existing_descriptions: dict[str, str] = dict(),
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Describes all tables within a schema.

        Args:
            ctx (ConductorState): Conductor state object.
            db_schema (str): The db_schema of the tables to be described.
            num_sampling (int): Number of different row samples to consider.
            num_sampled_rows (int): Number of rows to sample for each sampling process.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[dict[str,str]]): Computation node consisting of dictionary of string keys and values as table descriptions.
        """
        table_mapping = ctx.table_store.get_all_tables_in_db_schema(db_schema)
        table_descriptions: dict[str, str] = dict()
        for table_id, table in tqdm(table_mapping.items(), desc="Describing tables"):
            ctx.logger.info(
                "Step 1: Sample rows multiple times to get different perspectives."
            )
            sample_descriptions: list[str] = []
            for i in range(num_sampling):
                system_prompt = schema_processor_prompts["table_descriptor"]
                user_prompt = table.get_representation(
                    num_rows=num_sampled_rows, random_seed=42 + i
                )
                if existing_descriptions.get(table_id):
                    system_prompt = schema_processor_prompts[
                        "table_descriptor_with_initial_description"
                    ]
                    user_prompt = f"- Initial Description: ```{existing_descriptions.get(table_id, '')}```\n- Table Data: {user_prompt}"
                msg: list[LLMMessage] = [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
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
                f"=> Overall description of table '{table_id}': {table_description}"
            )
            table_descriptions[table_id] = table_description

        return ctx.computation_graph.create_node(
            computation_description=f"Described tables in DB schema `{db_schema}`",
            computation_output=table_descriptions,
            input_nodes=input_computation_nodes,
        )

    def get_enhanced_schemas(
        self,
        ctx: ConductorState,
        db_schema: str,
        table_descriptions: dict[str, str],
        num_sampled_rows=3,
        input_computation_nodes: list[Node] = [],
    ) -> Node:
        """
        Enhances table schemas.

        Args:
            ctx (ConductorState): Conductor state object.
            db_schema (str): The db_schema of the tables to be enhanced.
            table_descriptions (str): The descriptions of the tables in `db_schema`.
            num_sampled_rows (int): Number of rows to sample for each sampling process.
            input_computation_nodes (Node): A list of input nodes to keep track of computation.
        Returns:
            Output (Node[dict[str,str]]): Computation node consisting of dictionary of string keys and values as enhanced schemas of the tables.
        """
        results: dict[str, list[str]] = dict()
        table_mapping = ctx.table_store.get_all_tables_in_db_schema(db_schema)

        for table_id, table in table_mapping.items():
            ctx.logger.info(f"Enhancing the schema of table '{table_id}'")
            table_description = table_descriptions[table_id]
            ctx.logger.info(f"=> Table description: {table_description}")
            ctx.logger.info(
                f"=> Schema before enhancement: {table.get_representation(0)}"
            )

            new_columns: list[str] = []
            for col in table.get_schema():
                ctx.logger.info(f"==> Renaming column `{col}`")
                msg: list[LLMMessage] = [
                    {
                        "role": "system",
                        "content": schema_processor_prompts["column_renamer"],
                    },
                    {
                        "role": "user",
                        "content": f"""- Schema: {table.get_representation(num_sampled_rows, 42)}

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

        return ctx.computation_graph.create_node(
            computation_description=f"Enhanced tables in DB schema `{db_schema}`",
            computation_output=results,
            input_nodes=input_computation_nodes,
        )
