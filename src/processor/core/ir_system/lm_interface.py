from processor.core.ir_system.ir_prompt_factory import IRPromptFactory
from processor.core.ir_system.ir_data_model import AbstractDocument, convert_retrieval_results_to_str
from processor.core.ir_system.ir_state import IRState
from processor.core.ir_system.retriever.retriever_factory import (
    RetrieverType,
    RetrieverFactory,
)
from processor.model.interface.abstract_model import AbstractModel
from processor.model.llm_message import LLMMessage, Role

RETRIEVERS = [
    RetrieverType.PNEUMA,
    RetrieverType.KNOWLEDGE_BASE,
    RetrieverType.WEB_SEARCH,
]
RETRIEVER_INFO = [
    {"name": RetrieverType.PNEUMA, "description": "Retrieves relevant tabular data."},
    {
        "name": RetrieverType.KNOWLEDGE_BASE,
        "description": "Retrieves domain knowledge and user preferences (for a specific user) captured from the users.",
    },
    {
        "name": RetrieverType.WEB_SEARCH,
        "description": "Retrieves information from the internet.",
    },
]


class LMInterface:
    def __init__(self, models: dict[str, AbstractModel]):
        self.prompt_factory = IRPromptFactory()
        self.retriever_factory = RetrieverFactory(models)

        self.state = IRState()
        self.llm = models["llm"]

    def index_documents(
        self, retriever_type: RetrieverType, documents: list[AbstractDocument]
    ):
        """
        Indexes documents on a retriever.
        """
        print(f"Indexing documents on the retriever {retriever_type}.")
        self.retriever_factory.get_retriever(retriever_type).index(documents)
        print("Indexing process is done.")

    def get_relevant_retrievers(self, requirements: str) -> list[RetrieverType]:
        """
        Returns the list of relevant retrievers for the given requirements.
        """
        relevant_retrievers: list[RetrieverType] = []
        for i in RETRIEVER_INFO:
            messages = [
                LLMMessage(
                    role=Role.SYSTEM.value,
                    content=self.prompt_factory.get_retriever_classification_prompt(
                        requirements,
                        i["name"],
                        i["description"],
                    ),
                )
            ]
            classification_output = self.llm.chat(messages).strip().lower()
            if classification_output.startswith("yes"):
                relevant_retrievers.append(i["name"])

        if len(relevant_retrievers) == 0:
            # By default, use all retrievers if none is considered relevant by the LLM
            relevant_retrievers = [i["name"] for i in RETRIEVER_INFO]
        return relevant_retrievers

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
        return self.retrieve(retriever_type, refined_prompt, sources, k)
