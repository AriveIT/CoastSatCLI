"""
Stage implementations for the new pipeline.
"""

from .config_stage import ConfigLoadStage  # noqa: F401
from .download_stage import DownloadStage  # noqa: F401
from .detection_stage import DetectionStage  # noqa: F401
from .analysis_stage import AnalysisStage  # noqa: F401
from .slope_stage import SlopeEstimationStage  # noqa: F401
from .tide_stage import TideCorrectionStage  # noqa: F401
from .timeseries_stage import TimeSeriesPostProcessingStage  # noqa: F401
from .trends_stage import TrendCalculationStage  # noqa: F401
