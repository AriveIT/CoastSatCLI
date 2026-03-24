from __future__ import annotations

from typing import Any, Dict

from ..context import PipelineContext
from ..helpers.initialization import download_images
from ..stage import PipelineStage
from ..parameters import Parameters

class InitializationStage(PipelineStage):
    name = "initialization"
    description = "Prepare CoastSat inputs/settings structures for downstream stages."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        global_settings = context.require_settings()
        metadata = download_images(
            global_settings,
            params.download_filters,
        )

        context.metadata["initialization"] = metadata
