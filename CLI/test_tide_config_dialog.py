from importlib import util
from pathlib import Path

import pytest

_DIALOGS_SPEC = util.spec_from_file_location(
    "cli_dialogs",
    Path(__file__).resolve().parents[1] / "CLI" / "dialogs.py",
)
dialogs = util.module_from_spec(_DIALOGS_SPEC)
assert _DIALOGS_SPEC and _DIALOGS_SPEC.loader
_DIALOGS_SPEC.loader.exec_module(dialogs)


def _sequence_prompts(monkeypatch, responses):
    iterator = iter(responses)

    def _prompt(*args, **kwargs):
        return str(next(iterator))

    monkeypatch.setattr(dialogs.typer, "prompt", _prompt)


def test_get_tide_settings_fes(monkeypatch, tmp_path):
    monkeypatch.setattr(
        dialogs,
        "choose_file",
        lambda *args, **kwargs: str(tmp_path / "fes.yaml"),
    )
    monkeypatch.setattr(dialogs, "prompt_tide_filter_settings", lambda: None)
    _sequence_prompts(monkeypatch, ["fes"])

    result = dialogs.get_tide_correction_settings()

    assert result["method"] == "fes"
    assert result["fes_config"].endswith("fes.yaml")
    assert "tide_csv_path" not in result


def test_get_tide_settings_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(
        dialogs,
        "choose_file",
        lambda *args, **kwargs: str(tmp_path / "tides.csv"),
    )
    monkeypatch.setattr(dialogs, "prompt_tide_filter_settings", lambda: {"lower_percentile": 10.0, "upper_percentile": 90.0})
    _sequence_prompts(monkeypatch, ["csv", "0.5", "0.2"])

    result = dialogs.get_tide_correction_settings()

    assert result["method"] == "csv"
    assert Path(result["tide_csv_path"]).name == "tides.csv"
    assert result["reference_elevation"] == pytest.approx(0.5)
    assert result["beach_slope"] == pytest.approx(0.2)
    assert result["tide_filter"]["lower_percentile"] == 10.0
