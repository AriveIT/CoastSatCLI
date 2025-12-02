from pathlib import Path

import numpy as np

from coastsat_pipeline.helpers.plotting import PlottingOptions, render_transect_trend_plot


def test_render_transect_trend_plot(tmp_path, monkeypatch):
    output = {
        "shorelines": [
            np.array([[0, 0]]),
            np.array([[1, 1]]),
        ],
        "dates": [
            np.datetime64("2020-01-01"),
            np.datetime64("2020-01-05"),
        ],
    }
    transects = {"0001": np.array([[0, 0], [0, 10]])}
    cross_distance = {"0001": np.array([0.0, 1.0])}
    settings = {"inputs": {"sitename": "test", "filepath": str(tmp_path)}}

    monkeypatch.setattr(
        "coastsat_pipeline.helpers.plotting.SDS_transects.calculate_trend",
        lambda dates, series: (1.5, None),
    )

    render_transect_trend_plot(output, transects, cross_distance, settings, PlottingOptions(dpi=50))

    assert (tmp_path / "transects_colored_by_trend_updated.jpg").exists()
