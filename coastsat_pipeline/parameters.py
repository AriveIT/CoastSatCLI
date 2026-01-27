from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from datetime import datetime
import pytz

@dataclass
class ImageryOptions:
    save_geojson: bool = True
    save_plots: bool = True
    cache_enabled: bool = True
    skip_existing_jpg: bool = True

@dataclass
class AnalysisOptions:
    plot_transects: bool = True
    plot_time_series: bool = True
    write_csv: bool = True

@dataclass
class SlopeOptions:
    save_figures: bool = True
    cache_dir_name: str = "slope_estimation"

@dataclass
class TideOptions:
    reference_elevation: float = 0.0
    write_csv: bool = True
    beach_slope: Optional[float] = None

@dataclass
class PlottingOptions:
    trend_min: float = -30.0
    trend_max: float = 30.0
    cmap_name: str = "RdBu_r"
    dpi: int = 300

@dataclass
class TimeSeriesOptions:
    """Tuning switches for time-series post-processing outputs."""
    write_csv: bool = False # would overwrite file made earlier in pipeline...
    save_seasonal_plots: bool = True
    save_monthly_plots: bool = True

@dataclass
class Options:
    imageryOptions = ImageryOptions()
    analysisOptions = AnalysisOptions()
    slopeOptions = SlopeOptions()
    tideOptions = TideOptions()
    plottingOptions = PlottingOptions()
    timeSeriesOptions = TimeSeriesOptions()


@dataclass
class Parameters:
    #####################
    # Initialization
    #####################
    download_date_range = ["1984-01-01", "2025-01-01"]
    sat_list = ["L5", "L7", "L8", "L9"]

    analysis_settings = {
        "cloud_thresh": 0.2,
        "dist_clouds": 50,
        "check_detection": False,
        "adjust_detection": False,
        "save_figure": True,
        "min_beach_area": 500,
        "min_length_sl": 250,
        "cloud_mask_issue": False,
        "sand_color": "default",
        "pan_off": False,
        "s2cloudless_prob": 20,
        "max_dist_ref" : 500,
    }

    #####################
    # Analysis
    #####################
    transects_settings = {
        "along_dist": 25,
        "min_points": 3,
        "max_std": 15,
        "max_range": 30,
        "min_chainage": -100,
        "multiple_inter": "max",
        "auto_prc": 0.1,
    }

    outliers_settings = {
        "max_cross_change": 40,
        "otsu_threshold": [-0.5, 0],
        "plot_fig": False,
    }
    
    # passed to SDS_tools.remove_inaccurate_georef
    georef_accuracy_tolerance = 10 # minimum horizontal georeferencing accuracy (metres) for a shoreline to be accepted

    # SDS_transects
    d_origin_threshold = 200 # distance a shoreline points can be from transect origin and be counted as an intersection (used in 2 places)

    #####################
    # Slope Estimation
    #####################
    # date range used specifically for slope estimation. Should have at least 2 satellite data available
    slope_estimation_date_range = [
        pytz.utc.localize(datetime(2020, 1, 1)),
        pytz.utc.localize(datetime(2025, 1, 1)),
    ]
    tide_timestep = 900 # compute tide level in date range at intervals of timestep seconds

    settings_slope = {
        'slope_min': 0.005,
        'slope_max': 0.4,
        'delta_slope': 0.005,
        'n0': 50,
        'freq_cutoff': 1. / (24 * 3600 * 30),  # 30-day frequency
        'delta_f': 100 * 1e-10,
        'prc_conf': 0.05,
        'plot_fig': SlopeOptions().save_figures,
        'n_days': 8
    }

    # this is also used in tide.py and trends.py
    default_slope = 0.1 # default slope used when error occurs in slope estimation