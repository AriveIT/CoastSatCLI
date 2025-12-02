"""
CoastSat pipeline refactor package.

This package hosts the new pipeline runner, context dataclasses, and stage
implementations that will eventually replace the legacy Complete_Analysis
scripts. The code is intentionally modular so we can migrate stage-by-stage.
"""

from .context import PipelineContext  # noqa: F401
from .runner import PipelineRunner  # noqa: F401
