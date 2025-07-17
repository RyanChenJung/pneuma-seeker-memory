from ast import literal_eval
from logging import Logger

import duckdb
from pandas import DataFrame

from processor.core.interaction_conductor.ic_prompt_factory import ICPromptFactory
from processor.core.interaction_conductor.ic_state import ICState
from processor.core.interaction_conductor.ic_data_model import (
    IRFeedbackOutputType,
    LLMConductorOutputType,
    ToolType,
)
from processor.core.ir_system.ir_data_model import (
    RetrieverType,
    convert_retrieval_results_to_str,
)
from processor.core.ir_system.ir_state import AbstractDocument
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.llm_planner import LLMPlanner
from processor.core.interaction_conductor.ic_data_model import ToolType
from processor.model.interface.model_factory import get_llm
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption
from processor.utils.json_processor import parse_json


class LLMConductor:
    def __init__(self, llm_path: str, logger: Logger):
        """
        Initializes the LLM Conductor with a state, and materializer.
        """
        self.state = ICState()
        self.llm = get_llm(llm_path)(llm_path)
        self.chat_history: list[LLMMessage] = []
        self.prompt_factory = ICPromptFactory()
        self.materializer = LLMPlanner(self.llm)
        self.logger = logger

    def process_input(self, user_input: str) -> str:
        """
        Processes the user input, possibly calling tools.
        """
        self.logger.info(f"Start processing this user input: {user_input}")
        is_thinking_done = False
        final_response = ""
        self.chat_history.append(
            LLMMessage(
                user_input,
                Role.USER,
            )
        )

        total_iteration = 0
        iteration_limit = 5  # TODO: Determine limit more dynamically based on, e.g., input-output properties
        while not is_thinking_done and total_iteration < iteration_limit:
            model_output = self.llm.chat(self.chat_history, LLMOption(json_mode=True))
            self.logger.info(f"Model output: {model_output}")
            json_output: LLMConductorOutputType = parse_json(model_output)

            is_direct_response = json_output.get("is_direct_response")
            tool = json_output.get("tool")
            response = json_output.get("response")

            if is_direct_response:
                final_response = response
                self.logger.info(
                    f"=> Get direct response to return to the user: {final_response}"
                )
                is_thinking_done = True
            elif tool:
                if tool == ToolType.IR_SYSTEM:
                    context = self.__retrieve_context(response["prompt"])
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM,
                            content=f"The context requested: {context}",
                        )
                    )
                elif tool == ToolType.MATERIALIZER_ENGINE:
                    current_state = self.state.get_state()
                    materialized_target_schemas = (
                        self.materializer.materialize_target_schemas(
                            current_state["target_schemas"], current_state["sqls"]
                        )
                    )
                    self.state.set_state(
                        current_state["sqls"], materialized_target_schemas
                    )
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM,
                            content="The target schema has been materialized. You can ask the user if they want to execute the SQL statements to get the answer to their information need. It's possible that they decide to reset the state.",
                        )
                    )
                elif tool == ToolType.STATE_MANIPULATION:
                    new_sqls = response["new_sqls"]
                    new_target_schemas = response["new_target_schemas"]
                    new_target_schemas_df = []
                    for i in new_target_schemas:
                        # Assume i is a list of column names
                        new_target_schemas_df.append(DataFrame(columns=literal_eval(i)))
                    self.state.set_state(new_sqls, new_target_schemas_df)
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM,
                            content="The state has been adjusted as requested.",
                        )
                    )
                elif tool == ToolType.SQL_ENGINE:
                    result = self.__execute_sqls()
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.SYSTEM,
                            content=f"The SQLs have been executed, and this is the output: {result}",
                        )
                    )
            else:
                raise ValueError("The JSON output is invalid.")
            total_iteration += 1
        if total_iteration == iteration_limit and not is_thinking_done:
            self.chat_history.append(
                LLMMessage(
                    role=Role.SYSTEM,
                    content=self.prompt_factory.get_force_produce_final_response_prompt(total_iteration)
                )
            )
            final_response = self.llm.chat(self.chat_history)
        return final_response

    def __retrieve_context(
        self, prompt: str, sources: list[str] = None, k: int = 10
    ) -> dict[RetrieverType, AbstractDocument]:
        """
        Retrieves context from the IR system with auto sanity check mechanism.
        """
        ir_system = LMInterface(self.llm)
        relevant_retrievers = ir_system.get_relevant_retrievers(prompt)
        all_retrieval_results: dict[RetrieverType, list[AbstractDocument]] = dict()
        for retriever_type in relevant_retrievers:
            total_sanity_check_iteration = 0
            relevant_retrieval_results: list[AbstractDocument] = []

            curr_retrieval_results = ir_system.retrieve(
                retriever_type, prompt, sources, k
            )
            while (
                curr_retrieval_results
                and len(relevant_retrieval_results) < k
                and total_sanity_check_iteration < 5
            ):
                sanity_check_messages = [
                    LLMMessage(
                        role=Role.USER,
                        content=self.prompt_factory.get_ir_sanity_check_prompt(
                            prompt,
                            convert_retrieval_results_to_str(curr_retrieval_results),
                        ),
                    )
                ]
                sanity_check_result: IRFeedbackOutputType = parse_json(
                    self.llm.chat(sanity_check_messages, LLMOption(json_mode=True))
                )
                total_sanity_check_iteration += 1

                irrelevant_doc_ids = sanity_check_result["irrelevant_doc_ids"]
                feedback = sanity_check_result["feedback"]

                relevant_retrieval_results.extend(
                    [
                        i
                        for i in curr_retrieval_results
                        if i.doc_id not in irrelevant_doc_ids
                    ]
                )

                if len(irrelevant_doc_ids) > 0 and feedback != "":
                    curr_retrieval_results = ir_system.re_retrieve_with_feedback(
                        feedback,
                        [
                            i
                            for i in curr_retrieval_results
                            if i.doc_id in irrelevant_doc_ids
                        ],
                        k,
                    )

            irrelevant_retrieval_results = [
                i for i in curr_retrieval_results if i.doc_id in irrelevant_doc_ids
            ]
            idx = 0
            while len(relevant_retrieval_results) < k and idx < len(
                irrelevant_retrieval_results
            ):
                relevant_retrieval_results.append(irrelevant_retrieval_results[idx])
                idx += 1
            all_retrieval_results[retriever_type] = relevant_retrieval_results
        return all_retrieval_results

    def __execute_sqls(self) -> str:
        """
        Executes the SQLs (sequentially) over the target schemas.
        The result (for now) is a scalar (converted to string).
        """
        curr_state = self.state.get_state()
        tables: dict[str, DataFrame] = curr_state["target_schemas"]
        sqls: list[str] = curr_state["sqls"]

        # Create an in-memory DuckDB connection
        con = duckdb.connect(database=':memory:')

        # Register each table into DuckDB
        for table_name, df in tables.items():
            con.register(table_name, df)

        result = None
        for sql in sqls:
            result = con.execute(sql).fetchdf()

        # If the result has only one cell, return it as a scalar string
        if result.shape == (1, 1):
            return str(result.iat[0, 0])

        return result
