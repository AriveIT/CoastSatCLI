from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from .context import PipelineContext
from .parameters import Parameters

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """
    Base class for stages.

    Contract:
    - Implement run(context) to perform work and populate context.
    - Override should_run(context) when a stage can be skipped based on inputs.
    - Use log_start/log_end for consistent progress messages.
    """

    name: str = "stage"
    description: str = ""

    def should_run(self, context: PipelineContext, params:Parameters) -> bool:
        return True

    @abstractmethod
    def run(self, context: PipelineContext, params: Parameters) -> None:
        ...

    def log_start(self) -> None:
        logger.info("Starting stage %s", self.name)

    def log_end(self) -> None:
        logger.info("Finished stage %s", self.name)
