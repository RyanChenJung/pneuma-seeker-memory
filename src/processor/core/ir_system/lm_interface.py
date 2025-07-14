from processor.core.ir_system.ir_prompt_factory import IRPromptFactory
from processor.core.ir_system.ir_data_model import AbstractDocument
from processor.core.ir_system.ir_state import IRState
from processor.core.ir_system.retriever.retriever_factory import (
    RetrieverType,
    RetrieverFactory,
)
from processor.model.interface.abstract_model import AbstractModel
from processor.model.llm_message import LLMMessage, Role


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
    def __init__(self, llm: AbstractModel, models: dict[str, str]):
        self.prompt_factory = IRPromptFactory()
        self.retriever_factory = RetrieverFactory(models)

        self.state = IRState()
        self.llm = llm

    def index_documents(
        self, retriever_type: RetrieverType, documents: AbstractDocument
    ):
        """
        Indexes documents on a retriever.
        """
        print(f"Indexing documents on the retriever {retriever_type}.")
        self.retriever_factory.get_retriever(retriever_type).index(documents)
        print("Indexing process is done.")

    def retrieve(self, requirements: str) -> list[AbstractDocument]:
        """
        Retrieves documents from the retrievers in an intelligent manner.

        - requirements (str): First the initial query, subsequently feedback to improve
        the results by adjusting the initial query.
        """
        # Assume the retrievers to be used are only determined once in the beginning
        if len(self.state.relevant_retrievers) == 0:
            # Consider which retrievers to use.
            # Future-TODO: Parallelization
            for i in RETRIEVER_INFO:
                messages = [
                    LLMMessage(
                        role=Role.SYSTEM,
                        content=self.prompt_factory.get_retriever_classification_prompt(
                            requirements,
                            i["name"],
                            i["description"],
                        ),
                    )
                ]
                classification_output = self.llm.chat(messages).strip().lower()
                if classification_output.startswith("yes"):
                    self.state.relevant_retrievers.append(i["name"])

        if len(self.state.relevant_retrievers) == 0:
            # By default, use all retrievers if none is considered relevant by the LLM
            self.state.relevant_retrievers = [i["name"] for i in RETRIEVER_INFO]

        # Step 1: Create/adjust the prompt
        # Future-TODO: More granular adjustments for each retriever
        sys_prompt = self.prompt_factory.get_new_retrieve_prompt(requirements)
        if self.state.current_query != "":
            sys_prompt = self.prompt_factory.get_refine_retrieval_prompt(
                self.state.current_query, requirements
            )

        actual_retrieval_prompt = self.llm.chat(
            [LLMMessage(role=Role.SYSTEM, content=sys_prompt)]
        )
        self.state.current_query = actual_retrieval_prompt

        # Step 2: Call the retrievers and return the results
        documents = []
        for retriever_name in self.state.relevant_retrievers:
            retriever = self.retriever_factory.get_retriever(retriever_name)
            documents.extend(retriever.retrieve(actual_retrieval_prompt))
        return documents
