from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from .context import PipelineContext
from .stage import PipelineStage
from .parameters import Parameters

from . import checkpoints

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Executes a sequence of pipeline stages.

    Responsibilities:
    - Honor each stage's should_run predicate.
    - Run/log each stage in order and surface progress markers for UIs.
    - Leave populated context for downstream consumers.
    """

    def __init__(self, stages: Iterable[PipelineStage]):
        self.stages: List[PipelineStage] = list(stages)

    def run(self, context: PipelineContext) -> None:
        params = Parameters()
        total_stages = len(self.stages)
        if total_stages == 0:
            print("PROGRESS: 100%")
            return

        for idx, stage in enumerate(self.stages):
            ran = False
            if not stage.should_run(context):
                logger.info("Skipping stage %s", stage.name)
            else:
                checkpoints.save_context(context, stage.name)
                print(f"RUNNING: {stage.name}")
                stage.log_start()
                stage.run(context, params)
                stage.log_end()
                ran = True

            pct = int(((idx + 1) / total_stages) * 100)
            print(f"STAGE: {stage.name} ({'done' if ran else 'skipped'})")
            print(f"PROGRESS: {pct}%")


def run_pipeline(context: PipelineContext, stages: Iterable[PipelineStage]) -> PipelineContext:
    runner = PipelineRunner(stages)
    runner.run(context)
    return context
