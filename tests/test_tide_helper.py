from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from coastsat_pipeline.helpers.tide import apply_tide_correction, TideOptions
from coastsat_pipeline.helpers import tide as tide_helper


@pytest.fixture(autouse=True)
def patch_sds_tools(monkeypatch):
    monkeypatch.setattr(
        tide_helper.SDS_tools,
        "get_closest_datapoint",
        lambda dates_sat, dates_ts, tides_ts: tides_ts[: len(dates_sat)],
    )


def test_apply_tide_correction_writes_csv(tmp_path):
    output = {"dates": [1, 2]}
    cross_distance = {"0001": np.array([0.0, 1.0])}
    transects = {"0001": None}
    settings = {"inputs": {"filepath": str(tmp_path)}}
    slope_est = {"0001": 0.5}
    dates_sat = np.array([1, 2])
    tides_sat = np.array([0.0, 0.5])

    corrected = apply_tide_correction(
        output,
        cross_distance,
        transects,
        settings,
        slope_est,
        dates_sat,
        tides_sat,
        options=TideOptions(write_csv=True),
    )

    assert "0001" in corrected
    csv = tmp_path / "transect_time_series_tidally_corrected.csv"
    assert csv.exists()


def test_apply_tide_correction_csv_mode(tmp_path, monkeypatch):
    tide_csv = tmp_path / "tides.csv"
    df = pd.DataFrame({"dates": ["2020-01-01", "2020-01-02"], "tide": [0.0, 1.0]})
    df.to_csv(tide_csv, index=False)

    output = {"dates": [np.datetime64("2020-01-01"), np.datetime64("2020-01-02")]}
    cross_distance = {"0001": np.array([0.0, 1.0])}
    settings = {
        "inputs": {
            "filepath": str(tmp_path),
            "tide_csv_path": str(tide_csv),
            "reference_elevation": 0.0,
            "beach_slope": 1.0,
        }
    }
    corrected = apply_tide_correction(
        output,
        cross_distance,
        {},
        settings,
        slope_est={},
        dates_sat=[],
        tides_sat=[],
        options=TideOptions(write_csv=False),
    )

    assert not np.isnan(corrected["0001"]).any()
