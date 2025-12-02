from pathlib import Path
from datetime import datetime

import numpy as np
import pytest

from coastsat_pipeline.helpers.slope import run_slope_estimation, SlopeOptions


@pytest.fixture(autouse=True)
def patch_slope(monkeypatch):
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_tools.remove_duplicates",
        lambda output: output,
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_tools.remove_inaccurate_georef",
        lambda output, threshold: output,
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_tools.transects_from_geojson",
        lambda path: {"0001": np.array([[0, 0], [0, 10]])},
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_transects.compute_intersection_QC",
        lambda output, transects, settings: {"0001": np.array([0.0, 1.0])},
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_transects.reject_outliers",
        lambda cross_distance, output, settings: cross_distance,
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.pyfes.load_config",
        lambda yaml: {"tide": object(), "radial": object()},
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_tools.select_valid_centroid",
        lambda geom, ocean, load: (0.0, 0.0),
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_slope.compute_tide",
        lambda centroid, date_range, timestep, ocean, load: ([datetime(2020, 1, 1)], [0.0]),
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_slope.compute_tide_dates",
        lambda centroid, dates, ocean, load: [0.0 for _ in dates],
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_slope.tide_correct",
        lambda composite, tide, slope: np.array([0.0]),
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_slope.integrate_power_spectrum",
        lambda dates, tsall, settings, key: (0.1, (0.1, 0.2)),
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.SDS_slope.plot_spectrum_all",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.slope.plt",
        type("DummyPlot", (), {"gcf": staticmethod(lambda: type("F", (), {"savefig": lambda self, path, dpi=200: None})()), "close": staticmethod(lambda *args: None)}),
    )


def test_run_slope_estimation(monkeypatch, tmp_path):
    settings = {
        "inputs": {
            "filepath": str(tmp_path),
            "transect_geojson": "file.geojson",
            "fes_config": "fes.yaml",
            "polygon": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
            "sitename": "test",
        },
        "output_epsg": 4326,
    }
    cross_distance = {"0001": np.array([0.0, 1.0])}
    output = {"dates": [datetime(2020, 1, 1)], "satname": ["L8"]}

    slopes, dates_sat, tides_sat = run_slope_estimation(settings, cross_distance, output, options=SlopeOptions(save_figures=False))

    assert slopes["0001"] == pytest.approx(0.1)
