from pathlib import Path

import pytest

from coastsat_pipeline.helpers.initialization import prepare_initial_settings


@pytest.fixture(autouse=True)
def patch_coastsat(monkeypatch):
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.initialization.SDS_tools.polygon_from_kml",
        lambda path: f"poly:{path}",
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.initialization.SDS_tools.smallest_rectangle",
        lambda poly: f"rect({poly})",
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.initialization.SDS_download.retrieve_images",
        lambda inputs: {"retrieved": True, "inputs": inputs},
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.initialization.SDS_download.get_metadata",
        lambda inputs: {"metadata": inputs},
    )
    monkeypatch.setattr(
        "coastsat_pipeline.helpers.initialization.SDS_preprocess.get_reference_sl_from_geojson",
        lambda geojson, epsg: f"ref:{geojson}:{epsg}",
    )


def _make_config():
    return {
        "inputs": {
            "sitename": "site",
            "aoi_path": "aoi.kml",
            "reference_shoreline": "ref.geojson",
            "transects": "transects.geojson",
        },
        "output_dir": "/tmp/site",
        "output_epsg": 4326,
    }


def test_prepare_initial_settings_uses_defaults():
    config = _make_config()
    inputs, settings, metadata = prepare_initial_settings(config)

    assert inputs["dates"][0] == "1984-01-01"
    assert settings["reference_shoreline"].startswith("ref:")
    assert metadata["metadata"]["sitename"] == "site"


def test_prepare_initial_settings_honors_overrides():
    config = _make_config()
    config["dates"] = ["2000-01-01", "2001-01-01"]
    config["sat_list"] = ["S2"]
    config["cloud_thresh"] = 0.1
    inputs, settings, _ = prepare_initial_settings(config)

    assert inputs["dates"] == ["2000-01-01", "2001-01-01"]
    assert inputs["sat_list"] == ["S2"]
    assert settings["cloud_thresh"] == 0.1
