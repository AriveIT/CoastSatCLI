from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from coastsat import SDS_transects
from ..parameters import PlottingOptions

# @dataclass
# class PlottingOptions:
#     trend_min: float = -30.0
#     trend_max: float = 30.0
#     cmap_name: str = "RdBu_r"
#     dpi: int = 300


def render_transect_trend_plot(
    output: Dict[str, Any],
    transects: Dict[str, Any],
    cross_distance_tidally_corrected: Dict[str, Any],
    settings: Dict[str, Any],
    options: PlottingOptions | None = None,
) -> None:
    options = options or PlottingOptions()
    sitename = settings["inputs"]["sitename"]
    trend_min, trend_max = options.trend_min, options.trend_max
    num_intervals = 100

    cmap = plt.colormaps.get_cmap(options.cmap_name).resampled(num_intervals)
    norm = mcolors.Normalize(vmin=trend_min, vmax=trend_max)

    fig, ax = plt.subplots(figsize=(12, 8), tight_layout=True)
    ax.set_title(f"Transects Colored by Shoreline Change Trend ({sitename})", fontsize=14)
    ax.set_xlabel("Eastings")
    ax.set_ylabel("Northings")
    ax.axis("equal")
    ax.grid(linestyle=":", color="0.5")

    dates = [_coerce_datetime(date) for date in output["dates"]]

    for i in range(len(output["shorelines"])):
        sl = output["shorelines"][i]
        ax.plot(sl[:, 0], sl[:, 1], ".", label=_format_date_label(dates[i]), alpha=0.5)

    for key in transects.keys():
        series = np.asarray(cross_distance_tidally_corrected[key], dtype=float)
        aligned_dates = dates[: len(series)]
        min_len = min(len(aligned_dates), len(series))
        if min_len < 2:
            trend = 0.0
        else:
            trend, _ = SDS_transects.calculate_trend(aligned_dates[:min_len], series[:min_len])
        color = cmap(norm(trend))
        ax.plot(transects[key][:, 0], transects[key][:, 1], "-", color=color, lw=2)
        ax.plot(transects[key][0, 0], transects[key][0, 1], "bo", ms=5)

    cbar = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation="vertical")
    cbar.set_label("Shoreline Change Trend (m/year)", fontsize=12)
    cbar.set_ticks(range(int(trend_min), int(trend_max) + 1, 5))
    cbar.ax.tick_params(labelsize=10)

    output_path = os.path.join(settings["inputs"]["filepath"], "transects_colored_by_trend_updated.jpg")
    fig.savefig(output_path, dpi=options.dpi)
    plt.close(fig)


def _format_date_label(date: Any) -> str:
    if hasattr(date, "strftime"):
        return date.strftime("%Y-%m-%d")
    if isinstance(date, np.datetime64):
        return str(date.astype("datetime64[D]"))
    return str(date)


def _coerce_datetime(date: Any):
    if hasattr(date, "toordinal"):
        return date
    if isinstance(date, np.datetime64):
        return pd.Timestamp(date).to_pydatetime()
    return pd.to_datetime(date).to_pydatetime()
