from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..context import PipelineContext
from ..stage import PipelineStage
from ..helpers.config import build_settings
from ..parameters import Parameters

class ConfigLoadStage(PipelineStage):
    name = "config"
    description = "Load and validate settings.json produced by the CLI."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        config_path = Path(context.config_path).expanduser().resolve()

        global_settings = build_settings(config_path, params.download_filters)
        
        context.global_settings = global_settings
        context.metadata["config_loaded"] = True
