# Data Flow Notes

The CoastSatCLI workflow can be described as a linear set of filters. Each step consumes artifacts from the previous stage, enriches them, and emits new files for the next step or for analyst review.

## 1. Input Acquisition & Normalization

| Stage | Description | Output |
| --- | --- | --- |
| Analyst prep | Provide AOI polygons, historical shoreline references, and initial transects (GeoJSON). | Raw input files under `<sitename>/inputs/`. |
| CLI init | Prompt for metadata (sitename, EPSG, tide filters), validate geometries, copy/reference files into the project folder. | Canonical `settings.json` with resolved paths and options. |

## 2. Imagery Retrieval & Preprocessing

- **Trigger**: `coastsatcli.py run --config ...`
- **Actions**:
  - Reads `settings.json`, authenticates to GEE, assembles requests for Landsat/Sentinel imagery constrained to AOIs and date ranges.
  - Downloads imagery tiles or triggers GEE tasks and caches metadata locally.
  - Applies preliminary masking and normalization defined by CoastSat.
- **Outputs**: GeoTIFF imagery stacks (temporary), metadata JSON, and logs describing acquisition coverage.

## 3. Shoreline Detection & Classification

- **Filter**: CoastSat shoreline extraction modules executed by `Complete_Analysis.py` (tide-aware) or `Complete_Analysis_No_Tide.py`.
- **Steps**:
  - Apply trained classifiers (model artifacts under `classification/`).
  - Extract transect-intersection time series, compute QC metrics, and export intermediate GeoJSON/CSV files.
  - Render diagnostic plots (shoreline overlays, transect evolution, classifier probability previews).
- **Outputs**: `outputs/plots/`, `outputs/time_series/`, GeoJSON shapefiles, intermediate CSVs for tide correction.

## 4. Tide Correction & Filtering

- **Dependencies**: FES2022 data referenced in `settings.json` (`fes_config`) and optional `tide_filter` percentiles.
- **Process**:
  - Lookup modeled tide levels for the timestamp/site of each shoreline detection.
  - Estimate beach slope per transect and adjust shoreline positions.
  - Apply percentile-based filtering to discard extreme tide events, persisting filter stats for transparency.
- **Outputs**: Tide-adjusted CSVs, slope summaries, updated GeoJSON with attributes for downstream systems.

## 5. Publication & Archiving

- **Directory layout**: enforced under `<sitename>/outputs/` (plots, CSVs, GeoJSON, logs).
- **Commands**: Analysts can run `coastsatcli.py show --config ...` to inspect the tree or integrate with external cataloging scripts.
- **Long-term storage**: Copies of final outputs (and optionally intermediate imagery) are archived to the program’s data lake / shared drive following ops guidance.

Future enhancements (batch schedulers, UI flows) will plug into the same stages. Add sequence diagrams here once we lock the automation tooling described in `docs/ops/`.
