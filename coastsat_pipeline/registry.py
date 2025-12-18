from __future__ import annotations

from typing import List

from .stage import PipelineStage
from .stages import (
    AnalysisStage,
    ConfigLoadStage,
    ImageryStage,
    ImprovedTransectsPlotStage,
    InitializationStage,
    SlopeEstimationStage,
    TideCorrectionStage,
    TimeSeriesPostProcessingStage,
    TrendCalculationStage,
)


def default_stages() -> List[PipelineStage]:
    """
    Default ordered set of pipeline stages.

    Each stage expects outputs from the previous stage to be present in
    PipelineContext (e.g., config -> init -> imagery -> analysis). When new
    stages are added, append them here in the order they should execute.
    """
    return [
        ConfigLoadStage(),
        InitializationStage(),
        ImageryStage(),
        AnalysisStage(),
        SlopeEstimationStage(),
        TideCorrectionStage(),
        ImprovedTransectsPlotStage(),
        TimeSeriesPostProcessingStage(),
        TrendCalculationStage(),
    ]
