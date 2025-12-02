from pathlib import Path

import numpy as np
import pytest

from coastsat_pipeline.helpers.analysis import AnalysisOptions, run_shoreline_analysis


@pytest.fixture(autouse=True)
def patch_analysis(monkeypatch):
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.analysis.SDS_tools.remove_duplicates",
        lambda output: output,
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.analysis.SDS_tools.remove_inaccurate_georef",
        lambda output, threshold: output,
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.analysis.SDS_tools.transects_from_geojson",
        lambda path: {"0001": np.array([[0, 0], [0, 10]])},
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.analysis.SDS_transects.compute_intersection_QC",
        lambda output, transects, settings: {"0001": np.array([0.0, 1.0])},
    )


def test_run_shoreline_analysis_writes_csv(tmp_path, monkeypatch):
    output = {"shorelines": [np.array([[0, 0]])], "dates": [np.datetime64("2020-01-01")]}
    settings = {
        "inputs": {
            "transect_geojson": "transects.geojson",
            "filepath": str(tmp_path),
        },
        "output_epsg": 4326,
        "save_figure": False,
    }

    cross_distance, transects, updated_output = run_shoreline_analysis(output, settings)

    assert "0001" in cross_distance
    csv = tmp_path / "transect_time_series.csv"
    assert csv.exists()


def test_analysis_helper_respects_write_csv_flag(tmp_path, monkeypatch):
    output = {"shorelines": [np.array([[0, 0]])], "dates": [np.datetime64("2020-01-01")]}
    settings = {
        "inputs": {"transect_geojson": "transects.geojson", "filepath": str(tmp_path)},
        "output_epsg": 4326,
        "save_figure": False,
    }
    run_shoreline_analysis(output, settings, options=AnalysisOptions(write_csv=False, plot_time_series=False, plot_transects=False))
    assert not (tmp_path / "transect_time_series.csv").exists()
