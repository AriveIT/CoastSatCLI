from __future__ import annotations

import os
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.geometry import MultiLineString

import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class TransectTrend:
    """
    Container describing the final per-transect trend metrics that will be exported.
    """
    id: str
    trend: float
    slope: float
    geometry: MultiLineString
    images_used: int
    total_images: int
    tide_filter_removed_pct: float
    plot_path: str
    ma_plot_path: str
    run_date: datetime
    analysis_date_range: List
    missions: List


@dataclass
class TrendExportResult:
    records: List[TransectTrend]
    geojson_path: Path
    trend_dict: Dict[str, float]


def compute_and_save_trends(
    transects: Dict[str, Any],
    cross_distance_tidally_corrected: Dict[str, np.ndarray],
    output: Dict[str, Any],
    settings: Dict[str, Any],
    slope_est: Dict[str, float],
    trend_dict: Dict[str, float],
    trend_plot_dir: str,
) -> TrendExportResult:
    """
    Build per-transect trend summaries and export them as GeoJSON, mirroring the legacy Stage 08.
    """
    if not slope_est: slope_est = {}
    records = _build_transect_trends(
        transects=transects,
        cross_distance_tidally_corrected=cross_distance_tidally_corrected,
        output=output,
        settings=settings,
        trend_dict=trend_dict,
        slope_est=slope_est,
        trend_plot_dir=trend_plot_dir,
    )
    geojson_path = _export_trends_geojson(records, settings, trend_plot_dir)

    logger.info("Saved %d transect trends to %s", len(records), geojson_path)
    return TrendExportResult(records=records, geojson_path=geojson_path, trend_dict=trend_dict)


def _build_transect_trends(
    transects: Dict[str, Any],
    cross_distance_tidally_corrected: Dict[str, np.ndarray],
    output: Dict[str, Any],
    settings: Dict[str, Any],
    trend_dict: Dict[str, float],
    slope_est: Dict[str, float],
    trend_plot_dir: str | None,
) -> List[TransectTrend]:
    total_images = len(output.get("dates", []))
    tide_stats = settings.get("tide_filter_stats", {})
    seasonal_dir, ma_dir = _get_filepath(trend_plot_dir, settings)
    # slope_dir = Path(settings["inputs"]["filepath"]) / "slope_estimation"

    records: List[TransectTrend] = []
    for key, geometry in transects.items():
        seasonal_plot_path = os.path.join(seasonal_dir, f"{key}_seasonal_average.jpg")
        ma_plot_path = os.path.join(ma_dir, f"{key}_ma.jpg")
        # slope_energy_curve_path = str(slope_dir / f"2_energy_curve_{key}.jpg")

        cross = np.asarray(cross_distance_tidally_corrected.get(key, []), dtype=float)
        n_total = cross.size
        n_used = int(np.count_nonzero(~np.isnan(cross))) if n_total else 0
        coverage_pct = (100 * n_used / n_total) if n_total else np.nan
        # gap_pct = (100 - coverage_pct) if np.isfinite(coverage_pct) else np.nan

        tide_removed = tide_stats.get("removed_acquisitions", 0)
        tide_total = tide_stats.get("total_acquisitions", total_images)
        tide_removed_pct = 100 * tide_removed / tide_total if tide_total else np.nan

        record = TransectTrend(
            id=key,
            geometry=MultiLineString([geometry]),
            trend=trend_dict.get(key, np.nan),
            slope=slope_est.get(key, None),
            images_used=n_used,
            total_images=total_images,
            tide_filter_removed_pct=tide_removed_pct,
            plot_path=seasonal_plot_path,
            ma_plot_path=ma_plot_path,
            run_date=str(datetime.datetime.now()),
            analysis_date_range=settings["inputs"]["dates"],
            missions=settings["inputs"]["sat_list"],
        )
        records.append(record)

    logger.debug("Built trend summaries for %d transects", len(records))
    return records

# returns relative path that points to the seasonal_plots directory
def _get_filepath(trend_plot_dir, settings):
    if trend_plot_dir:
        seasonal_dir = os.path.join(trend_plot_dir, "seasonal_plots", settings["inputs"]["sitename"])
        ma_dir = os.path.join(trend_plot_dir, "ma_plots", settings["inputs"]["sitename"])
        return seasonal_dir, ma_dir
    else:
        seasonal_dir = os.path.join(settings["inputs"]["filepath"], "seasonal_plots")
        ma_dir = os.path.join(settings["inputs"]["filepath"], "ma_plots")
        return seasonal_dir, ma_dir

# where to save geojson
def _get_geojson_path(trend_plot_dir, settings):
    if trend_plot_dir:
        p = os.path.join(trend_plot_dir, "geojson")
        os.makedirs(p, exist_ok=True)
        return p
    else:
        return Path(settings["inputs"]["filepath"])

def _export_trends_geojson(records: List[TransectTrend], settings: Dict[str, Any], trend_plot_dir: str | None) -> Path:
    gdf_transects = gpd.GeoDataFrame([asdict(record) for record in records], crs=CRS(settings["output_epsg"]))

    filepath = _get_geojson_path(trend_plot_dir, settings)
    geojson_path = os.path.join(filepath, f"{settings['inputs']['sitename']}_transects_with_trends.geojson")

    geojson = json.loads(gdf_transects.to_json())

    with open(geojson_path, "w") as f:
        json.dump(geojson, f)

    return geojson_path
