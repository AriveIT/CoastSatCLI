from __future__ import annotations

from typing import Any, Dict

from ..context import PipelineContext
from ..helpers.imagery import run_batch_shoreline_detection
from ..stage import PipelineStage
from ..parameters import Parameters


class ImageryStage(PipelineStage):
    name = "imagery"
    description = "Download/preprocess imagery and run shoreline detection."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        metadata = context.metadata.get("initialization") if context.metadata else None
        global_settings = context.require_settings()

        if metadata is None or params.shoreline_settings is None:
            raise RuntimeError(
                "ImageryStage requires shoreline_settigns and initialization metadata."
            )

        output = run_batch_shoreline_detection(
            metadata,
            global_settings,
            params.shoreline_settings,
        )

        context.shoreline_output = output
        context.metadata["imagery"] = {"metadata": metadata}
