from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString

from coastsat_pipeline.helpers.trends import compute_and_save_trends, TrendExportResult


def test_compute_and_save_trends_exports_geojson(monkeypatch, tmp_path):
    transects = {"T1": LineString([(0, 0), (1, 1)])}
    cross_distance = {"T1": np.array([1.0, np.nan, 2.0])}
    output = {"dates": [1, 2, 3]}
    settings = {
        "inputs": {
            "filepath": str(tmp_path),
            "sitename": "demo",
        },
        "output_epsg": 4326,
        "tide_filter_stats": {"removed_acquisitions": 1, "total_acquisitions": 3},
    }
    slope_est = {"T1": 0.2}
    trend_dict = {"T1": -0.5}

    captured = {}

    def fake_to_file(self, path, driver=None, encoding=None, **kwargs):
        captured["path"] = Path(path)
        captured["frame"] = self.copy()

    import geopandas as gpd

    monkeypatch.setattr(gpd.GeoDataFrame, "to_file", fake_to_file, raising=False)

    result = compute_and_save_trends(
        transects=transects,
        cross_distance_tidally_corrected=cross_distance,
        output=output,
        settings=settings,
        slope_est=slope_est,
        trend_dict=trend_dict,
    )

    assert isinstance(result, TrendExportResult)
    assert result.geojson_path == tmp_path / "demo_transects_with_trends.geojson"
    assert captured["path"] == result.geojson_path
    assert len(result.records) == 1

    record = result.records[0]
    assert record.id == "T1"
    assert record.images_total == 3
    assert record.images_used == 2
    assert record.trend == -0.5
    assert record.slope == 0.2
    assert record.coverage_pct == pytest.approx(66.666, rel=1e-3)
    assert record.tide_filter_removed_pct == pytest.approx(100 * 1 / 3)

    exported_row = captured["frame"].iloc[0]
    assert exported_row["id"] == "T1"
    assert exported_row["plot_path"].endswith("T1_seasonal_average.jpg")
