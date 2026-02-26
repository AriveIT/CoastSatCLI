from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from coastsat import SDS_transects
from ..parameters import TimeSeriesOptions
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesResult:
    """Summary of processed transect time-series."""
    cross_distance: Dict[str, np.ndarray]
    trend_dict: Dict[str, float]
    processed_transects: int
    skipped_transects: int

def run_time_series_post_processing(
    transects: Dict[str, Any],
    settings: Dict[str, Any],
    cross_distance_tidally_corrected: Dict[str, np.ndarray],
    output: Dict[str, Any],
    trend_plot_dir: str | None,
    options: TimeSeriesOptions | None = None,
) -> TimeSeriesResult:
    options = options or TimeSeriesOptions()
    (seasonal_path, monthly_path) = _get_full_plot_path(trend_plot_dir, settings)
    cross_distance = {key: np.asarray(series, dtype=float).copy() for key, series in cross_distance_tidally_corrected.items()}
    dates = output["dates"]

    if options.write_csv:
        _write_time_series_csv(transects, cross_distance, dates, settings)

    # Compute trends and plots. (Note: outliers have already been rejected in the analysis stage)
    trend_dict: Dict[str, float] = {}
    processed, skipped = 0, 0

    for key in cross_distance.keys():
        print(f'\rProcessing and plotting {key}...', end='')
        series = cross_distance[key]
        idx_valid = ~np.isnan(series)
        valid_dates = np.array(dates)[idx_valid]
        valid_chainage = series[idx_valid]

        if valid_chainage.size > 1:
            trend, fitted = SDS_transects.calculate_trend(valid_dates, valid_chainage)
            processed += 1

            if settings.get("save_figure", False) and options.save_seasonal_plots:
                try:
                    _plot_seasonal_average(key, valid_dates, valid_chainage, seasonal_path)
                except Exception as e:
                    print(e)
            if settings.get("save_figure", False) and options.save_monthly_plots:
                _plot_monthly_average(key, valid_dates, valid_chainage, monthly_path)

        else:
            trend = np.nan
            fitted = []
            skipped += 1
        trend_dict[key] = trend


    logger.info("Stage 07: processed %d transects (skipped %d due to insufficient data)", processed, skipped)
    print(f"\nProcessed {processed} transects (skipped {skipped} due to insufficient data)")
    return TimeSeriesResult(cross_distance=cross_distance, trend_dict=trend_dict, processed_transects=processed, skipped_transects=skipped)

def _get_full_plot_path(trend_plot_dir, settings):
    if trend_plot_dir:
        os.makedirs(os.path.join(trend_plot_dir, "seasonal_plots", settings["inputs"]["sitename"]), exist_ok=True)
        os.makedirs(os.path.join(trend_plot_dir, "monthly_plots", settings["inputs"]["sitename"]), exist_ok=True)
        return (
            os.path.join(trend_plot_dir, "seasonal_plots", settings["inputs"]["sitename"]),
            os.path.join(trend_plot_dir, "monthly_plots", settings["inputs"]["sitename"])
        )
    else:
        os.makedirs(os.path.join(settings["inputs"]["filepath"], "seasonal_plots"), exist_ok=True)
        os.makedirs(os.path.join(settings["inputs"]["filepath"], "monthly_plots"), exist_ok=True)
        return (
            os.path.join(settings["inputs"]["filepath"], "seasonal_plots"),
            os.path.join(settings["inputs"]["filepath"], "monthly_plots")
        )

def _write_time_series_csv(transects, cross_distance, dates, settings):
    # Emit per-transect CSV time series for downstream use.
    out_dict = {"dates": dates}
    for key in transects.keys():
        out_dict[f"Transect {key}"] = cross_distance[key]
    df = pd.DataFrame(out_dict)
    fn = os.path.join(settings["inputs"]["filepath"], "transect_time_series.csv")
    df.to_csv(fn, sep=",")


def _plot_seasonal_average(key, dates, chainage, trend_plot_dir):
    """Plot seasonal averages and seasonal trends for a transect."""
    dict_seas, dates_seas, chainage_seas, list_seas = SDS_transects.seasonal_average(dates.tolist(), chainage.tolist())
    if len(dates_seas) == 0:
        raise Exception("Not enough data for seasonal trends plot")
    overall_trend, overall_fit = SDS_transects.calculate_trend(dates_seas, chainage_seas)
    season_colors = {"DJF": "C3", "MAM": "C1", "JJA": "C2", "SON": "C0"}

    # 6-month moving average for smoother seasonal visualization (independent of trend).
    df_ma = pd.DataFrame({"date": pd.to_datetime(dates), "value": chainage}).sort_values("date")
    ma = df_ma.set_index("date")["value"].rolling("180D", min_periods=2, center=True).mean()

    # Per-season regression (legacy behaviour)
    season_trends = {}
    season_fits = {}
    for seas, data in dict_seas.items():
        s_dates = data["dates"]
        s_chain = data["chainages"]
        if len(s_dates) > 1:
            seas_trend, seas_fit = SDS_transects.calculate_trend(s_dates, s_chain)
            season_trends[seas] = seas_trend
            season_fits[seas] = seas_fit
        else:
            season_trends[seas] = np.nan
            season_fits[seas] = [np.nan] * len(s_dates)

    fig, ax = plt.subplots(1, 1, figsize=[14, 4], tight_layout=True)
    ax.grid(which="major", linestyle=":", color="0.5")
    ax.set_title(f"Time-series at {key}", x=0, ha="left")
    ax.set(ylabel="distance [m]")
    ax.plot(dates, chainage, "+", lw=1, color="k", mfc="w", ms=4, alpha=0.5, label="raw datapoints")
    ax.plot(dates_seas, chainage_seas, "-", lw=1, color="k", mfc="w", ms=4, label="seasonally-averaged")
    if ma.notna().sum() > 1:
        ax.plot(ma.index, ma.values, color="darkorange", lw=1.5, label="6-mo moving avg")

    for seas in dict_seas.keys():
        ax.plot(
            dict_seas[seas]["dates"],
            dict_seas[seas]["chainages"],
            "o",
            mec="k",
            color=season_colors.get(seas, "k"),
            label=seas,
            ms=5,
        )
        if len(dict_seas[seas]["dates"]) > 1:
            ax.plot(
                dict_seas[seas]["dates"],
                season_fits[seas],
                "--",
                color=season_colors.get(seas, "k"),
                label=f"{seas} trend = {season_trends[seas]:.2f} m/yr",
            )

    ax.plot(dates_seas, overall_fit, "--", color="b", label=f"trend {overall_trend:.1f} m/year")
    ax.legend(loc="lower left", ncol=6, markerscale=1.5, frameon=True, edgecolor="k", columnspacing=1)
    fig.savefig(os.path.join(trend_plot_dir, f"{key}_seasonal_average.jpg"))
    plt.close(fig)


def _plot_monthly_average(key, dates, chainage, trend_plot_dir):
    """Plot monthly averages for a transect."""
    dict_month, dates_month, chainage_month, list_month = SDS_transects.monthly_average(dates.tolist(), chainage.tolist())
    month_colors = plt.get_cmap("tab20")

    fig, ax = plt.subplots(1, 1, figsize=[14, 4], tight_layout=True)
    ax.grid(which="major", linestyle=":", color="0.5")
    ax.set_title(f"Time-series at {key}", x=0, ha="left")
    ax.set(ylabel="distance [m]")
    ax.plot(dates, chainage, "+", lw=1, color="k", mfc="w", ms=4, alpha=0.5, label="raw datapoints")
    ax.plot(dates_month, chainage_month, "-", lw=1, color="k", label="monthly-averaged")

    for idx, month in enumerate(dict_month.keys()):
        ax.plot(
            dict_month[month]["dates"],
            dict_month[month]["chainages"],
            "o",
            mec="k",
            color=month_colors(idx),
            label=month,
            ms=5,
        )
    ax.legend(loc="lower left", ncol=7, markerscale=1.5, frameon=True, edgecolor="k", columnspacing=1)
    fig.savefig(os.path.join(trend_plot_dir, f"{key}_monthly_average.jpg"))
    plt.close(fig)
