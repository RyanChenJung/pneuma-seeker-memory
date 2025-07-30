from typing import Any, Optional

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
from processor.utils.json_processor import parse_json


class LLMPlanner:
    def __init__(self, llm: AbstractModel, logger: Logger, embed_model: AbstractModel, data_sources: list[str]):
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

        self.feedback_iteration = 0

    def materialize_target_schemas(
        self,
        target_schemas: dict[str, DataFrame],
        column_descriptions: dict[str, dict[str, str]],
        sqls: list[str],
        feedback: Optional[str] = None,
    ) -> dict[str, DataFrame]:
        self.logger.info(
            f"Starting materialization for {len(target_schemas)} target schemas with {len(sqls)} SQLs"
        )
        if not feedback:
            self.state.reset()
        sys_prompt = LLMMessage(
            role=Role.SYSTEM.value,
            content=self.prompt_factory.get_planning_prompt(
                target_schemas=target_schemas,
                column_descriptions=column_descriptions,
                sqls=sqls,
                operation_description=get_operation_description(),
            ),
        )
        if feedback and len(self.state.intermediate_tables) > 0:
            sys_prompt = LLMMessage(
                role=Role.SYSTEM.value,
                content=self.prompt_factory.get_planning_prompt_with_feedback(
                    target_schemas=target_schemas,
                    column_descriptions=column_descriptions,
                    sqls=sqls,
                    operation_description=get_operation_description(),
                    feedback=feedback,
                ),
            )
        num_iterations = 0
        llm_messages = [sys_prompt]
        while not self.__check_completion(target_schemas, feedback):
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
                        curr_retrieved_docs_tables_only[doc.doc_id] = doc.content
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
                assign_to: str = plan.get("assign_to")
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
                    self.state.current_retrieved_documents = get_documents(
                        self.llm, self.embed_model, self.logger, prompt, self.data_sources
                    )
                    self.actions.append(
                        f'Successfully retrieved documents using this prompt: ```{prompt}```. Notice that the "Previously retrieved documents" have been filled.'
                    )
                elif op_name == "Table Select":
                    self.logger.info(f"Enter Table Select")
                    table_mapping = op_args
                    for target_schema_id, retrieved_table_id in table_mapping.items():
                        if retrieved_table_id.startswith("Table "):
                            retrieved_table_id = retrieved_table_id[6:]
                        retrieved_table_id = retrieved_table_id.strip()
                        target_schema_id = target_schema_id.strip()
                        self.logger.info(f"DEBUGGY: target_schema_id: {target_schema_id}; retrieved_table_id: {retrieved_table_id}")
                        if target_schema_id in target_schemas and retrieved_table_id in all_tables:
                            self.state.intermediate_tables[target_schema_id] = all_tables[retrieved_table_id]
                    self.actions.append(
                        f"Successfully selecting retrieved tables in the mapping as target schema tables. Notice the state's intermediate tables have changed."
                    )
                elif op_name == "Python Executor":
                    python_code: str = op_args["code"]
                    exec_res = execute_python_code(python_code, all_tables, self.logger)
                    if isinstance(exec_res, DataFrame):
                        self.state.intermediate_tables[assign_to] = exec_res
                        self.actions.append(
                            f"Successfully executed the Python code, resulting in a table named {assign_to}"
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

    def __check_completion(self, target_schemas: dict[str, DataFrame], feedback: str | None) -> bool:
        if feedback and self.feedback_iteration < 2:
            self.feedback_iteration += 1
            return False
        self.logger.info(f"CHECK COMPLETION")
        all_schema_ids = set(target_schemas.keys())
        materialized_schema_ids = set(self.state.intermediate_tables.keys())
        self.logger.info(f"==> all_schema_ids: {all_schema_ids}")
        self.logger.info(f"==> materialized_schema_ids: {materialized_schema_ids}")

        is_complete = all_schema_ids <= materialized_schema_ids

        self.logger.info(f"==> is_complete: {is_complete}")

        self.logger.info(
            f"Completion check: {is_complete} ({len(materialized_schema_ids)}/{len(all_schema_ids)} schemas materialized)"
        )
        return is_complete
