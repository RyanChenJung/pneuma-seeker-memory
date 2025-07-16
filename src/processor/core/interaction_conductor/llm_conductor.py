from ast import literal_eval
from typing import cast

from pandas import DataFrame

from processor.core.interaction_conductor.ic_prompt_factory import ICPromptEngineer
from processor.core.interaction_conductor.ic_state import ICState
from processor.core.interaction_conductor.ic_data_model import (
    IRFeedbackOutputType,
    LLMConductorOutputType,
    ToolType,
    IRSystemToolCallingType,
    StateManipulationToolCallingType,
)
from processor.core.ir_system.ir_data_model import RetrieverType
from processor.core.ir_system.ir_state import AbstractDocument
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.llm_planner import LLMPlanner
from processor.core.interaction_conductor.ic_data_model import ToolType
from processor.model.interface.model_factory import get_llm
from processor.model.llm_message import LLMMessage, Role
from processor.model.option import LLMOption
from processor.utils.json_processor import parse_json


class LLMConductor:
    def __init__(self, llm_path: str):
        """
        Initializes the LLM Conductor with a state, and materializer.
        """
        self.state = ICState()
        self.llm = get_llm(llm_path)(llm_path)
        self.chat_history: list[LLMMessage] = []
        self.prompt_engineer = ICPromptEngineer()
        self.materializer = LLMPlanner(self.llm)

    def process_input(self, user_input: str) -> str:
        """
        Processes the user input, possibly calling tools.
        """
        is_thinking_done = False
        final_response = ""
        self.chat_history.append(
            LLMMessage(
                user_input,
                Role.USER,
            )
        )
        while not is_thinking_done:
            model_output = self.llm.chat(self.chat_history, LLMOption(json_mode=True))
            json_output: LLMConductorOutputType = parse_json(model_output)
            if json_output["is_direct_response"] and json_output["direct_response"]:
                final_response = json_output["direct_response"]
                is_thinking_done = True
            elif json_output["tool"]:
                tool = json_output["tool"]
                if tool == ToolType.IR_SYSTEM:
                    ir_system_instructions = cast(IRSystemToolCallingType, json_output)
                    retrieval_prompt = ir_system_instructions["prompt"]
                    # TODO: Serialize the output!
                    context = self.retrieve_context(retrieval_prompt)
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.ASSISTANT,
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
                            role=Role.ASSISTANT,
                            content="The target schema has been materialized. You can ask the user if they want to execute the SQL statements to get the answer to their information need.",
                        )
                    )
                elif tool == ToolType.STATE_MANIPULATION:
                    state_manipulation_instructions = cast(
                        StateManipulationToolCallingType, json_output
                    )
                    new_sqls = state_manipulation_instructions["new_sqls"]
                    new_target_schemas = state_manipulation_instructions[
                        "new_target_schemas"
                    ]
                    new_target_schemas_df = []
                    for i in new_target_schemas:
                        # Assume i is a list of column names
                        new_target_schemas_df.append(DataFrame(columns=literal_eval(i)))
                    self.state.set_state(new_sqls, new_target_schemas_df)
                    self.chat_history.append(
                        LLMMessage(
                            role=Role.ASSISTANT,
                            content="The state has been adjusted as requested.",
                        )
                    )
            else:
                raise ValueError("The JSON output is invalid.")

        return final_response

    def retrieve_context(
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
                        content=self.prompt_engineer.get_ir_sanity_check_prompt(
                            prompt,
                            self.__convert_retrieval_results_to_str(
                                curr_retrieval_results
                            ),
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

    def __convert_retrieval_results_to_str(
        self, retrieval_results: list[AbstractDocument]
    ):
        representation = "Retrieval results:\n"
        for result in retrieval_results:
            representation += f"- ```{str(result)}```\n"
        return representation.strip()
