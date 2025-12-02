from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from .context import PipelineContext
from .stage import PipelineStage

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Executes a sequence of pipeline stages.
    """

    def __init__(self, stages: Iterable[PipelineStage]):
        self.stages: List[PipelineStage] = list(stages)

    def run(self, context: PipelineContext) -> None:
        for stage in self.stages:
            if not stage.should_run(context):
                logger.info("Skipping stage %s", stage.name)
                continue
            stage.log_start()
            stage.run(context)
            stage.log_end()


def run_pipeline(context: PipelineContext, stages: Iterable[PipelineStage]) -> PipelineContext:
    runner = PipelineRunner(stages)
    runner.run(context)
    return context
