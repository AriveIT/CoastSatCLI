from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from datetime import datetime
import pytz

@dataclass
class ImageryOptions:
    save_geojson: bool = False # save extracted shorelines to geojson
    save_plots: bool = True # plots all extracted shorelines in different colours
    cache_enabled: bool = True # Try loading <sitename>_output.pkl file to skip shoreline extraction
    skip_existing_jpg: bool = True # skip creating jpg that already exist

@dataclass
class AnalysisOptions:
    plot_transects: bool = True # plots all extracted shorelines and all transects
    plot_time_series: bool = True # saves time series of each transect (currently illegible for any reasonable number of transects)
    write_csv: bool = True # saves time series data to csv file (after outlier rejection)

@dataclass
class SlopeOptions:
    save_figures: bool = True # plots energy curves and slope spectrum
    cache_dir_name: str = "slope_estimation" # directory for slope plots

@dataclass
class TideOptions:
    reference_elevation: float = 0.0 # elevation of reference shoreline
    write_csv: bool = True # saves tidally corrected time series data to csv file
    beach_slope: Optional[float] = None # default beach slope for csv tidal correction if one not provided by user

@dataclass
class PlottingOptions:
    trend_min: float = -30.0 # set range for plotting transects_colored_by_trend (currently transects aren't visible)
    trend_max: float = 30.0
    cmap_name: str = "RdBu_r" # colour bar
    dpi: int = 300

@dataclass
class TimeSeriesOptions:
    """Tuning switches for time-series post-processing outputs."""
    write_csv: bool = False # would overwrite file made earlier in pipeline...
    save_seasonal_plots: bool = True # save plot for each transect with one point per season
    save_monthly_plots: bool = True # save plot for each transect with one point per month


@dataclass
class Parameters:
    #####################
    # Initialization
    #####################
    # Note: these parameters only affect downloads. Analysis is unaffected (it is performed on anything already downloaded)
    download_filters = {
        'dates': ["1984-01-01", "2025-01-01"], # range of dates of aquisitions to be downloaded
        'sat_list': ["L5", "L7", "L8", "L9"], # satellite missions to download images from
        # 'excluded_epsg_codes': ['32609'], # exclude images with given epsg codes
        # 'LandsatWRS': '055022', # specify a Landsat tile (WRS path/row)
        # 'S2tile': '09UVA', # specifies an S2 tile
        # 'months': [7, 8, 9, 10], # include only images taken in given months
        # 'skip_L7_SLC': True # skip L7 after Scan-Line-Correction failure
    }

    analysis_settings = {
        "cloud_thresh": 0.2, # percentage of image that can be covered by cloud
        "dist_clouds": 50, # distance in metres defining a buffer around cloudy pixels where the shoreline cannot be mapped
        "check_detection": False, # if True, lets user manually accept/reject the mapped shorelines
        "adjust_detection": False, # lets user adjust the detected shorelines with a slide bar.
        "save_figure": True, # this has to be true for ANY figures to be saved
        "min_beach_area": 500, # minimum number of pixels that have to be connected to belong to the SAND class
        "min_length_sl": 250, # minimum length of shoreline perimeter to be kept (in meters)
        "cloud_mask_issue": False, # switch this parameter to True if sand pixels are masked (in black) on many images
        "sand_color": "default", # classification model: 'default', 'latest', 'dark' (for grey/black sand beaches) or 'bright' (for white sand beaches)
        "pan_off": False, # True to switch pansharpening off for Landsat 7/8/9 imagery
        "s2cloudless_prob": 20, # Threshold to identify cloud pixels in the s2cloudless probability mask (s2 cloud mask is not 1 and 0, but a probability [0,100))
        "max_dist_ref" : 500, # maximum distance from the reference shoreline in meters
    }

    #####################
    # Analysis
    #####################
    transect_settings = {
        "along_dist": 25, # how far a point can be orthogonally to transect line
        "d_origin_threshold": 200, # distance a shoreline points can be from transect origin and be counted as an intersection
        "min_points": 3, # minimum number of points to calculate an intersections
        "max_std": 15, # maximum standard deviation of intersections per transect (exceptions are dealt with according to multiple_inter)
        "max_range": 30, # maximum range of intersections per transect (exceptions are dealt with according to multiple_inter)
        "min_chainage": -100, # furthest landward of the transect origin that an intersection is accepted
        
        # method of dealing with transect/shorelines with large dispersion ('auto', 'nan', 'max')
        # nan = set values to nan
        # max = use maximum intersection
        # auto = if more than auto_prc% of intersections for a given transect (across shorelines) have std>max_std, use maximum intersection
        "multiple_inter": "max",

        # percentage to use in 'auto' mode to blend between 'nan' and 'max'
        # auto_prc = 0.0 --> max
        # auto_prc = 1.0 --> nan
        "auto_prc": 0.1, 
    }

    outlier_settings = {
        "max_cross_change": 40, # maximum cross-shore change allowed between consecutive timesteps
        "otsu_threshold": [-0.5, 0], # min and max intensity threshold use for contouring the shoreline
        "plot_fig": False, # display time series before and after outlier rejection for each transect (doesn't save figs)
    }
    
    # passed to SDS_tools.remove_inaccurate_georef
    georef_accuracy_tolerance = 10 # minimum horizontal georeferencing accuracy (metres) for a shoreline to be accepted

    #####################
    # Slope Estimation
    #####################
    # date range used specifically for slope estimation. Should have at least 2 satellite data available
    slope_estimation_date_range = [
        pytz.utc.localize(datetime(2020, 1, 1)),
        pytz.utc.localize(datetime(2025, 1, 1)),
    ]
    tide_timestep = 900 # compute tide level in date range at intervals of timestep seconds

    slope_settings = {
        'plot_fig': SlopeOptions().save_figures, # save slope estimation figures

        # beach slopes generated from slope_min to slope_max at intervals of delta_slope
        'slope_min': 0.005,
        'slope_max': 0.4,
        'delta_slope': 0.005,

        # parameters for slope estimation. Do not touch unless you understand the process
        'n0': 50,
        'freq_cutoff': 1. / (24 * 3600 * 30),  # 30-day frequency
        'delta_f': 100 * 1e-10,
        'prc_conf': 0.05, # confidence 
        'n_days': 8
    }

    # this is also used in tide.py and trends.py
    default_slope = 0.1 # default slope used when error occurs in slope estimation