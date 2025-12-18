from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TideFilterConfig:
    """Optional percentile filter applied to tide series."""
    lower_percentile: float
    upper_percentile: float


@dataclass
class TideConfig:
    """Normalized tide configuration from settings.json."""
    mode: str  # "fes", "csv", or "none"
    fes_config: Optional[Path] = None
    tide_csv_path: Optional[Path] = None
    reference_elevation: Optional[float] = None
    beach_slope: Optional[float] = None
    tide_filter: Optional[TideFilterConfig] = None


@dataclass
class InputsConfig:
    """Input file references for a site."""
    sitename: str
    aoi_path: Path
    reference_shoreline: Path
    transects: Path
    shoreline_path: Optional[Path] = None


@dataclass
class Settings:
    """Typed settings view loaded from settings.json."""
    raw: Dict[str, Any]
    inputs: InputsConfig
    output_dir: Path
    output_epsg: int
    tide: TideConfig


@dataclass
class PipelineContext:
    """
    Shared state passed between pipeline stages.

    Each stage reads/writes attributes here instead of returning large tuples.
    Stages should check for required fields (or use require_settings) before
    proceeding. Keep additions backwards compatible: prefer adding new fields
    over mutating existing ones.
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
