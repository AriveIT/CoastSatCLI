from __future__ import annotations

import gc
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz
import pyfes
from shapely.geometry import Polygon

from coastsat import SDS_slope, SDS_tools, SDS_transects

@dataclass
class SlopeOptions:
    save_figures: bool = True
    cache_dir_name: str = "slope_estimation"

def run_slope_estimation(
    settings: Dict[str, Any],
    cross_distance: Dict[str, Any],
    output: Dict[str, Any],
    options: SlopeOptions | None = None,
) -> Tuple[Dict[str, float], list[Any], np.ndarray]:
    options = options or SlopeOptions()
    fp_slopes = os.path.join(settings["inputs"]["filepath"], options.cache_dir_name)
    os.makedirs(fp_slopes, exist_ok=True)

    centroid, dates_ts, tides_ts, dates_sat, tides_sat = _compute_tides(settings, output)

    (
        filtered_dates_sat,
        filtered_tides_sat,
        filtered_cross_distance,
        tide_stats,
    ) = _apply_tide_filters(settings, dates_ts, tides_ts, dates_sat, tides_sat, cross_distance, output)

    slope_est, cis = _estimate_slopes(
        fp_slopes,
        filtered_dates_sat,
        filtered_tides_sat,
        filtered_cross_distance,
        options.save_figures,
    )

    settings["tide_filter_stats"] = {**settings.get("tide_filter_stats", {}), **tide_stats}
    return slope_est, dates_sat, tides_sat

def _compute_tides(settings: Dict[str, Any], output: Dict[str, Any]):
    handlers = pyfes.load_config(settings["inputs"]["fes_config"])
    ocean_tide = handlers["tide"]
    load_tide = handlers["radial"]

    aoi_geom = Polygon(settings["inputs"]["polygon"][0])
    centroid = SDS_tools.select_valid_centroid(aoi_geom, ocean_tide, load_tide)

    date_range = [
        pytz.utc.localize(datetime(2020, 1, 1)),
        pytz.utc.localize(datetime(2025, 1, 1)),
    ]
    timestep = 900
    dates_ts, tides_ts = SDS_slope.compute_tide(centroid, date_range, timestep, ocean_tide, load_tide)

    dates_sat = output["dates"]
    tides_sat = np.asarray(
        SDS_slope.compute_tide_dates(centroid, dates_sat, ocean_tide, load_tide),
        dtype=float,
    )

    del ocean_tide, load_tide
    gc.collect()

    return centroid, dates_ts, tides_ts, dates_sat, tides_sat


def _apply_tide_filters(
    settings: Dict[str, Any],
    dates_ts,
    tides_ts,
    dates_sat,
    tides_sat,
    cross_distance,
    output
):
    tide_filter_cfg = settings.get("tide_filter")
    tide_filter_mask, tide_thresholds = _get_percentile_tide_mask(tide_filter_cfg, tides_sat, tides_ts)

    date_start = pytz.utc.localize(datetime(2020, 1, 1))
    date_end = pytz.utc.localize(datetime(2025, 1, 1))
    dates_mask = _get_dates_mask(date_start, date_end, dates_sat)

    combined_mask = dates_mask & tide_filter_mask if tide_filter_cfg else dates_mask
    combined_mask &= _get_no_S2_mask(output) # remove noisy S2 data
    
    selected_indices = np.where(combined_mask)[0]
    if selected_indices.size == 0:
        selected_indices = np.where(dates_mask)[0] if np.any(dates_mask) else np.arange(len(dates_sat))
        print("No acquisition dates fall within the slope estimation window; removing tide filters or using all dates instead.")

    # use combined_mask to filter data
    settings.setdefault("tide_filter_stats", {})["used_for_slopes"] = int(selected_indices.size)
    filtered_dates_sat = [dates_sat[i] for i in selected_indices]
    filtered_tides_sat = tides_sat[selected_indices]
    filtered_cross_distance = {
        key: cross_distance[key][selected_indices] for key in cross_distance.keys()
    }

    return filtered_dates_sat, filtered_tides_sat, filtered_cross_distance, tide_thresholds

def _get_percentile_tide_mask(tide_filter_cfg, tides_sat, tides_ts):
    tide_filter_mask = np.ones_like(tides_sat, dtype=bool)
    tide_thresholds = {}
    if tide_filter_cfg:
        source_series = np.asarray(tides_ts, dtype=float)
        lower_pct = tide_filter_cfg.get("lower_percentile")
        upper_pct = tide_filter_cfg.get("upper_percentile")

        if lower_pct is not None:
            lower_thresh = float(np.nanpercentile(source_series, lower_pct))
            tide_thresholds["lower_threshold"] = lower_thresh
            tide_filter_mask &= tides_sat >= lower_thresh
        if upper_pct is not None:
            upper_thresh = float(np.nanpercentile(source_series, upper_pct))
            tide_thresholds["upper_threshold"] = upper_thresh
            tide_filter_mask &= tides_sat <= upper_thresh

        removed = int(np.count_nonzero(~tide_filter_mask))
        total = int(tides_sat.size)
        tide_thresholds["removed_acquisitions"] = removed
        tide_thresholds["total_acquisitions"] = total
    return tide_filter_mask, tide_thresholds

# get all dates in given range in utc time zone
def _get_dates_mask(date_start, date_end, dates_sat):
    normalized_dates: list[datetime] = [
        _ensure_aware(raw_date) for raw_date in dates_sat
    ]
    return np.array(
        [date_start < aware < date_end for aware in normalized_dates],
        dtype=bool,
    )

def _ensure_aware(date):
    if not isinstance(date, datetime):
        date = pd.to_datetime(date).to_pydatetime()

    if date.tzinfo is None or date.tzinfo.utcoffset(date) is None:
        return pytz.utc.localize(date)
    return date.astimezone(pytz.utc)

def _get_no_S2_mask(output: Dict[str, Any]) -> np.array:
    return np.array([sat != 'S2' for sat in output['satname']], dtype=bool)

def _estimate_slopes(
    fp_slopes: str,
    filtered_dates_sat,
    filtered_tides_sat,
    filtered_cross_distance,
    save_figures: bool,
):
    settings_slope = {
        'slope_min': 0.005,
        'slope_max': 0.4,
        'delta_slope': 0.005,
        'n0': 50,
        'freq_cutoff': 1. / (24 * 3600 * 30),  # 30-day frequency
        'delta_f': 100 * 1e-10,
        'prc_conf': 0.05,
        'plot_fig': save_figures,
        'n_days': 8
    }

    # get range of beach slopes for power_spectrum
    beach_slopes = SDS_slope.range_slopes(settings_slope['slope_min'], settings_slope['slope_max'], settings_slope['delta_slope'])

    if len(filtered_dates_sat) > 1:
        try:
            SDS_slope.plot_timestep(filtered_dates_sat)
        except Exception as exc:
            print(f"Warning: unable to plot timestep distribution after filtering: {exc}")
        else:
            fig = plt.gcf()
            fig.savefig(os.path.join(fp_slopes, '0_timestep_distribution.jpg'), dpi=200)
            plt.close(fig)

        try:
            freq_band = SDS_slope.find_tide_peak(filtered_dates_sat, filtered_tides_sat, settings_slope)
        except Exception as exc:
            print(f"Warning: unable to compute tidal frequency band after filtering: {exc}")
        else:
            fig = plt.gcf()
            fig.savefig(os.path.join(fp_slopes, '1_tides_power_spectrum.jpg'), dpi=200)
            plt.close(fig)
    else:
        print("Not enough acquisition dates to characterize timestep distribution after filtering.")

    if freq_band is not None:
        settings_slope['freqs_max'] = freq_band

    slope_est, cis = {}, {}
    for key in filtered_cross_distance.keys():
        try:
            idx_nan = np.isnan(filtered_cross_distance[key])
            dates = [filtered_dates_sat[i] for i in range(len(filtered_dates_sat)) if not idx_nan[i]]
            tide = np.array(filtered_tides_sat)[~idx_nan]
            composite = np.array(filtered_cross_distance[key])[~idx_nan]

            tsall = SDS_slope.tide_correct(composite, tide, beach_slopes)
            if len(dates) == 0 or len(tsall) == 0:
                print(f"Skipping transect {key} due to empty data.")
                print(f"Setting default slope for {key} to 0.1 due to error.")
                slope_est[key], cis[key] = 0.1, (0.1, 0.1)
                continue
            
            slope_est[key], cis[key] = SDS_slope.integrate_power_spectrum(dates, tsall, settings_slope, key)
            if save_figures:
                plt.gcf().savefig(os.path.join(fp_slopes, f"2_energy_curve_{key}.jpg"), dpi=200)
                plt.close()
                SDS_slope.plot_spectrum_all(dates, composite, tsall, settings_slope, slope_est[key])
                plt.gcf().savefig(os.path.join(fp_slopes, f"3_slope_spectrum_{key}.jpg"), dpi=200)
                plt.close()
            print(f"  → {key}: Estimated slope = {slope_est[key]:.3f} m (CI: {cis[key][0]:.4f} – {cis[key][1]:.4f})")
        except Exception as e:
            print(f'Error processing {key}: {e}')
            print(f"Setting default slope for {key} to 0.1 due to error.")
            slope_est[key], cis[key] = 0.1, (0.1, 0.1)
    return slope_est, cis