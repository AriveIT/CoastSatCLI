from __future__ import annotations

from typing import Any, Dict

from ..context import PipelineContext
from ..helpers.imagery import run_batch_shoreline_detection
from ..stage import PipelineStage


class ImageryStage(PipelineStage):
    name = "imagery"
    description = "Download/preprocess imagery and run shoreline detection."

    def run(self, context: PipelineContext) -> None:
        inputs = context.inputs_config
        settings = context.analysis_settings
        metadata = context.metadata.get("initialization") if context.metadata else None

        if inputs is None or settings is None or metadata is None:
            raise RuntimeError(
                "ImageryStage requires inputs_config, analysis_settings, and initialization metadata."
            )

        output = run_batch_shoreline_detection(metadata, settings, inputs)
        context.shoreline_output = output
        context.metadata["imagery"] = {"metadata": metadata}
