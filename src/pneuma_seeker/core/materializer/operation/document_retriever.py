from logging import Logger
from pneuma_seeker.core.ir_system.data_model import AbstractDocument, RetrieverType
from pneuma_seeker.core.ir_system.main import IRSystem
from pneuma_seeker.model.interface.abstract_model import AbstractModel


def get_documents(
    llm: AbstractModel,
    embed_model: AbstractModel,
    logger: Logger,
    prompt: str,
    source_datasets: list[str],
) -> dict[RetrieverType, list[AbstractDocument]]:
    ir_system = IRSystem(
        {
            "llm": llm,
            "embed_model": embed_model,
        },
        logger,
    )
    return ir_system.retrieve_documents(prompt, source_datasets, 10)
