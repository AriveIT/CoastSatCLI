import numpy as np
import pytest

from coastsat_pipeline.helpers.timeseries import TimeSeriesOptions, run_time_series_post_processing
from coastsat_pipeline.helpers import timeseries as helper


@pytest.fixture(autouse=True)
def patch_sds_transects(monkeypatch):
    monkeypatch.setattr(helper.SDS_transects, "reject_outliers", lambda cross_distance, output, settings: cross_distance)
    monkeypatch.setattr(
        helper.SDS_transects,
        "seasonal_average",
        lambda dates, chainage: (
            {"DJF": {"dates": dates, "chainages": chainage}},
            dates,
            chainage,
            [],
        ),
    )
    monkeypatch.setattr(
        helper.SDS_transects,
        "monthly_average",
        lambda dates, chainage: (
            {"Jan": {"dates": dates, "chainages": chainage}},
            dates,
            chainage,
            [],
        ),
    )
    monkeypatch.setattr(
        helper.SDS_transects,
        "calculate_trend",
        lambda dates, chainage: (0.1, chainage),
    )


def test_run_time_series_post_processing(tmp_path, monkeypatch):
    transects = {"0001": np.array([[0, 0], [0, 10]])}
    settings = {"inputs": {"filepath": str(tmp_path)}, "save_figure": False}
    cross_distance = {"0001": np.array([0.0, 1.0, np.nan])}
    output = {"dates": np.array([1, 2, 3])}

    result = run_time_series_post_processing(
        transects,
        settings,
        cross_distance,
        output,
        options=TimeSeriesOptions(write_csv=False, save_seasonal_plots=False, save_monthly_plots=False),
    )

    assert "0001" in result.cross_distance
    assert result.trend_dict["0001"] == pytest.approx(0.1)
    assert result.processed_transects == 1
