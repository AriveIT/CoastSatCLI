from __future__ import annotations

from typing import Any, Dict

from ..context import PipelineContext
from ..helpers import run_batch_shoreline_detection
from ..stage import PipelineStage
from ..parameters import Parameters


class DetectionStage(PipelineStage):
    name = "detection"
    description = "Run shoreline detection."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        metadata = context.metadata.get("download") if context.metadata else None
        global_settings = context.require_settings()

        if metadata is None or params.shoreline_settings is None:
            raise RuntimeError(
                "DetectionStage requires shoreline_settigns and downloadd metadata."
            )

        output = run_batch_shoreline_detection(
            metadata,
            global_settings,
            params.shoreline_settings,
        )

        context.shoreline_output = output
        context.metadata["dowload"] = {"metadata": metadata}
