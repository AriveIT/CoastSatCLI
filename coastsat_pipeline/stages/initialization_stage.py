from __future__ import annotations

from typing import Any, Dict

from ..context import PipelineContext
from ..helpers.initialization import prepare_initial_settings
from ..stage import PipelineStage
from ..parameters import Parameters

class InitializationStage(PipelineStage):
    name = "initialization"
    description = "Prepare CoastSat inputs/settings structures for downstream stages."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        settings = context.require_settings()
        inputs, analysis_settings, metadata = prepare_initial_settings(
            settings.raw,
            params.download_filters,
            params.shoreline_settings
        )

        context.inputs_config = inputs
        context.analysis_settings = analysis_settings
        context.metadata["initialization"] = metadata
