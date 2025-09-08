from typing import Any

from logging import Logger
from pandas import DataFrame
from pneuma_seeker.core.ir_system.data_model import AbstractDocument, RetrieverType, Table
from pneuma_seeker.core.materializer.operation.semantic_column_generator import (
    SemanticColumnGenerator,
)
from pneuma_seeker.core.materializer.operation.semantic_joiner import SemanticJoiner, SyntacticSimMetric
from pneuma_seeker.core.materializer.prompt_factory import MaterializerPromptFactory
from pneuma_seeker.core.materializer.state import MaterializerState
from pneuma_seeker.core.materializer.operation.table_enumerator import table_enumerator
from pneuma_seeker.core.materializer.operation.document_retriever import (
    get_documents,
)
from pneuma_seeker.core.materializer.operation.operation_description import (
    get_operation_description,
)
from pneuma_seeker.core.materializer.operation.python_executor import (
    execute_python_code,
)
from pneuma_seeker.core.materializer.operation.sql_executor import execute_sql
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.utils.parser import parse_code, parse_json


class Materializer:
    def __init__(
        self,
        llm: AbstractModel,
        logger: Logger,
        embed_model: AbstractModel,
        data_sources: list[str],
    ):
        self.logger = logger
        self.logger.info("Initializing Materializer")
        self.llm = llm
        self.embed_model = embed_model

        self.prompt_factory = MaterializerPromptFactory()
        self.state = MaterializerState()

        self.semantic_joiner = SemanticJoiner(self.llm, self.embed_model)
        self.semantic_col_generator = SemanticColumnGenerator(self.llm, 20) # Try 20

        self.actions: list[str] = []
        self.data_sources = data_sources

        self.is_sql_alignment_checked = False

    def __cleanup_system(self):
        self.state.reset()
        self.is_sql_alignment_checked = False
        self.actions = []

    def materialize_target_schemas(
        self,
        target_schemas: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        sqls: list[str],
        user_side_note="",
        external_data: list[AbstractDocument] = [],
    ) -> dict[str, DataFrame]:
        self.logger.info(
            f"Starting materialization for {len(target_schemas)} tables with {len(sqls)} SQL queries"
        )
        self.__cleanup_system()
        sys_prompt = LLMMessage(
            role=Role.SYSTEM.value,
            content=self.prompt_factory.get_planning_prompt(
                target_schemas=target_schemas,
                column_descriptions=column_descriptions,
                sqls=sqls,
                operation_description=get_operation_description(),
            ),
        )

        num_iterations = 0
        llm_messages = [sys_prompt]
        while not self.__check_completion(target_schemas):
            self.logger.info("Planning next materialization step")
            self.logger.info("Requesting LLM response for plan")
            llm_messages.append(
                LLMMessage(
                    role=Role.USER.value,
                    content=self.prompt_factory.get_context_prompt(
                        self.state.current_retrieved_documents,
                        self.state.intermediate_tables,
                        self.actions,
                        num_iterations,
                        user_side_note,
                        external_data,
                    ),
                )
            )

            num_iterations += 1
            response = self.llm.chat(llm_messages, LLMOption(json_mode=True))
            response = "".join(response)
            llm_messages.append(
                LLMMessage(
                    role=Role.ASSISTANT.value,
                    content=response,
                )
            )
            self.logger.info(f"LLM response: {response}")
            """
            Output format:
            {{
                "step_type": "operation" | "internal_reasoning",
                "message": null (if step_type is "operation") | <"Reflect out loud (for yourself only)">
                "name": null (if step_type is "internal_reasoning") | "Operation name",
                "args": null (if step_type is "internal_reasoning") | {{"The argument to the operation that you call"}}
                "assign_to": null (if step_type is "internal_reasoning") | "result_table_id"  # Must match one of the target schema IDs if this is a final result
            }}
            """
            plan: dict[str, Any] = parse_json(response)
            step_type: str = plan["step_type"]

            curr_retrieved_docs_tables_only: dict[str, DataFrame] = dict()
            for retriever_type in self.state.current_retrieved_documents:
                if retriever_type == RetrieverType.PNEUMA:
                    docs = self.state.current_retrieved_documents[retriever_type]
                    for doc in docs:
                        curr_retrieved_docs_tables_only[doc.doc_id] = doc.content
            
            external_data_tables_only: dict[str, DataFrame] = dict()
            for datum in external_data:
                if isinstance(datum, Table):
                    external_data_tables_only[datum.doc_id] = datum.content

            all_tables = {
                **curr_retrieved_docs_tables_only,
                **self.state.intermediate_tables,
                **external_data_tables_only,
            }

            if step_type == "internal_reasoning":
                message: str = plan["message"]
                self.actions.append(f"Reasoned internally: {message}")
            elif step_type == "operation":
                op_name: str = plan["name"]
                op_args: dict[str, Any] = plan["args"]
                assign_to: str = plan.get("assign_to", "")
                if op_name == "Document Retriever":
                    prompt: str = op_args["prompt"]
                    self.state.current_retrieved_documents = get_documents(
                        self.llm,
                        self.embed_model,
                        self.logger,
                        prompt,
                        self.data_sources,
                    )
                    self.actions.append(
                        f'Successfully retrieved documents using this prompt: ```{prompt}```. Notice that the "Previously retrieved documents" have been filled.'
                    )
                elif op_name == "Table Enumerator":
                    self.logger.info(f"Enter Table Enumerator")
                    pattern: str = op_args["pattern"]
                    extra_tables: list[AbstractDocument] = table_enumerator(
                        pattern, self.data_sources
                    )

                    if len(self.state.current_retrieved_documents.keys()) == 0:
                        if len(extra_tables) > 0:
                            self.state.current_retrieved_documents = {
                                RetrieverType.PNEUMA: extra_tables
                            }
                    else:
                        self.state.current_retrieved_documents[RetrieverType.PNEUMA] = (
                            list(
                                set(
                                    self.state.current_retrieved_documents[
                                        RetrieverType.PNEUMA
                                    ]
                                ).union(set(extra_tables))
                            )
                        )
                    if len(extra_tables) > 0:
                        self.actions.append(
                            f'Successfully retrieved all tables that match the pattern {pattern}. You can use them to materialize target schemas, even if you have not called Document Retriever before, as these tables have been included to "Previously retrieved documents".'
                        )
                    else:
                        self.actions.append(
                            f"There are no tables that match the pattern."
                        )
                elif op_name == "Table Select":
                    self.logger.info(f"Enter Table Select")
                    table_mapping = op_args
                    for target_schema_id, retrieved_table_info in table_mapping.items():
                        if isinstance(retrieved_table_info, list):
                            retrieved_table_info = retrieved_table_info[0]
                        retrieved_table_id: str = retrieved_table_info["id"]
                        relevant_columns: list[str] = retrieved_table_info["columns"]

                        if retrieved_table_id.startswith("Table "):
                            retrieved_table_id = retrieved_table_id[6:]
                        retrieved_table_id = retrieved_table_id.strip()
                        target_schema_id = target_schema_id.strip()
                        self.logger.info(
                            f"DEBUGGY: target_schema_id: {target_schema_id}; retrieved_table_id: {retrieved_table_id}"
                        )
                        if (
                            target_schema_id in target_schemas
                            and retrieved_table_id in all_tables
                        ):
                            # Trying to automatically resolve target and source columns
                            table = all_tables[retrieved_table_id][relevant_columns]
                            self.state.intermediate_tables[target_schema_id] = table
                            self.actions.append(
                                f"Successfully selecting retrieved tables in the mapping as target schema tables. Notice the state's intermediate tables have changed, but please CHECK if the schemas in the selected tables match with the ones in target schemas."
                            )
                        elif target_schema_id not in target_schemas:
                            self.actions.append(
                                f"Error: The ID {target_schema_id} does not exist in the target schemas. Please fix it."
                            )
                        else:
                            self.actions.append(
                                f"Error: The ID {retrieved_table_id} does not exist in either the retrieved tables OR the intermediate tables so far. Please fix it."
                            )
                elif op_name == "Semantic Column Generator":
                    table_id: str | None = op_args.get("table_id")
                    new_column_name: str | None = op_args.get("new_column_name")
                    table_relevant_columns: list[str] | None = op_args.get(
                        "relevant_columns"
                    )
                    instruction: str | None = op_args.get("instruction")

                    if table_id is None or table_id not in all_tables:
                        self.actions.append(
                            f"table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                        )
                        continue
                    if new_column_name is None:
                        self.actions.append("new_column_name is not provided.")
                        continue
                    if table_relevant_columns is None:
                        self.actions.append("relevant_columns is not provided.")
                        continue
                    if not set(table_relevant_columns) <= set(
                        list(all_tables[table_id].columns)
                    ):
                        self.actions.append(
                            f"relevant_columns must be a subset of the columns of table {table_id}."
                        )
                        continue
                    if instruction is None:
                        self.actions.append("instruction is not provided.")
                        continue

                    new_column_values = (
                        self.semantic_col_generator.generate_semantic_column(
                            all_tables[table_id][table_relevant_columns],
                            new_column_name,
                            instruction,
                        )
                    )
                    all_tables[table_id][new_column_name] = new_column_values
                    self.actions.append(
                        f"Successfully added a new column named {new_column_name} to table with ID {table_id}."
                    )

                elif op_name == "Semantic Join":
                    left_table_id: str | None = op_args.get("left_table_id")
                    right_table_id: str | None = op_args.get("right_table_id")
                    relevant_left_cols: list[str] | None = op_args.get(
                        "relevant_left_cols"
                    )
                    relevant_right_cols: list[str] | None = op_args.get(
                        "relevant_right_cols"
                    )
                    joined_table_id: str | None = op_args.get("joined_table_id")

                    if left_table_id is None or left_table_id not in all_tables:
                        self.actions.append(
                            f"left_table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                        )
                        continue
                    if right_table_id is None or right_table_id not in all_tables:
                        self.actions.append(
                            f"right_table_id is not valid (not part of retrieved tables or the state's intermediate tables)."
                        )
                        continue

                    left_table = all_tables[left_table_id]
                    right_table = all_tables[right_table_id]

                    if relevant_left_cols is None:
                        self.actions.append(f"relevant_left_cols is not provided.")
                        continue
                    if relevant_right_cols is None:
                        self.actions.append(f"relevant_right_cols is not provided.")
                        continue
                    if not set(relevant_left_cols) <= set(list(left_table.columns)):
                        self.actions.append(
                            f"relevant_left_cols is not a subseet of left_table's columns."
                        )
                        continue
                    if not set(relevant_right_cols) <= set(list(right_table.columns)):
                        self.actions.append(
                            f"relevant_right_cols is not a subseet of right_table's columns."
                        )
                        continue
                    if not joined_table_id:
                        self.actions.append(f"joined_table_id is not provided.")
                        continue

                    joined_table = self.semantic_joiner.semantic_join(
                        left_table,
                        right_table,
                        relevant_left_cols,
                        relevant_right_cols,
                        syntactic_sim_metric=SyntacticSimMetric.JACCARD_QGRAM,
                        top_k=2,
                    )
                    self.state.intermediate_tables[joined_table_id] = joined_table
                    self.actions.append(
                        f"Successfully joined the left and right tables semantically. Notice the state's intermediate tables have changed."
                    )
                elif op_name == "Python Executor":
                    python_code: str = parse_code(op_args["code"])
                    exec_res = execute_python_code(python_code, all_tables, self.logger)
                    if isinstance(exec_res, DataFrame):
                        if len(exec_res) == 0:
                            self.actions.append(
                                f"Something is wrong with your code; the table is empty. Plese reflect and adjust the code."
                            )

                        self.state.intermediate_tables[assign_to] = exec_res
                        self.actions.append(
                            f"Successfully executed the Python code, resulting in a table named {assign_to}"
                        )
                    elif isinstance(exec_res, Exception):
                        self.logger.info(
                            f"Exception during execution of the Python code: {exec_res}"
                        )
                        # Self-diagnose
                        diagnose_messages = [
                            LLMMessage(
                                role=Role.SYSTEM.value,
                                content=self.prompt_factory.get_fix_python_prompt(
                                    python_code, all_tables, exec_res
                                ),
                            )
                        ]
                        feedback = self.llm.chat(diagnose_messages)
                        feedback = "".join(feedback)
                        self.actions.append(feedback)
                    else:
                        if exec_res is None:
                            self.actions.append(
                                f"The `result` variable is empty, which means the my Python code did not assign the outcome (e.g., table) to the variable `result`."
                            )
                        else:
                            self.actions.append(
                                f"Successfully executed the Python code, resulting in this: {exec_res}"
                            )
                elif op_name == "SQL Executor":
                    try:
                        sql_query: str = op_args["sql_query"]
                        exec_res = execute_sql(
                            self.logger, sql_query, all_tables, self.llm
                        )
                        self.state.intermediate_tables[assign_to] = exec_res
                        self.actions.append(
                            f"Successfully executed the SQL query, resulting in a table named {assign_to}"
                        )
                    except Exception as e:
                        self.actions.append(
                            f"Error when executing the SQL query: {e}. Please fix it (you may want to quote identifiers with, for instance, `-` symbol)."
                        )
                else:
                    self.actions.append(
                        f"Trying to perform/execute {op_name}, but it is not a valid operation."
                    )
            else:
                self.actions.append(f"The step {step_type} is not a valid action.")
        self.logger.info("Materialization completed successfully")
        final_result: dict[str, DataFrame] = dict()
        for key, value in self.state.intermediate_tables.items():
            if key in target_schemas.keys():
                final_result[key] = value
        return final_result

    def __check_completion(self, target_schemas: dict[str, DataFrame]) -> bool:
        self.logger.info(f"CHECK COMPLETION")
        all_schema_ids = set(target_schemas.keys())
        materialized_schema_ids = set(self.state.intermediate_tables.keys())

        self.logger.info(f"==> all_schema_ids: {all_schema_ids}")
        self.logger.info(f"==> materialized_schema_ids: {materialized_schema_ids}")
        is_complete = all_schema_ids <= materialized_schema_ids

        if not is_complete:
            self.actions.append(
                f"You have not materialized these tables: {all_schema_ids - materialized_schema_ids}"
            )

        already_complete = is_complete
        column_issues: list[str] = []

        if is_complete:
            for target_schema_id in all_schema_ids:
                if target_schema_id in materialized_schema_ids:
                    self.logger.info(f"Checking the target schema {target_schema_id}.")

                    target_cols = set(target_schemas[target_schema_id].columns)
                    materialized_cols = set(
                        self.state.intermediate_tables[target_schema_id].columns
                    )

                    self.logger.info(f"target_cols {target_cols}")
                    self.logger.info(f"materialized_cols {materialized_cols}")

                    missing_cols = target_cols - materialized_cols
                    extra_cols = materialized_cols - target_cols

                    if missing_cols or extra_cols:
                        is_complete = False
                        issue_msg = f"For table `{target_schema_id}`: "

                        if missing_cols:
                            issue_msg += f"missing columns {sorted(missing_cols)}. "
                        if extra_cols:
                            issue_msg += f"unexpected columns {sorted(extra_cols)}. "

                        column_issues.append(issue_msg.strip())

        if already_complete and not is_complete:
            for issue in column_issues:
                self.actions.append(issue)
            self.actions.append(
                "Fix the above column issues. If some columns have different names (e.g., `Doc ID` vs `doc_id`), rename them using Python."
            )

        self.logger.info(f"==> is_complete: {is_complete}")
        self.logger.info(
            f"Completion check: {is_complete} ({len(materialized_schema_ids)}/{len(all_schema_ids)} schemas materialized)"
        )
        return is_complete
