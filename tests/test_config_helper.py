import json
from pathlib import Path

from coastsat_pipeline.helpers.config import load_settings_from_cli_config


def _make_settings(tmp_path: Path) -> Path:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "aoi.kml").write_text("")
    (site_dir / "ref.geojson").write_text("")
    (site_dir / "transects.geojson").write_text("")
    (site_dir / "fes.yaml").write_text("")
    (site_dir / "outputs").mkdir()
    config = {
        "inputs": {
            "sitename": "test",
            "aoi_path": "aoi.kml",
            "reference_shoreline": "ref.geojson",
            "transects": "transects.geojson",
            "fes_config": "fes.yaml",
        },
        "output_dir": "outputs",
        "output_epsg": 4326,
        "tide_filter": {"lower_percentile": 5, "upper_percentile": 95},
    }
    path = site_dir / "settings.json"
    path.write_text(json.dumps(config))
    return path


def test_load_settings_resolves_paths(tmp_path: Path):
    config_path = _make_settings(tmp_path)
    config = load_settings_from_cli_config(config_path)

    assert Path(config["inputs"]["aoi_path"]).is_absolute()
    assert config["output_dir"].endswith("outputs")
    assert config["tide_filter"]["lower_percentile"] == 5.0
