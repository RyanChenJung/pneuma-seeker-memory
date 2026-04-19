# Architecture Overview

![The Architecture of Pneuma-Seeker](figures/pneuma_seeker.png)

`Pneuma-Seeker` is designed around a modular architecture that separates high-level orchestration ([Conductor](../src/pneuma_seeker/services/core/conductor/main.py)), data retrieval ([Retriever](../src/pneuma_seeker/services/core/ir_system/main.py)), and materialization ([Materializer](../src/pneuma_seeker/services/core/materializer/main.py)) from supporting infrastructure services—for langauge model access ([LMService](../src/pneuma_seeker/services/language_model/model_factory.py)), data management ([DBService](../src/pneuma_seeker/services/db/main.py)), and indexing ([IndexingService](../src/pneuma_seeker/services/indexing/main.py)). This separation enables both scalability and controlled context management for LLM-based data interaction.
