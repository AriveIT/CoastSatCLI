import json
from pathlib import Path

import pytest

from coastsat_pipeline.context import PipelineContext
from coastsat_pipeline.runner import PipelineRunner
from coastsat_pipeline.stage import PipelineStage
from coastsat_pipeline.stages.analysis_stage import AnalysisStage
from coastsat_pipeline.stages.config_stage import ConfigLoadStage
from coastsat_pipeline.stages.detection_stage import ImageryStage
from coastsat_pipeline.stages.plot_stage import ImprovedTransectsPlotStage
from coastsat_pipeline.stages.slope_stage import SlopeEstimationStage
from coastsat_pipeline.stages.tide_stage import TideCorrectionStage
from coastsat_pipeline.stages.timeseries_stage import TimeSeriesPostProcessingStage
from coastsat_pipeline.stages.trends_stage import TrendCalculationStage
from coastsat_pipeline.helpers.trends import TrendExportResult


def _write_settings(tmp_path: Path) -> Path:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    for filename in ["aoi.kml", "reference.geojson", "transects.geojson", "fes2022.yaml"]:
        (site_dir / filename).write_text("{}")
    (site_dir / "outputs").mkdir()

    config = {
        "inputs": {
            "sitename": "test_site",
            "aoi_path": "aoi.kml",
            "reference_shoreline": "reference.geojson",
            "transects": "transects.geojson",
            "fes_config": "fes2022.yaml",
        },
        "output_dir": "outputs",
        "output_epsg": 4326,
        "tide_filter": {"lower_percentile": 5, "upper_percentile": 95},
    }
    config_path = site_dir / "settings.json"
    config_path.write_text(json.dumps(config))
    return config_path


def test_config_stage_populates_settings(tmp_path: Path):
    config_path = _write_settings(tmp_path)
    context = PipelineContext(config_path=config_path)
    stage = ConfigLoadStage()

    stage.run(context)

    settings = context.settings
    assert settings is not None
    assert settings.inputs.sitename == "test_site"
    assert settings.output_dir.is_absolute()
    assert settings.tide.mode == "fes"
    assert settings.tide.tide_filter is not None
    assert settings.tide.tide_filter.lower_percentile == 5.0


def test_pipeline_runner_executes_in_order(tmp_path: Path):
    config_path = _write_settings(tmp_path)
    context = PipelineContext(config_path=config_path)

    executed = []

    class DummyStage(PipelineStage):
        def __init__(self, name: str):
            self.name = name

        def run(self, context: PipelineContext) -> None:
            executed.append(self.name)

    runner = PipelineRunner([ConfigLoadStage(), DummyStage("stage-a"), DummyStage("stage-b")])
    runner.run(context)

    assert context.settings is not None
    assert executed == ["stage-a", "stage-b"]


def test_imagery_stage_uses_existing_metadata(tmp_path: Path, monkeypatch):
    context = PipelineContext(config_path=tmp_path / "settings.json")
    context.inputs_config = {"input": "value"}
    context.analysis_settings = {"setting": "value"}
    context.metadata["initialization"] = {"meta": "data"}

    captured = {}

    def fake_batch(metadata, settings, inputs):
        captured["metadata"] = metadata
        captured["settings"] = settings
        captured["inputs"] = inputs
        return {"output": "ok"}

    monkeypatch.setattr("coastsat_pipeline.stages.imagery_stage.run_batch_shoreline_detection", fake_batch)

    stage = ImageryStage()
    stage.run(context)

    assert context.shoreline_output == {"output": "ok"}
    assert captured["metadata"] == {"meta": "data"}
    assert captured["inputs"] == {"input": "value"}


def test_analysis_stage_updates_context(monkeypatch):
    context = PipelineContext(config_path=Path("dummy"))
    context.analysis_settings = {"settings": "value"}
    context.shoreline_output = {"existing": True}

    def fake_shoreline_analysis(output, settings):
        return "cross", {"transect": []}, {"updated": True}

    monkeypatch.setattr("coastsat_pipeline.stages.analysis_stage.run_shoreline_analysis", fake_shoreline_analysis)

    stage = AnalysisStage()
    stage.run(context)

    assert context.cross_distance == "cross"
    assert context.transects == {"transect": []}
    assert context.shoreline_output == {"updated": True}


def test_slope_stage_updates_context(monkeypatch):
    context = PipelineContext(config_path=Path("dummy"))
    context.analysis_settings = {"settings": "value"}
    context.cross_distance = "cross"
    context.shoreline_output = {"output": True}

    def fake_slope_estimation(settings, cross_distance, output):
        return {"slope": 1.2}, {"dates": []}, {"tides": []}

    monkeypatch.setattr(
        "coastsat_pipeline.stages.slope_stage.run_slope_estimation",
        fake_slope_estimation,
    )

    stage = SlopeEstimationStage()
    stage.run(context)

    assert context.slope_est == {"slope": 1.2}
    assert context.dates_sat == {"dates": []}
    assert context.tides_sat == {"tides": []}


def test_tide_stage_requires_context(monkeypatch):
    context = PipelineContext(config_path=Path("dummy"))
    context.shoreline_output = {"output": True}
    context.cross_distance = "cross"
    context.transects = {"t": []}
    context.analysis_settings = {"settings": True}
    context.slope_est = {"slope": 1}
    context.dates_sat = {"dates": []}
    context.tides_sat = {"tides": []}

    def fake_tide(*args, **kwargs):
        return "corrected"

    monkeypatch.setattr(
        "coastsat_pipeline.stages.tide_stage.apply_tide_correction",
        fake_tide,
    )

    stage = TideCorrectionStage()
    stage.run(context)

    assert context.cross_distance_tidally_corrected == "corrected"


def test_plot_stage_calls_helper(monkeypatch):
    context = PipelineContext(config_path=Path("dummy"))
    context.shoreline_output = {"output": True}
    context.transects = {"t": []}
    context.cross_distance_tidally_corrected = "corrected"
    context.analysis_settings = {"settings": True}

    called = {}

    def fake_plot(output, transects, corrected, settings):
        called["args"] = (output, transects, corrected, settings)

    monkeypatch.setattr(
        "coastsat_pipeline.stages.plot_stage.render_transect_trend_plot",
        fake_plot,
    )

    stage = ImprovedTransectsPlotStage()
    stage.run(context)

    assert called["args"][2] == "corrected"


def test_timeseries_stage_updates_context(monkeypatch):
    context = PipelineContext(config_path=Path("dummy"))
    context.transects = {"t": []}
    context.analysis_settings = {"settings": True}
    context.cross_distance_tidally_corrected = "corrected"
    context.shoreline_output = {"output": True}

    class DummyResult:
        def __init__(self):
            self.cross_distance = "processed"
            self.trend_dict = {"trend": {}}
            self.processed_transects = 1
            self.skipped_transects = 0

    def fake_post(transects, settings, corrected, output):
        return DummyResult()

    monkeypatch.setattr(
        "coastsat_pipeline.stages.timeseries_stage.run_time_series_post_processing",
        lambda **kwargs: fake_post(kwargs["transects"], kwargs["settings"], kwargs["cross_distance_tidally_corrected"], kwargs["output"]),
    )

    stage = TimeSeriesPostProcessingStage()
    stage.run(context)

    assert context.cross_distance_processed == "processed"
    assert context.trend_dict == {"trend": {}}


def test_trend_stage_updates_context(monkeypatch):
    context = PipelineContext(config_path=Path("dummy"))
    context.transects = {"t": []}
    context.cross_distance_tidally_corrected = "corrected"
    context.shoreline_output = {"output": True}
    context.analysis_settings = {"settings": True}
    context.slope_est = {"slope": 1}
    context.trend_dict = {"trend": {}}

    dummy_result = TrendExportResult(records=[], geojson_path=Path("trend.geojson"), trend_dict={"trend": {}})

    def fake_calc(*args, **kwargs):
        return dummy_result

    monkeypatch.setattr(
        "coastsat_pipeline.stages.trends_stage.compute_and_save_trends",
        fake_calc,
    )

    stage = TrendCalculationStage()
    stage.run(context)

    assert context.trend_results == dummy_result
