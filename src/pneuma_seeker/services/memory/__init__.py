"""Memory-layer plugin (🟢 ours). Decoupled from Pneuma core; toggled by
``ENABLE_MEMORY_INJECTION`` (default off). See ``docs_memory/`` for the design."""

from pneuma_seeker.services.memory.injector import MemoryInjector

__all__ = ["MemoryInjector"]
