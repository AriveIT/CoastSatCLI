from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from coastsat import SDS_tools


@dataclass
class TideOptions:
    reference_elevation: float = 0.0
    write_csv: bool = True
    beach_slope: Optional[float] = None


def apply_tide_correction(
    output: Dict[str, Any],
    cross_distance: Dict[str, np.ndarray],
    transects: Dict[str, Any],
    settings: Dict[str, Any],
    slope_est: Dict[str, float],
    dates_sat,
    tides_sat,
    options: TideOptions | None = None,
) -> Dict[str, np.ndarray]:
    """
    Apply tide correction using either FES-derived tides or user-provided CSV tides.
    """
    options = options or TideOptions()
    tide_inputs = settings["inputs"]
    print("[Tide] Starting correction stage.")
    print(f"[Tide] Inputs mode: {'csv' if tide_inputs.get('tide_csv_path') else 'fes'}")
    print(f"[Tide] Transects: {len(transects)}, cross_distance keys: {len(cross_distance)}")
    if tide_inputs.get("tide_csv_path"):
        return _apply_csv_tide_correction(output, cross_distance, settings, options)

    # use FES-derived tides
    reference_elevation = options.reference_elevation
    cross_distance_tidally_corrected: Dict[str, np.ndarray] = {}
    for key in cross_distance.keys():
        common_length = min(len(dates_sat), len(tides_sat), len(cross_distance[key]))
        truncated_tides = tides_sat[:common_length]
        truncated_cross = cross_distance[key][:common_length]
        transect_slope = slope_est.get(key, 0.1) or 0.1
        correction = (truncated_tides - reference_elevation) / transect_slope
        cross_distance_tidally_corrected[key] = truncated_cross + correction

    if options.write_csv:
        _write_tidally_corrected_csv(cross_distance_tidally_corrected, dates_sat, settings)
    return cross_distance_tidally_corrected


def _apply_csv_tide_correction(
    output: Dict[str, Any],
    cross_distance: Dict[str, np.ndarray],
    settings: Dict[str, Any],
    options: TideOptions,
) -> Dict[str, np.ndarray]:
    print("[Tide] Applying CSV-based tide correction.")
    tide_inputs = settings["inputs"]
    path = tide_inputs["tide_csv_path"]
    reference_elevation = tide_inputs.get("reference_elevation", options.reference_elevation)
    beach_slope = tide_inputs.get("beach_slope") or options.beach_slope or 0.1
    tide_data = pd.read_csv(path)
    if "dates" not in tide_data.columns or "tide" not in tide_data.columns:
        raise ValueError("Tide CSV must contain 'dates' and 'tide' columns")

    dates_ts = [pd.to_datetime(d).to_pydatetime() for d in tide_data["dates"]]
    tides_ts = np.asarray(tide_data["tide"], dtype=float)
    dates_sat = output["dates"]
    tides_sat = np.asarray(SDS_tools.get_closest_datapoint(dates_sat, dates_ts, tides_ts), dtype=float)

    tide_filter_cfg = settings.get("tide_filter")
    tide_filter_mask = np.ones_like(tides_sat, dtype=bool)
    tide_thresholds = {}
    if tide_filter_cfg:
        lower_pct = tide_filter_cfg.get("lower_percentile")
        upper_pct = tide_filter_cfg.get("upper_percentile")
        if lower_pct is not None:
            lower_thresh = float(np.nanpercentile(tides_ts, lower_pct))
            tide_thresholds["lower_threshold"] = lower_thresh
            tide_filter_mask &= tides_sat >= lower_thresh
        if upper_pct is not None:
            upper_thresh = float(np.nanpercentile(tides_ts, upper_pct))
            tide_thresholds["upper_threshold"] = upper_thresh
            tide_filter_mask &= tides_sat <= upper_thresh

        removed = int(np.count_nonzero(~tide_filter_mask))
        total = int(tides_sat.size)
        settings["tide_filter_stats"] = {
            "filter_configured": True,
            "total_acquisitions": total,
            "removed_acquisitions": removed,
            "kept_acquisitions": total - removed,
        }
        if tide_thresholds:
            updated_filter = tide_filter_cfg.copy()
            updated_filter.update(tide_thresholds)
            settings["tide_filter"] = updated_filter
    else:
        settings["tide_filter_stats"] = {
            "filter_configured": False,
            "total_acquisitions": int(tide_filter_mask.size),
            "removed_acquisitions": 0,
            "kept_acquisitions": int(tide_filter_mask.size),
        }

    print(f"[Tide] Tide filter mask size: {tide_filter_mask.size}, kept: {int(np.count_nonzero(tide_filter_mask))}")
    correction = (tides_sat - reference_elevation) / beach_slope
    correction[~tide_filter_mask] = np.nan
    cross_distance_tidally_corrected = {}
    for key in cross_distance:
        corrected = cross_distance[key] + correction
        corrected = np.asarray(corrected, dtype=float)
        corrected[~tide_filter_mask] = np.nan
        cross_distance_tidally_corrected[key] = corrected

    if options.write_csv:
        _write_tidally_corrected_csv(cross_distance_tidally_corrected, dates_sat, settings)
    return cross_distance_tidally_corrected


def _write_tidally_corrected_csv(
    cross_distance_tidally_corrected: Dict[str, np.ndarray],
    dates_sat,
    settings: Dict[str, Any],
) -> None:
    first_series = next(iter(cross_distance_tidally_corrected.values()), [])
    out_dict = {"dates": list(dates_sat)[: len(first_series)]}
    for key, series in cross_distance_tidally_corrected.items():
        out_dict[key] = series
    df = pd.DataFrame(out_dict)
    fn = os.path.join(settings["inputs"]["filepath"], "transect_time_series_tidally_corrected.csv")
    df.to_csv(fn, sep=",")
