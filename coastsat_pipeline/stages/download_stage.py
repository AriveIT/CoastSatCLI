from __future__ import annotations

from typing import Any, Dict

from ..context import PipelineContext
from ..helpers.download import download_images
from ..stage import PipelineStage
from ..parameters import Parameters

class DownloadStage(PipelineStage):
    name = "Download"
    description = "Download imagery"

    def run(self, context: PipelineContext, params: Parameters) -> None:
        global_settings = context.require_settings()
        metadata = download_images(
            global_settings,
            params.download_filters,
        )

        context.metadata["download"] = metadata
