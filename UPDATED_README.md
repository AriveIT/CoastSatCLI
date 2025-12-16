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
   - GUI: `python -m coastsat_pipeline.gui` and pick your `settings.json`.
   - Headless:
   ```
   python - <<'PY'
   from pathlib import Path
   from coastsat_pipeline.cli import run_pipeline_from_config
   run_pipeline_from_config(Path("path/to/settings.json"))
   PY
   ```
   - Legacy CLI wrapper (still available): `python cli/CoastsatCLI.py run --config path/to/settings.json --engine pipeline`
4) Outputs land under the `output_dir` specified in `settings.json` (plots, CSV/GeoJSON, trend artifacts).

## Quick Start (legacy fallback)
If you need the older CLI-driven flow:
```
python cli/CoastsatCLI.py init          # guided setup to create a site
python cli/CoastsatCLI.py run --config path/to/settings.json
```
The tide-free variant is `Complete_Analysis_No_Tide.py` (invoked by the CLI when configured).

## GUI plan (init flow, Gooey)
Goal: replicate the legacy `init` experience with a point-and-click GUI while keeping the legacy CLI intact. We will:
- Wrap the existing Typer `init` logic with Gooey forms (or mirror the same steps in a Gooey-specific entrypoint) so settings.json generation and optional run work end-to-end.
- Keep batch and single AOI modes, tide method selection (FES vs CSV), transect customization, and EPSG detection prompts.

Implementation sketch:
- Dependency: add `gooey` to the environment.
- Entry: add a new `cli/gui_init.py` (or similar) that uses `@Gooey(program_name="CoastSat Init")` and a `GooeyParser`.
- Arguments/widgets to expose:
  - `--engine` dropdown: `legacy` (default) or `pipeline`.
  - Base project directory (FolderChooser).
  - Sitename (TextField).
  - Shoreline file (FileChooser for .geojson/.shp).
  - Mode: single vs batch AOI (Dropdown/RadioGroup).
  - AOI file(s): FileChooser or MultiFileChooser for KML.
  - Tide method: CSV vs FES (RadioGroup) with conditional widgets:
    - FES: YAML FileChooser.
    - CSV: tide CSV FileChooser, beach slope (Number); reference elevation fixed to 0.0.
  - Optional tide filter: lower/upper percentile (Number inputs).
  - Transect params (Number inputs): spacing, length, offset ratio, skip threshold; tuck under an “Advanced” group.
- Flow:
  - On submit, call the same helper functions (`setup_project_directories`, `detect_or_prompt_epsg` equivalent logic without prompts, `create_and_save_reference_shoreline`, `generate_and_save_transects`, write settings.json).
  - If single AOI: run once. If batch: loop AOIs with suffixed sitenames.
  - After writing settings, prompt “Run analysis now?” via Gooey-confirm (or start immediately with a checkbox).
  - Run engine: `run_analysis_from_config(..., engine=engine)` to keep parity.
- Output: display log text in Gooey console; surface the generated settings path(s) and outputs dir(s) at the end.

Scope boundary for first cut:
- Keep EPSG detection automatic; if detection fails, allow manual EPSG input field.
- No map previews; rely on file pickers and defaults.
- Do not alter legacy CLI signatures; GUI lives in a separate module and reuses the same helpers.
- Validation: mark required fields; enforce numeric ranges (offset ratio 0–1; spacing/length/skip threshold > 0; tide percentiles 0–100 with lower < upper; beach slope/reference elevation numeric).

Status: a first Gooey init GUI lives at `cli/gui_init.py` (`python -m cli.gui_init`) reusing the legacy helpers for folder setup, EPSG detection, transects, settings.json writing, and optional run.
Branding: drop custom icons into `assets/gooey_icons/` (program_icon.png/.ico, config_icon.png, start.png, stop.png, success.png, error.png, refresh.png, spinner.png); Gooey will pick them up automatically.
Layout: the GUI uses tabbed navigation (`navigation="TABBED"`, `tabbed_groups=True`) so argument groups appear as tabs rather than a long scroll.
Site rerun GUI: `python -m cli.gui_site_rerun` mirrors the legacy `site-rerun` flow (pick settings.json, optional ref/transects overrides, optional transect regeneration, clear outputs, run now).

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

## Full Setup Order (clone → env → GEE → tide)
1) Clone the repo:
```
git clone https://github.com/BenJTowers/CoastSatCLI.git
cd CoastSatCLI
```
2) Create/activate the environment:
```
conda env create -f environment.yml
conda activate coastsat
```
3) Configure Google Earth Engine (needed for imagery download):
```
# install Google Cloud SDK if you don't have it
gcloud init
gcloud auth application-default login
# record your project name for CoastSat scripts
gcloud config get-value project
```
4) Prepare tide inputs:
   - **FES model**: ensure you have the FES2022 YAML config; point `inputs.fes_config` in `settings.json` to it.
   - **Tide CSV**: if using gauge CSVs, set `inputs.tide_csv_path`, `reference_elevation`, and `beach_slope` in `settings.json`.
   - Optional: add `tide_filter` percentiles to filter extremes.
5) Initialize a site (legacy CLI) to produce `settings.json`:
```
python cli/CoastsatCLI.py init
```
6) Run analysis:
```
python cli/CoastsatCLI.py run --config path/to/settings.json --engine pipeline   # new runner
# or omit --engine to use the legacy scripts
```

## Testing
Run the fast checks before sharing changes:
```
pytest tests -q
```
For a smoke test, point the new pipeline at a small fixture `settings.json` and verify outputs under its `output_dir`.

## Status & Next Steps
- The refactor plan (`coastsat_pipeline/PLAN.md`, `docs/refactor/`) tracks migration of stages from legacy scripts.
- Prefer the new pipeline for headless runs; keep the legacy CLI only as a compatibility path while migration completes.
