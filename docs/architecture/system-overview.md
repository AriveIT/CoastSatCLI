# System Overview

CoastSatCLI implements an analytics workflow that behaves like a **pipe-and-filter** architecture: each stage ingests a well-defined artifact, transforms it, and passes the result downstream. The CLI keeps those stages scriptable so analysts can re-run any portion when AOIs or reference data change.

## 1. System Context & Dependencies

- **External services**
  - *Google Earth Engine (GEE)* — imagery retrieval for Landsat/Sentinel missions.
  - *FES2022 tide model* — tidal harmonics and correction factors via `pyfes`.
  - *Storage backends* — local disks or network shares sized for multi-decade imagery stacks per AOI.
- **Local compute**
  - Python 3.11 environment with geospatial libraries (GDAL, GeoPandas, rasterio, shapely).
  - Optional GPU hardware when retraining classifiers, though inference runs on CPU today.
- **Users**
  - Coastal analysts preparing AOIs and validating results.
  - Developers extending classifiers, CLI logic, or automation harnesses.

## 2. Primary Components

1. **Input capture (CLI / dialogs)** — gathers AOI metadata, file paths, EPSG codes, and optional tide filters, then materializes a canonical `settings.json`.
2. **Scheduler / dispatcher** — `coastsatcli.py` shells out to `Complete_Analysis.py` or the no-tide variant, passing the resolved configuration.
3. **Processing filters** — CoastSat modules pull imagery from GEE, classify shorelines, export GeoJSON/CSV artifacts, and emit QC plots.
4. **Tide correction filter** — wraps CoastSat results with FES2022 lookups, slope estimation, and percentile filtering.
5. **Reporting / packaging** — organizes outputs into predictable subdirectories and emits status summaries (`show` command).

Each filter only depends on the upstream artifact; for example, tide correction reads shoreline time series from the analysis output, independent of how the transects were generated.

## 3. Deployment & Runtime Assumptions

- Commands run locally under Windows (primary), macOS, or Linux with Miniforge/Mamba.
- Users clone the repo and keep project data under `<root>/<sitename>/`.
- Earth Engine authentication must be configured before the `run` stage, otherwise imagery retrieval fails early.
- Batch execution of multiple AOIs can be orchestrated externally (e.g., PowerShell/Python scripts) by iterating over settings files.

## 4. Data Contracts Between Stages

| Artifact | Producer | Consumer | Notes |
| --- | --- | --- | --- |
| `settings.json` | `init` command | All subsequent commands | Absolute paths preferred to avoid ambiguity during reruns. |
| AOI / shoreline / transect GeoJSON | Analyst inputs or generated during init | CoastSat analysis scripts | Stored under `<sitename>/inputs/`. |
| Imagery cache (`/temp` or GEE tasks) | CoastSat download routines | Classification filters | Cached to avoid re-downloading when rerunning. |
| Shoreline detections & QC plots (`outputs/plots`, GeoJSON) | `Complete_Analysis*.py` | Analysts, tide correction stage | File names encode transect IDs and timestamps. |
| Tide-adjusted CSVs & slope stats | Tide correction modules | Downstream analytics, reporting | Includes percentile filter metadata for transparency. |

Future diagrams (Mermaid or image exports) will be added once we document the automation harness in `docs/ops/`.
