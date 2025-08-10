from logging import Logger
from typing import Optional
from pneuma_seeker.core.ir_system.prompt_factory import PromptFactory
from pneuma_seeker.core.ir_system.data_model import (
    AbstractDocument,
    IRFeedbackOutputType,
    convert_retrieval_results_to_str,
)
from pneuma_seeker.core.ir_system.state import IRState
from pneuma_seeker.core.ir_system.retriever.retriever_factory import (
    RetrieverType,
    RetrieverFactory,
)
from pneuma_seeker.model.interface.abstract_model import AbstractModel
from pneuma_seeker.model.llm_message import LLMMessage, Role
from pneuma_seeker.model.option import LLMOption
from pneuma_seeker.utils.json_processor import parse_json

RETRIEVERS = [
    RetrieverType.PNEUMA,
    RetrieverType.KNOWLEDGE_BASE,
    RetrieverType.WEB_SEARCH,
]
RETRIEVER_INFO = [
    {
        "name": RetrieverType.PNEUMA,
        "description": "Retrieves relevant tabular data from the database.",
    },
    {
        "name": RetrieverType.KNOWLEDGE_BASE,
        "description": "Retrieves domain knowledge and user preferences captured from the users.",
    },
    {
        "name": RetrieverType.WEB_SEARCH,
        "description": "Retrieves information from the internet. Only use it for time-sensitive and external information requests to get more reference (e.g., today's stock information).",
    },
]
MAX_SANITY_CHECK_ITERATIONS = 3


class IRSystem:
    def __init__(self, models: dict[str, AbstractModel], logger: Logger):
        self.prompt_factory = PromptFactory()
        self.retriever_factory = RetrieverFactory(models)

        self.state = IRState()
        self.llm = models["llm"]
        self.embed_model = models["embed_model"]
        self.logger = logger

    def index_documents(
        self, retriever_type: RetrieverType, documents: list[AbstractDocument]
    ):
        """
        Indexes documents on a retriever.
        """
        self.logger.info(f"Indexing documents on the retriever {retriever_type}.")
        self.retriever_factory.get_retriever(retriever_type).index(documents)
        self.logger.info("Indexing process is done.")

    def get_relevant_retrievers(self, requirements: str) -> list[RetrieverType]:
        """
        Returns the list of relevant retrievers for the given requirements.
        """
        return [
            RetrieverType.PNEUMA,
            RetrieverType.KNOWLEDGE_BASE
        ]
        # relevant_retrievers: list[RetrieverType] = []
        # for i in RETRIEVER_INFO:
        #     messages = [
        #         LLMMessage(
        #             role=Role.SYSTEM.value,
        #             content=self.prompt_factory.get_retriever_classification_prompt(
        #                 requirements,
        #                 i["name"],
        #                 i["description"],
        #             ),
        #         )
        #     ]
        #     classification_output = self.llm.chat(messages).strip().lower()
        #     if classification_output.startswith("yes"):
        #         relevant_retrievers.append(i["name"])

        # if len(relevant_retrievers) == 0:
        #     # By default, use all retrievers if none is considered relevant by the LLM
        #     relevant_retrievers = [i["name"] for i in RETRIEVER_INFO]
        # return relevant_retrievers

    def retrieve_documents(
        self, prompt: str, sources: list[str], k: int = 10, retriever_types: Optional[list[RetrieverType]] = None
    ) -> dict[RetrieverType, list[AbstractDocument]]:
        """
        Retrieves context from the IR system with auto sanity check mechanism.
        """
        self.logger.info(f"Starting document retrieval for prompt: {prompt[:100]}...")
        if retriever_types is not None:
            relevant_retrievers = retriever_types
        else:
            relevant_retrievers = self.get_relevant_retrievers(prompt)
        self.logger.info(f"Selected retrievers: {relevant_retrievers}")

        all_retrieval_results: dict[RetrieverType, list[AbstractDocument]] = dict()
        for retriever_type in relevant_retrievers:
            self.logger.info(f"=> Retrieving from: {retriever_type}")
            curr_retrieval_results = self.retrieve(retriever_type, prompt, sources, k)

            self.logger.info(
                f"=> Initial retrieval returned {len(curr_retrieval_results)} documents:"
            )
            for retrieved_document in curr_retrieval_results:
                self.logger.info(
                    f"==> {retrieved_document}"
                )
            self.logger.info("=" * 50)
            
            all_retrieval_results[retriever_type] = curr_retrieval_results

            # relevant_retrieval_results: set[AbstractDocument] = set()
            # irrelevant_doc_ids: list[str] = []
            # total_sanity_check_iteration = 0
            # while (
            #     curr_retrieval_results
            #     and len(relevant_retrieval_results) < k
            #     and total_sanity_check_iteration < MAX_SANITY_CHECK_ITERATIONS
            # ):
            #     self.logger.info(
            #         f"=> Starting sanity check iteration {total_sanity_check_iteration + 1}"
            #     )
            #     sanity_check_messages = [
            #         LLMMessage(
            #             role=Role.USER.value,
            #             content=self.prompt_factory.get_ir_sanity_check_prompt(
            #                 prompt,
            #                 convert_retrieval_results_to_str(curr_retrieval_results),
            #             ),
            #         )
            #     ]

            #     sanity_check_result: IRFeedbackOutputType = parse_json(
            #         self.llm.chat(sanity_check_messages, LLMOption(json_mode=True))
            #     )
            #     total_sanity_check_iteration += 1

            #     irrelevant_doc_ids = sanity_check_result["irrelevant_doc_ids"]
            #     feedback = sanity_check_result["feedback"]
            #     self.logger.info(
            #         f"=> Found {len(irrelevant_doc_ids)} irrelevant documents: {irrelevant_doc_ids}"
            #     )
            #     self.logger.info(
            #         f"=> Feedback: {feedback}"
            #     )

            #     for i in curr_retrieval_results:
            #         if i.doc_id not in irrelevant_doc_ids:
            #             relevant_retrieval_results.add(i)
                
            #     if len(irrelevant_doc_ids) == 0:
            #         self.logger.info(
            #             f"==> Since there are no irrelevant documents, we don't need to do another sanity check."
            #         )
            #         break
            #     elif len(irrelevant_doc_ids) > 0 and feedback != "":
            #         self.logger.info(f"==> Re-retrieving documents with feedback: {feedback}")
            #         curr_retrieval_results = self.re_retrieve_with_feedback(
            #             retriever_type,
            #             feedback,
            #             [
            #                 i
            #                 for i in curr_retrieval_results
            #                 if i.doc_id in irrelevant_doc_ids
            #             ],
            #             k,
            #             sources,
            #         )
            #         self.logger.info(
            #             f"=> Adjusted retrieval returned {len(curr_retrieval_results)} documents:"
            #         )
            #         for retrieved_document in curr_retrieval_results:
            #             self.logger.info(
            #                 f"==> {retrieved_document}"
            #             )

            # # If at the end, we have less than k results, we should not discard the supposedly
            # # irrelevant results. Let's keep them.
            # irrelevant_retrieval_results = [
            #     i for i in curr_retrieval_results if i.doc_id in irrelevant_doc_ids
            # ]
            # idx = 0
            # while len(relevant_retrieval_results) < k and idx < len(
            #     irrelevant_retrieval_results
            # ):
            #     relevant_retrieval_results.add(irrelevant_retrieval_results[idx])
            #     idx += 1

            # all_retrieval_results[retriever_type] = list(relevant_retrieval_results)
            # self.logger.info(
            #     f"Final results for {retriever_type}: {len(relevant_retrieval_results)} documents:"
            # )
            # for retrieved_document in curr_retrieval_results:
            #     self.logger.info(
            #         f"==> {retrieved_document}"
            #     )

        self.logger.info("Document retrieval completed")
        return all_retrieval_results

    def retrieve(
        self,
        retriever_type: RetrieverType,
        prompt: str,
        sources: list[str],
        k: int = 10,
    ) -> list[AbstractDocument]:
        """
        Retrieves documents from the specified retriever.

        - prompt (str): The query to be given to the retriever.
        """
        self.state.current_queries[retriever_type] = prompt
        retriever = self.retriever_factory.get_retriever(retriever_type)
        documents = retriever.retrieve(prompt, sources, k)
        return documents

    def re_retrieve_with_feedback(
        self,
        retriever_type: RetrieverType,
        feedback: str,
        irrelevant_results: list[AbstractDocument],
        k: int,
        sources: list[str],
    ) -> list[AbstractDocument]:
        """
        Re-retrives previously (irrelevant) retrieved documents.
        It does so by adjusting the prompt using the feedback.
        """
        sys_prompt = self.prompt_factory.get_refine_retrieval_prompt(
            self.state.current_queries[retriever_type],
            convert_retrieval_results_to_str(irrelevant_results),
            feedback,
        )
        refined_prompt = self.llm.chat(
            [LLMMessage(role=Role.SYSTEM.value, content=sys_prompt)]
        )
        print(f"Refined prompt: {refined_prompt}")
        return self.retrieve(retriever_type, refined_prompt, sources, k)
