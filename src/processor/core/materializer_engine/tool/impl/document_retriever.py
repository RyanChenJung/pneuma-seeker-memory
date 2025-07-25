from logging import Logger
from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.tool.abstract_tool import AbstractTool
from processor.model.interface.abstract_model import AbstractModel


class DocumentRetriever(AbstractTool):
    def __init__(
        self, llm: AbstractModel, embed_model: AbstractModel, logger: Logger
    ) -> None:
        super().__init__()
        self.llm = llm
        self.embed_model = embed_model
        self.logger = logger

    def execute(
        self, argument: str, **kwargs
    ) -> dict[RetrieverType, list[AbstractDocument]]:
        # Argument is the prompt
        ir_system = LMInterface(
            {
                "llm": self.llm,
                "embed_model": self.embed_model,
            },
            self.logger,
        )
        return ir_system.retrieve_documents(argument, ["buysite"], 10)

    def describe(self) -> str:
        return """{"name": "Document Retriever", "Description": "Retrieves relevant documents from the document store", "Parameters": {"inputs": ["Search query string"]}}"""
