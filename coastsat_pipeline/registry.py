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
    Factory returning the default stage sequence.
    Currently includes the implemented stages; more will be added as they migrate.
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
