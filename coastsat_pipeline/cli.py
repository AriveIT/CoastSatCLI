from __future__ import annotations

from pathlib import Path

from .context import PipelineContext
from .registry import default_stages
from .runner import PipelineRunner


def run_pipeline_from_config(config_path: Path) -> None:
    """
    Execute the new pipeline using the default stage registry.
    """
    context = PipelineContext(config_path=Path(config_path).expanduser().resolve())
    runner = PipelineRunner(default_stages())
    runner.run(context)
