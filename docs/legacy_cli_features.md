# Legacy CLI Capabilities (Typer + Tk dialogs)

This summarizes what the legacy `cli/CoastsatCLI.py` provides so we can mirror it in a GUI while keeping the legacy entrypoint intact.

## Commands
- `init [--engine legacy|pipeline]`: guided project creation and optional immediate analysis run.
- `site-rerun [--engine legacy|pipeline]`: re-run an existing site with optional input overrides and output clearing.
- `run --config PATH [--engine legacy|pipeline]`: execute analysis for a given `settings.json`.

## Settings.json creation (init flow)
- Prompts for base project folder and sitename (lowercased, required).
- Prompts for shoreline file (GeoJSON/Shapefile) and loads it.
- Prompts for tidal correction method:
  - `fes`: pick FES2022 YAML path; stored as `inputs.fes_config` (absolute).
  - `csv`: pick tide CSV; prompts `reference_elevation` and `beach_slope`; stored as `inputs.tide_csv_path`, `reference_elevation`, `beach_slope`.
  - Optional tide filtering: prompts percentiles; stored as `tide_filter.lower_percentile`/`upper_percentile`.
- Single vs batch:
  - Batch: pick multiple AOI KMLs; sitenames are suffixed `_001`, `_002`, …; shoreline is preloaded once.
  - Single: pick one AOI KML.
- EPSG: auto-detects Canadian UTM EPSG from AOI centroid; if detection fails, user can enter manually.
- Folders/files per site (under `<base>/<sitename>/`):
  - `inputs/`: copied AOI (`<sitename>_aoi.kml`), generated reference shoreline (`<sitename>_ref.geojson`), generated transects (`<sitename>_transects.geojson`).
  - `outputs/`: created empty.
- Transect generation: prompts whether to customize; parameters:
  - `transect_spacing` (default 100 m)
  - `transect_length` (default 200 m)
  - `transect_offset_ratio` (default 0.75, seaward vs landward split)
  - `transect_skip_threshold` (default 300 m)
- `settings.json` contents (relative paths, except tide extras):
  - `inputs.sitename`
  - `inputs.aoi_path`, `inputs.reference_shoreline`, `inputs.transects` (relative to site dir)
  - Optional `inputs.fes_config` or `inputs.tide_csv_path` (+ `reference_elevation`, `beach_slope`)
  - Optional `tide_filter`
  - `output_dir` (relative `outputs/`)
  - `output_epsg` (auto or manual)
- After writing `settings.json`, prompts to run analysis immediately (uses chosen `--engine`).

## Analysis execution (run + init prompt)
- `engine=legacy`: picks script based on tide inputs (`Complete_Analysis.py` or `Complete_Analysis_CSV.py`) and runs `python <script> --config <settings.json>`.
- `engine=pipeline`: calls `coastsat_pipeline.cli.run_pipeline_from_config`.
- Exit code surfaced; success/failure messages printed.

## Site rerun workflow
- Pick existing `settings.json`; loads config.
- Optional overrides:
  - Replace reference shoreline (copies into project `inputs/` and marks transects for regeneration).
  - Replace transects file directly.
  - Change transect settings to regenerate transects.
- Optional clear outputs (deletes files in `outputs/`).
- Regenerates transects if flagged, then prompts to run analysis (respects `--engine`).

## UI/interaction details
- Uses Typer prompts + Tk file/folder dialogs (`choose_file`, `choose_folder`, multi-file picker).
- Batch mode reuses loaded shoreline to avoid re-reading per AOI.
- Prints timing and summary of generated paths/EPSG after init.
