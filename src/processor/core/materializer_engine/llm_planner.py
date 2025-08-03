from typing import Any

from logging import Logger
from pandas import DataFrame
from processor.core.ir_system.ir_data_model import RetrieverType
from processor.core.materializer_engine.me_prompt_factory import MEPromptFactory
from processor.core.materializer_engine.me_state import MaterializerState
from processor.core.materializer_engine.operation.document_retriever import (
    get_documents,
)
from processor.core.materializer_engine.operation.operation_description import (
    get_operation_description,
)
from processor.core.materializer_engine.operation.python_executor import (
    execute_python_code,
)
from processor.core.materializer_engine.operation.sql_executor import execute_sql
from processor.core.materializer_engine.operation.std_inner_join import std_inner_join
from processor.core.materializer_engine.operation.union import union
from processor.model.interface.abstract_model import AbstractModel
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption
from processor.utils.json_processor import parse_code, parse_json


class LLMPlanner:
    def __init__(
        self,
        llm: AbstractModel,
        logger: Logger,
        embed_model: AbstractModel,
        data_sources: list[str],
    ):
        self.logger = logger
        self.logger.info(
            "Initializing LLMPlanner, the core component of Materializer Engine"
        )
        self.llm = llm
        self.embed_model = embed_model

        self.prompt_factory = MEPromptFactory()
        self.state = MaterializerState()

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
    ) -> dict[str, DataFrame]:
        self.logger.info(
            f"Starting materialization for {len(target_schemas)} target schemas with {len(sqls)} SQLs"
        )
        self.__cleanup_system()
        sys_prompt = LLMMessage(
            role=Role.SYSTEM.value,
            content=self.prompt_factory.get_planning_prompt_brief(
                target_schemas=target_schemas,
                column_descriptions=column_descriptions,
                sqls=sqls,
                operation_description=get_operation_description(),
            ),
        )

        num_iterations = 0
        llm_messages = [sys_prompt]
        while not self.__check_completion(target_schemas, sqls):
            self.logger.info("Planning next materialization step")
            self.logger.info("Requesting LLM response for plan")
            llm_messages.append(
                LLMMessage(
                    role=Role.USER.value,
                    content=self.prompt_factory.get_context_prompt_brief(
                        self.state.current_retrieved_documents,
                        self.state.intermediate_tables,
                        self.actions,
                        num_iterations,
                        user_side_note,
                    ),
                )
            )

            num_iterations += 1
            response = self.llm.chat(llm_messages, LLMOption(json_mode=True))
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
                        alternative_doc_id = doc.doc_id.split("/")[-1]
                        curr_retrieved_docs_tables_only[doc.doc_id] = doc.content
                        curr_retrieved_docs_tables_only[alternative_doc_id] = (
                            doc.content
                        )
            all_tables = {
                **curr_retrieved_docs_tables_only,
                **self.state.intermediate_tables,
            }

            if step_type == "internal_reasoning":
                message: str = plan["message"]
                self.actions.append(f"Reasoned internally: {message}")
            elif step_type == "operation":
                op_name: str = plan["name"]
                op_args: dict[str, Any] = plan["args"]
                assign_to: str = plan.get("assign_to", "")
                if op_name == "Standard Inner Join":
                    left_table_id: str = op_args["left_table_id"]
                    right_table_id: str = op_args["right_table_id"]
                    join_key: str = op_args["join_key"]
                    join_res = std_inner_join(
                        left_table_id,
                        right_table_id,
                        all_tables,
                        join_key,
                    )
                    self.state.intermediate_tables[assign_to] = join_res
                    self.actions.append(
                        f"Performed standard inner join between {left_table_id} and {right_table_id} with join key {join_key}, resulting in {assign_to}"
                    )
                elif op_name == "Union":
                    table_ids: list[str] = op_args["table_ids"]
                    union_res = union(all_tables, table_ids)
                    self.state.intermediate_tables[assign_to] = union_res
                    self.actions.append(
                        f"Performed union between these tables: {table_ids}, resulting in {assign_to}"
                    )
                elif op_name == "Document Retriever":
                    prompt: str = op_args["prompt"]
                    extra_documents = get_documents(
                        self.llm,
                        self.embed_model,
                        self.logger,
                        prompt,
                        self.data_sources,
                    )

                    if len(self.state.current_retrieved_documents.keys()) == 0:
                        self.state.current_retrieved_documents = extra_documents

                    self.state.current_retrieved_documents[RetrieverType.PNEUMA] = list(
                        set(self.state.current_retrieved_documents[RetrieverType.PNEUMA]).union(set(extra_documents[RetrieverType.PNEUMA]))
                    )
                    self.actions.append(
                        f'Successfully retrieved documents using this prompt: ```{prompt}```. Notice that the "Previously retrieved documents" have been filled.'
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
                        self.logger.info(f"Exception during execution of the Python code: {exec_res}")
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
                    sql_query: str = op_args["sql_query"]
                    exec_res = execute_sql(self.logger, sql_query, all_tables, self.llm)
                    self.state.intermediate_tables[assign_to] = exec_res
                    self.actions.append(
                        f"Successfully executed the SQL query, resulting in a table named {assign_to}"
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

    def __check_completion(
        self, target_schemas: dict[str, DataFrame], sqls: list[str]
    ) -> bool:
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
        wrong_columns = []
        if is_complete:
            for target_schema_id in all_schema_ids:
                if target_schema_id in materialized_schema_ids:
                    self.logger.info(f"Checking the {target_schema_id}")
                    target_table_columns = set(target_schemas[target_schema_id].columns)
                    materialized_table_columns = set(
                        self.state.intermediate_tables[target_schema_id].columns
                    )

                    self.logger.info(f"target_table_columns {target_table_columns}")
                    self.logger.info(
                        f"materialized_table_columns {materialized_table_columns}"
                    )
                    if target_table_columns != materialized_table_columns:
                        is_complete = False
                        wrong_columns.extend(
                            target_table_columns - materialized_table_columns
                        )
        if already_complete and not is_complete:
            self.actions.append(
                f"You either: 1) overselected the columns (i.e., there are unnecessary columns not specified in the target schemas), in which you should remove them, or 2) you should rename some column names using a Python code, as these columns may have different names in the materialized schemas (e.g., `Doc ID` instead of `doc_id`)."
            )
            print(self.actions[-1])

        self.logger.info(f"==> is_complete: {is_complete}")
        self.logger.info(
            f"Completion check: {is_complete} ({len(materialized_schema_ids)}/{len(all_schema_ids)} schemas materialized)"
        )
        return is_complete
