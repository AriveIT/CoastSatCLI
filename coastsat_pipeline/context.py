from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TideFilterConfig:
    lower_percentile: float
    upper_percentile: float


@dataclass
class TideConfig:
    mode: str  # "fes", "csv", or "none"
    fes_config: Optional[Path] = None
    tide_csv_path: Optional[Path] = None
    reference_elevation: Optional[float] = None
    beach_slope: Optional[float] = None
    tide_filter: Optional[TideFilterConfig] = None


@dataclass
class InputsConfig:
    sitename: str
    aoi_path: Path
    reference_shoreline: Path
    transects: Path
    shoreline_path: Optional[Path] = None


@dataclass
class Settings:
    raw: Dict[str, Any]
    inputs: InputsConfig
    output_dir: Path
    output_epsg: int
    tide: TideConfig


@dataclass
class PipelineContext:
    """
    Shared state passed between pipeline stages.
    """

    config_path: Path
    cli_options: Dict[str, Any] = field(default_factory=dict)
    settings: Optional[Settings] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    inputs_config: Optional[Dict[str, Any]] = None
    analysis_settings: Optional[Dict[str, Any]] = None
    geometry_info: Optional[Dict[str, Any]] = None
    imagery_metadata: Optional[Any] = None
    shoreline_output: Optional[Any] = None
    cross_distance: Optional[Any] = None
    transects: Optional[Any] = None
    dates_sat: Optional[Any] = None
    tides_sat: Optional[Any] = None
    slope_est: Optional[Any] = None
    slope_artifacts: List[Path] = field(default_factory=list)
    cross_distance_tidally_corrected: Optional[Any] = None
    tide_stats: Optional[Dict[str, Any]] = None
    plot_artifacts: List[Path] = field(default_factory=list)
    cross_distance_processed: Optional[Any] = None
    trend_dict: Optional[Any] = None
    trend_results: Optional[Any] = None

    def require_settings(self) -> Settings:
        if self.settings is None:
            raise RuntimeError("PipelineContext settings accessed before initialization.")
        return self.settings
