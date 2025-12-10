# CoastSatCLI (Updated Overview)

This snapshot reflects the in-progress pipeline refactor that lives in `coastsat_pipeline/` while keeping the legacy CLI/analysis scripts available as a fallback.

## What's Here
- **New pipeline**: `coastsat_pipeline` stages + runner + registry; headless execution without notebooks.
- **Legacy flow**: `Complete_Analysis*.py` and `cli/CoastsatCLI.py` remain for compatibility.
- **Docs**: Refactor plans under `docs/refactor/`, architecture notes under `docs/architecture/`, user/dev guides under `docs/user/` and `docs/dev/`.
- **Tests**: Unit tests for pipeline wiring and helpers under `tests/`.

## Quick Start (new pipeline)
1) Create and activate the env (Miniforge/Mamba recommended):
```
conda env create -f environment.yml
conda activate coastsat
```
2) Prepare a site folder with `settings.json` (see `docs/user/configuration.md` for fields). Today the easiest path is to run the legacy CLI init to scaffold the folder and generate `settings.json`:
```
python cli/CoastsatCLI.py init
```
3) Run the new pipeline against that config:
```
python - <<'PY'
from pathlib import Path
from coastsat_pipeline.cli import run_pipeline_from_config
run_pipeline_from_config(Path("path/to/settings.json"))
PY
```
   Or invoke it via the legacy CLI wrapper with the pipeline engine flag:
```
python cli/CoastsatCLI.py run --config path/to/settings.json --engine pipeline
```
4) Outputs land under the `output_dir` specified in `settings.json` (plots, CSV/GeoJSON, trend artifacts).

## Quick Start (legacy fallback)
If you need the older CLI-driven flow:
```
python cli/CoastsatCLI.py init          # guided setup to create a site
python cli/CoastsatCLI.py run --config path/to/settings.json
```
The tide-free variant is `Complete_Analysis_No_Tide.py` (invoked by the CLI when configured).

## Minimal Folder Map
```
coastsat_pipeline/    # new stages, runner, registry, helpers
coastsat/             # upstream CoastSat scripts
cli/                  # legacy Typer CLI for init/run/show
classification/       # classifier models and training notebook
docs/                 # architecture, user, ops, refactor plans
tests/                # unit tests for pipeline and helpers
```

## Requirements & Data Notes
- Python 3.11; GDAL/rtree must import cleanly in the env.
- Classification models (`classification/models/*.pkl`) must be present; store large files outside Git history or fetch from your artifact source.
- Tide corrections require FES config or tide CSV as referenced in `settings.json`.
- Google Earth Engine access is still required for imagery download (see `docs/ops/environment.md`).

## Testing
Run the fast checks before sharing changes:
```
pytest tests -q
```
For a smoke test, point the new pipeline at a small fixture `settings.json` and verify outputs under its `output_dir`.

## Status & Next Steps
- The refactor plan (`coastsat_pipeline/PLAN.md`, `docs/refactor/`) tracks migration of stages from legacy scripts.
- Prefer the new pipeline for headless runs; keep the legacy CLI only as a compatibility path while migration completes.
