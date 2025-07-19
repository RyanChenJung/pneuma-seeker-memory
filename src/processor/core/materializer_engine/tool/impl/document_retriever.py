from processor.core.ir_system.ir_data_model import AbstractDocument, RetrieverType
from processor.core.ir_system.lm_interface import LMInterface
from processor.core.materializer_engine.tool.abstract_tool import AbstractTool


class DocumentRetriever(AbstractTool):
    def __init__(self) -> None:
        super().__init__()

    def execute(self, argument: str, **kwargs) -> dict[RetrieverType, list[AbstractDocument]]:
        # Argument is the prompt
        if "llm" not in kwargs or "embed_model" not in kwargs:
            raise ValueError("You need to provide both an LLM and an embedding model.")
        ir_system = LMInterface({"llm": kwargs["llm"], "embed_model": kwargs["embed_model"]})
        return ir_system.retrieve_documents(argument, ["buysite"], 10)

    def describe(self) -> str:
        return "Retrieves top-10 documents (can be table, text, etc.) from each of n retrievers, which means that there are n*10 documents in total."
