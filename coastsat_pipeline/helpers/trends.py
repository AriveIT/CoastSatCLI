from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.geometry import MultiLineString

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
    images_total: int
    images_used: int
    coverage_pct: float
    data_gap_pct: float
    tide_filter_removed: float
    tide_filter_total: float
    tide_filter_removed_pct: float
    plot_path: str
    slope_plot_path: str


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
    default_slope: float
) -> TrendExportResult:
    """
    Build per-transect trend summaries and export them as GeoJSON, mirroring the legacy Stage 08.
    """

    records = _build_transect_trends(
        transects=transects,
        cross_distance_tidally_corrected=cross_distance_tidally_corrected,
        output=output,
        settings=settings,
        slope_est=slope_est,
        trend_dict=trend_dict,
        default_slope=default_slope
    )
    geojson_path = _export_trends_geojson(records, settings)

    logger.info("Saved %d transect trends to %s", len(records), geojson_path)
    return TrendExportResult(records=records, geojson_path=geojson_path, trend_dict=trend_dict)


def _build_transect_trends(
    transects: Dict[str, Any],
    cross_distance_tidally_corrected: Dict[str, np.ndarray],
    output: Dict[str, Any],
    settings: Dict[str, Any],
    slope_est: Dict[str, float],
    trend_dict: Dict[str, float],
    default_slope: float,
) -> List[TransectTrend]:
    total_images = len(output.get("dates", []))
    tide_stats = settings.get("tide_filter_stats", {})
    filepath = Path(settings["inputs"]["filepath"])
    slope_dir = filepath / "slope_estimation"

    records: List[TransectTrend] = []
    for key, geometry in transects.items():
        seasonal_plot_path = str(filepath / f"{key}_seasonal_average.jpg")
        slope_energy_curve_path = str(slope_dir / f"2_energy_curve_{key}.jpg")

        cross = np.asarray(cross_distance_tidally_corrected.get(key, []), dtype=float)
        n_total = cross.size
        n_used = int(np.count_nonzero(~np.isnan(cross))) if n_total else 0
        coverage_pct = (100 * n_used / n_total) if n_total else np.nan
        gap_pct = (100 - coverage_pct) if np.isfinite(coverage_pct) else np.nan

        tide_removed = tide_stats.get("removed_acquisitions", 0)
        tide_total = tide_stats.get("total_acquisitions", total_images)
        tide_removed_pct = 100 * tide_removed / tide_total if tide_total else np.nan

        record = TransectTrend(
            id=key,
            geometry=MultiLineString([geometry]),
            trend=trend_dict.get(key, np.nan),
            slope=slope_est.get(key, default_slope),
            images_total=int(total_images),
            images_used=n_used,
            coverage_pct=coverage_pct,
            data_gap_pct=gap_pct,
            tide_filter_removed=tide_removed,
            tide_filter_total=tide_total,
            tide_filter_removed_pct=tide_removed_pct,
            plot_path=seasonal_plot_path,
            slope_plot_path=slope_energy_curve_path,
        )
        records.append(record)

    logger.debug("Built trend summaries for %d transects", len(records))
    return records


def _export_trends_geojson(records: List[TransectTrend], settings: Dict[str, Any]) -> Path:
    gdf_transects = gpd.GeoDataFrame([asdict(record) for record in records], crs=CRS(settings["output_epsg"]))

    filepath = Path(settings["inputs"]["filepath"])
    geojson_path = filepath / f"{settings['inputs']['sitename']}_transects_with_trends.geojson"
    gdf_transects.to_file(geojson_path, driver="GeoJSON", encoding="utf-8")
    return geojson_path
