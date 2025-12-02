"""
Stage implementations for the new pipeline.
"""

from .config_stage import ConfigLoadStage  # noqa: F401
from .initialization_stage import InitializationStage  # noqa: F401
from .imagery_stage import ImageryStage  # noqa: F401
from .analysis_stage import AnalysisStage  # noqa: F401
from .slope_stage import SlopeEstimationStage  # noqa: F401
from .tide_stage import TideCorrectionStage  # noqa: F401
from .plot_stage import ImprovedTransectsPlotStage  # noqa: F401
from .timeseries_stage import TimeSeriesPostProcessingStage  # noqa: F401
from .trends_stage import TrendCalculationStage  # noqa: F401
