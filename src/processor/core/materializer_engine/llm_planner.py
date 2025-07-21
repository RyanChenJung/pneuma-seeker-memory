from typing import Any
import pandas as pd

from logging import Logger
from pandas import DataFrame
from processor.core.materializer_engine.me_prompt_factory import MEPromptFactory
from processor.core.materializer_engine.me_state import MaterializerState
from processor.core.materializer_engine.tool.tool_factory import ToolFactory
from processor.core.materializer_engine.operation.operation_factory import (
    OperationFactory,
)
from processor.model.interface.abstract_model import AbstractModel
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption
from processor.utils.json_processor import parse_json


class LLMPlanner:
    def __init__(self, llm: AbstractModel, logger: Logger, embed_model: AbstractModel):
        self.logger = logger
        self.logger.info("Initializing LLMPlanner")
        self.llm = llm
        self.embed_model = embed_model

        self.operation_factory = OperationFactory()
        self.tool_factory = ToolFactory()
        self.prompt_factory = MEPromptFactory()
        self.state = MaterializerState()

    def materialize_target_schemas(
        self, target_schemas: dict[str, dict[str, str]], sqls: list[str]
    ) -> dict[str, DataFrame]:
        self.logger.info(
            f"Starting materialization for {len(target_schemas)} target schemas with {len(sqls)} SQLs"
        )
        self.state.reset()
        while not self.__check_completion(target_schemas):
            self.logger.info("Planning next materialization step")
            plan_prompt = self.prompt_factory.get_planning_prompt(
                target_schemas=target_schemas,
                sqls=sqls,
                history=self.state.action_history,
                tools=self.tool_factory.available_tools(),
                operations=self.operation_factory.available_operations(),
                retrieved_documents=self.state.current_retrieved_documents,
                intermediate_tables=self.state.intermediate_tables,
            )

            self.logger.info("Requesting LLM response for plan")
            response = self.llm.chat(
                [
                    LLMMessage(
                        role=Role.SYSTEM.value,
                        content=plan_prompt,
                    )
                ],
                LLMOption(json_mode=True),
            )
            self.state.action_history.append(
                LLMMessage(role=Role.ASSISTANT.value, content=response)
            )
            self.logger.info(f"LLM response: {response}")

            try:
                plan = parse_json(response)
                self.logger.info(
                    f"Executing plan of type: {plan.get('step_type')} with name: {plan.get('name')}"
                )
                result = self.__execute_plan(plan, target_schemas)
                self.logger.info(f"Updating state with result for: {plan['assign_to']}")
                self.__update_state_with_result(
                    plan["assign_to"], result, target_schemas
                )
            except Exception as e:
                self.logger.error(f"Failed to execute plan: {e}", exc_info=True)
                continue

        self.logger.info("Materialization completed successfully")
        return self.state.materialized_target_schemas

    def __check_completion(self, target_schemas: dict[str, dict[str, str]]) -> bool:
        all_schema_ids = set(target_schemas.keys())
        materialized_schema_ids = set(self.state.materialized_target_schemas.keys())
        is_complete = all_schema_ids == materialized_schema_ids
        self.logger.info(
            f"Completion check: {is_complete} ({len(materialized_schema_ids)}/{len(all_schema_ids)} schemas materialized)"
        )
        return is_complete

    def __execute_plan(self, plan: dict, target_schemas: dict[str, dict[str, str]]) -> Any:
        step_type = plan["step_type"]
        self.logger.info(f"Executing plan step: {step_type}")

        if step_type == "operation":
            self.logger.info(f"Executing operation: {plan['name']}")
            operation = self.operation_factory.get_operation(plan["name"])
            inputs = [self.__resolve_input(input_id) for input_id in plan["inputs"]]
            self.logger.info(f"Operation inputs resolved: {len(inputs)} inputs")
            return operation.execute(*inputs, **plan.get("parameters", {}))

        elif step_type == "tool":
            self.logger.info(f"Executing tool: {plan['name']}")
            tool = self.tool_factory.get_tool(plan["name"])

            # Get the main input
            main_input = (
                plan["inputs"][0]
                if isinstance(plan["inputs"], list)
                else plan["inputs"]
            )

            # Prepare tool-specific parameters
            tool_params = {}

            if plan["name"] == "SQL Executor" and "tables" in plan["parameters"]:
                # Resolve table references to actual DataFrames
                table_dict = {}
                for table_name, table_id in plan["parameters"]["tables"].items():
                    table_dict[table_name] = self.__resolve_input(table_id)
                tool_params["tables"] = table_dict

            elif plan["name"] == "Document Retriever":
                tool_params["llm"] = self.llm
                tool_params["embed_model"] = self.embed_model

            elif plan["name"] == "Python Executor":
                # Add state variables to Python context
                tool_params["context"] = {
                    "intermediate_tables": self.state.intermediate_tables,
                    "target_schemas": target_schemas,
                    "retrieved_documents": self.state.current_retrieved_documents,
                }

            self.logger.info(f"Executing tool with parameters: {tool_params}")
            result = tool.execute(main_input, **tool_params)

            # Special handling for Document Retriever results
            if plan["name"] == "Document Retriever":
                self.logger.info(
                    f"Updating retrieved documents with {len(result)} new documents"
                )
                # Update current retrieved documents
                for retriever_docs in result.values():
                    self.state.current_retrieved_documents.update(retriever_docs)
                # Return None since we don't want to store this result
                return None

            return result
        else:
            self.logger.error(f"Unknown step type encountered: {step_type}")
            raise ValueError(f"Unknown step type: {step_type}")

    def __resolve_input(self, input_id: str) -> DataFrame:
        self.logger.info(f"Resolving input: {input_id}")
        # Check intermediate tables first
        if input_id in self.state.intermediate_tables:
            return self.state.intermediate_tables[input_id]

        # Then check materialized schemas
        if input_id in self.state.materialized_target_schemas:
            return self.state.materialized_target_schemas[input_id]

        # Finally check retrieved documents
        for doc in self.state.current_retrieved_documents:
            if doc.doc_id == input_id:
                if isinstance(doc.content, DataFrame):
                    return doc.content
                raise ValueError(f"Document {input_id} content is not a DataFrame")

        self.logger.error(f"Failed to resolve input: {input_id}")
        raise ValueError(f"Could not find input '{input_id}' in any available sources")

    def __update_state_with_result(
        self, name: str, result: Any, target_schemas: dict[str, dict[str, str]]
    ):
        if result is None:
            self.logger.info(f"Skipping update for {name} - result is None")
            return

        if not isinstance(result, pd.DataFrame):
            self.logger.warning(f"Result '{name}' is not a DataFrame, skipping.")
            return

        self.logger.info(
            f"Updating state with result for {name} (shape: {result.shape})"
        )
        # Validate schema if this is a target schema
        if name in target_schemas:
            expected_columns = set(target_schemas[name])
            actual_columns = set(result.columns)
            if expected_columns != actual_columns:
                raise ValueError(
                    f"Schema mismatch for {name}. Expected: {expected_columns}, Got: {actual_columns}"
                )

        # Store result
        if name in target_schemas:
            self.state.materialized_target_schemas[name] = result
        else:
            self.state.intermediate_tables[name] = result
