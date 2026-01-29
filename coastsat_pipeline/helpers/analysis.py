from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import gridspec

from coastsat import SDS_tools, SDS_transects
from ..parameters import AnalysisOptions

logger = logging.getLogger(__name__)


def run_shoreline_analysis(
    output: Dict[str, Any],
    settings: Dict[str, Any],
    transect_settings: Dict[str, Any],
    outlier_settings: Dict[str, Any],
    georef_accuracy_tolerance: float,
    options: AnalysisOptions | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Analyze the shoreline detections and return (cross_distance, transects, updated_output).
    Mirrors the legacy shoreline_analysis function.
    """
    options = options or AnalysisOptions()
    sitename = settings.get("inputs", {}).get("sitename", "unknown")
    logger.info("Stage 03: analyzing shorelines for site %s", sitename)

    output = SDS_tools.remove_duplicates(output)
    output = SDS_tools.remove_inaccurate_georef(output, georef_accuracy_tolerance)

    transects = SDS_tools.transects_from_geojson(settings["inputs"]["transect_geojson"])

    if settings.get("save_figure", False) and options.plot_transects:
        _plot_shorelines_with_transects(output, transects, settings)

    cross_distance = _compute_cross_distance(output, transects, transect_settings, outlier_settings)

    if settings.get("save_figure", False) and options.plot_time_series:
        _plot_time_series(output, cross_distance, settings)

    if options.write_csv:
        _write_time_series_csv(output, cross_distance, settings)

    logger.info("Stage 03: completed shoreline analysis (%d transects)", len(transects))
    return cross_distance, transects, output


def _plot_shorelines_with_transects(output: Dict[str, Any], transects: Dict[str, Any], settings: Dict[str, Any]) -> None:
    fig = plt.figure(figsize=[15, 8], tight_layout=True)
    plt.axis("equal")
    plt.xlabel("Eastings")
    plt.ylabel("Northings")
    plt.grid(linestyle=":", color="0.5")
    for i in range(len(output["shorelines"])):
        sl = output["shorelines"][i]
        date = output["dates"][i]
        plt.plot(sl[:, 0], sl[:, 1], ".", label=date.strftime("%d-%m-%Y"))
    for i, key in enumerate(list(transects.keys())):
        plt.plot(transects[key][0, 0], transects[key][0, 1], "bo", ms=5)
        plt.plot(transects[key][:, 0], transects[key][:, 1], "k-", lw=1)
    fig.savefig(os.path.join(settings["inputs"]["filepath"], "mapped_shorelines_with_transects.jpg"), dpi=200)
    plt.close(fig)


def _compute_cross_distance(
        output: Dict[str, Any],
        transects: Dict[str, Any],
        transect_settings: Dict[str, Any],
        outlier_settings: Dict[str, Any],
) -> Dict[str, Any]:
    cross_distance = SDS_transects.compute_intersection_QC(output, transects, transect_settings)
    return SDS_transects.reject_outliers(cross_distance, output, outlier_settings)


def _plot_time_series(output: Dict[str, Any], cross_distance: Dict[str, Any], settings: Dict[str, Any]) -> None:
    fig = plt.figure(figsize=[15, 8], tight_layout=True)
    gs = gridspec.GridSpec(len(cross_distance), 1)
    gs.update(left=0.05, right=0.95, bottom=0.05, top=0.95, hspace=0.05)
    for i, key in enumerate(cross_distance.keys()):
        if np.all(np.isnan(cross_distance[key])):
            continue
        ax = fig.add_subplot(gs[i, 0])
        ax.grid(linestyle=":", color="0.5")
        ax.set_ylim([-50, 50])
        ax.plot(
            output["dates"],
            cross_distance[key] - np.nanmedian(cross_distance[key]),
            "-o",
            ms=4,
            mfc="w",
        )
        ax.set_ylabel("distance [m]", fontsize=12)
        ax.text(
            0.5,
            0.95,
            key,
            bbox=dict(boxstyle="square", ec="k", fc="w"),
            ha="center",
            va="top",
            transform=ax.transAxes,
            fontsize=14,
        )
    fig.savefig(os.path.join(settings["inputs"]["filepath"], "time_series_raw.jpg"), dpi=200)
    plt.close(fig)


def _write_time_series_csv(output: Dict[str, Any], cross_distance: Dict[str, Any], settings: Dict[str, Any], name: str="transect_time_series.csv") -> None:
    series_lengths = [len(output.get("dates", []))]
    series_lengths.extend(len(values) for values in cross_distance.values())
    target_len = max(series_lengths) if series_lengths else 0

    def _pad(values, fill_value):
        padded = [fill_value] * target_len
        for idx, value in enumerate(values[:target_len]):
            padded[idx] = value
        return padded

    out_dict: Dict[str, Any] = {}
    out_dict["dates"] = _pad(list(output.get("dates", [])), pd.NaT)
    for key in cross_distance.keys():
        out_dict[f"Transect {key}"] = _pad(list(cross_distance[key]), np.nan)

    df = pd.DataFrame(out_dict)
    target = os.path.join(settings["inputs"]["filepath"], name)
    df.to_csv(target, sep=",")
