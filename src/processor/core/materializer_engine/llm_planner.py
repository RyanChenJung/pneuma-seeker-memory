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
        self.llm = llm
        self.embed_model = embed_model
        self.logger = logger

        self.operation_factory = OperationFactory()
        self.tool_factory = ToolFactory()
        self.prompt_factory = MEPromptFactory()
        self.state = MaterializerState(
            
        )

    def materialize_target_schemas(
        self, target_schemas: dict[str, list[str]], sqls: list[str]
    ) -> dict[str, DataFrame]:
        self.state.reset()
        while not self.__check_completion(target_schemas):
            plan_prompt = self.prompt_factory.get_planning_prompt(
                target_schemas=target_schemas,
                sqls=sqls,
                history=self.state.action_history,
                tools=self.tool_factory.available_tools(),
                operations=self.operation_factory.available_operations(),
                retrieved_documents=self.state.current_retrieved_documents,
                intermediate_tables=self.state.intermediate_tables,
            )

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

            try:
                plan = parse_json(response)
                result = self.__execute_plan(plan, target_schemas)
                self.__update_state_with_result(plan["assign_to"], result, target_schemas)
            except Exception as e:
                self.logger.error(f"Failed to execute plan: {e}")
                continue

        return self.state.materialized_target_schemas

    def __check_completion(self, target_schemas: dict[str, list[str]]) -> bool:
        # Future-TODO: Implement rule-based or LLM-guided checking later if necessary
        all_schema_ids = set(target_schemas.keys())
        materialized_schema_ids = set(self.state.materialized_target_schemas.keys())
        return all_schema_ids == materialized_schema_ids

    def __execute_plan(self, plan: dict, target_schemas: dict[str, list[str]]) -> Any:
        step_type = plan["step_type"]
        if step_type == "operation":
            operation = self.operation_factory.get_operation(plan["name"])
            # Convert input IDs to actual DataFrames
            inputs = [self.__resolve_input(input_id) for input_id in plan["inputs"]]
            return operation.execute(*inputs, **plan.get("parameters", {}))

        elif step_type == "tool":
            tool = self.tool_factory.get_tool(plan["name"])
            
            # Get the main input
            main_input = plan["inputs"][0] if isinstance(plan["inputs"], list) else plan["inputs"]
            
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
                    "retrieved_documents": self.state.current_retrieved_documents
                }
            
            # Execute tool and handle results
            result = tool.execute(main_input, **tool_params)
            
            # Special handling for Document Retriever results
            if plan["name"] == "Document Retriever":
                # Update current retrieved documents
                for retriever_docs in result.values():
                    self.state.current_retrieved_documents.update(retriever_docs)
                # Return None since we don't want to store this result
                return None
                
            return result

        else:
            raise ValueError(f"Unknown step type: {step_type}")

    def __resolve_input(self, input_id: str) -> DataFrame:
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
        
        raise ValueError(f"Could not find input '{input_id}' in any available sources")

    def __update_state_with_result(self, name: str, result: Any, target_schemas: dict[str, list[str]]):
        if result is None:
            return
            
        if not isinstance(result, pd.DataFrame):
            self.logger.warning(f"Result '{name}' is not a DataFrame, skipping.")
            return
            
        # Validate schema if this is a target schema
        if name in target_schemas:
            expected_columns = set(target_schemas[name])
            actual_columns = set(result.columns)
            if expected_columns != actual_columns:
                raise ValueError(f"Schema mismatch for {name}. Expected: {expected_columns}, Got: {actual_columns}")
        
        # Store result
        if name in target_schemas:
            self.state.materialized_target_schemas[name] = result
        else:
            self.state.intermediate_tables[name] = result
