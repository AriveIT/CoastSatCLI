# CoastSat Project Toolkit

CoastSatCLI is a command-line interface that operationalizes CoastSat for the Canadian Coastal Change program. It helps researchers go from raw shoreline inputs to tide-corrected change metrics using a repeatable, automated workflow.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Highlights](#system-highlights)
3. [End-to-End Workflow](#end-to-end-workflow)
4. [Architecture Snapshot](#architecture-snapshot)
5. [Requirements & Setup](#requirements--setup)
6. [Known Limitations & Roadmap](#known-limitations--roadmap)
7. [Contributing & Support](#contributing--support)
8. [Documentation Links](#documentation-links)

---

## Project Overview

Canada’s coastline stretches over 200,000 km and exhibits large spatial variability in geomorphology, forcing, and available observations. The Canadian Coastal Change program aims to build a consistent 40+ year history of shoreline change for priority Areas of Interest (AOIs). Manually running CoastSat per AOI is slow, hard to reproduce, and error prone. CoastSatCLI addresses those issues by:

- Guiding analysts through a structured initialization of AOIs, transects, and reference shorelines.
- Automating the CoastSat processing pipeline (imagery download, shoreline detection, QC artifacts, tide correction, exports).
- Storing inputs/outputs with clear provenance so that future reruns can compare how decisions changed results.

The README introduces the project from first principles; long-form technical documentation now lives under `docs/`.

---

## System Highlights

- **CLI front-end for CoastSat**: Typer-powered commands (`init`, `run`, `site-rerun`, `show`) encode best practices for Canadian AOIs. A lightweight GUI is planned once the CLI feature set stabilizes.
- **Automated tide-aware pipeline**: The default workflow wires CoastSat outputs into FES2022 tide corrections and percentiles-based filtering so you can go straight from raw imagery to slope CSVs and plots.
- **Speed & reproducibility improvements**:
  - Headless execution batches CoastSat steps without manual notebook intervention.
  - Shared utilities in `CLI/` (file helpers, geo transforms, dialog prompts) ensure analysts follow the same data layout.
  - Rerun tooling lets you surgically update transects or reference shorelines while keeping other assets intact.
- **Extendable architecture**: Classifier training notebooks and scripts live in `classification/`, while tidal/no-tide variants of the analysis are maintained side by side. ADRs capture the bigger design decisions.

---

## End-to-End Workflow

### 1. Initialize a Site (`python cli/coastsatcli.py init`)
- Launches an interactive prompt (or dialog on Windows) to collect sitename, AOI polygons, shoreline inputs, reference data, transect options, and optional tide filters.
- Produces a canonical project tree:
  ```
  <base>/<sitename>/
  ├─ inputs/
  │  ├─ shoreline/
  │  ├─ aoi/
  │  ├─ reference/
  │  └─ transects/
  ├─ outputs/
  └─ settings.json
  ```
- Writes `settings.json` with resolved paths, EPSG choices, and tide configuration so subsequent commands can run unattended.

### 2. Run the Complete Analysis (`python cli/coastsatcli.py run --config ...`)
- Invokes `Complete_Analysis.py` (tide-aware) or `Complete_Analysis_No_Tide.py` based on the settings file.
- Steps include imagery retrieval through the CoastSat Google Earth Engine (GEE) stack, shoreline classification, QC plots, slope estimation, CSV export, and optional media outputs.
- Tide corrections use `pyfes` plus site-specific percentile filters when configured.

### 3. Inspect Outputs & Iterate
- Use `python cli/coastsatcli.py show --config ...` to summarize the output tree (plots, GeoJSON, CSVs).
- Analysts typically review:
  - Shoreline overlay plots and transect-by-transect time series.
  - CSV statistics for slope changes, tide adjustments, and filter counts.
  - Debug GeoJSON files for manual QA/QC.

### 4. Rerun with Updated Inputs (`python cli/coastsatcli.py site-rerun`)
- Designed for cases where transect placement, AOIs, or reference shorelines evolve.
- Optionally clears previous outputs while keeping imagery caches, so reruns focus on the changed components.
- Ensures the provenance of new outputs is tied to the updated configuration.

> **Future workflows**: A simple desktop UI will sit on top of the same commands, and we plan to document additional automation (batch runs, scheduler integration) inside `docs/ops/`.

---

## Architecture Snapshot

| Layer | Purpose | Key Assets |
| --- | --- | --- |
| CLI Interface | Collects user input, validates configuration, dispatches jobs. | `cli/coastsatcli.py`, `CLI/dialogs.py`, `CLI/file_utils.py`, `CLI/geo_utils.py` |
| Analysis Engines | Execute CoastSat shoreline extraction with and without tide correction. | `Complete_Analysis.py`, `Complete_Analysis_No_Tide.py`, scripts in `coastsat/` |
| Classification & Training | Train/refresh classifiers for shoreline detection. | `classification/train_new_classifier.ipynb` |
| Documentation & Decisions | Provide context for architecture, operations, and contributions. | `docs/` tree with ADRs, architecture notes, ops runbooks, user/dev guides |

Additional diagrams and component deep dives will be maintained in `docs/architecture/` as they mature.

---

## Requirements & Setup

This project targets Miniforge/Mamba environments on Windows (primary), Linux, and macOS. Python 3.11 is the current tested version. An `environment.yml` will be published once dependency locking stabilizes; for now follow the steps below.

### 1. Install & Configure the Conda/Mamba Environment

Use Miniforge so the `conda-forge` channel is the default:

1. Download Miniforge for your platform: <https://github.com/conda-forge/miniforge#miniforge3>
2. Install it and open a Miniforge (or terminal) prompt.
3. Create and activate the CoastSat environment using the provided spec (recommended):

```bash
conda env create -f environment.yml
conda activate coastsat
```

If Conda is slow on your machine and you have `mamba` installed, you can substitute `mamba env create` / `mamba activate`.

If you prefer manual installation, follow the steps below:

```bash
conda create -n coastsat
conda activate coastsat
conda install python=3.11 geopandas gdal -y
conda install earthengine-api scikit-image matplotlib astropy notebook -y
pip install pyqt5 imageio-ffmpeg
conda install pyfes -y
conda install pyyaml -y
```

Your prompt should now start with `(coastsat)`. If you hit dependency issues, clean up and retry:

```bash
conda clean --all
conda update conda
```

> Prefer `conda` for compatibility. If you already use `mamba`, it can replace any of the commands above for faster solves. Keep the environment activated (`conda activate coastsat`) before running CLI commands.

### 2. Activate the Google Earth Engine (GEE) API

1. Request access: <https://signup.earthengine.google.com/>
2. Install the Google Cloud SDK: <https://cloud.google.com/sdk/docs/install>
3. Initialize and authenticate:
   ```bash
   gcloud init
   gcloud auth application-default login
   ```
4. Record your GEE project name (`gcloud config get-value project`) and configure the CoastSat scripts, e.g.:
   ```python
   project_name = "ee-yourproject"
   SDS_download.authenticate_and_initialize(project_name)
   ```

If authentication keeps expiring, rerun `gcloud auth application-default login` or `gcloud components update`.

### 3. Clone and Run

```bash
git clone https://github.com/BenJTowers/CoastSatCLI
cd CoastsatCLI
conda activate coastsat
python cli/coastsatcli.py --help
```

---

## Known Limitations & Roadmap

- **Outlier detection**: Extreme shoreline positions occasionally slip through current QC thresholds. Work is underway to incorporate more robust statistical filters and manual review tooling.
- **Slope calculation**: The slope estimation used for tide correction is sensitive to sparse observations on some transects. We are evaluating improved interpolation methods and confidence scoring.
- **User interface**: A desktop UI is planned to lower the barrier for new analysts. Until then, the CLI remains the supported entry point.

Follow upcoming ADRs and issue discussions in `docs/adrs/` for decisions on these topics.

---

## Contributing & Support

We welcome contributions from the Canadian Coastal Change team and collaborators:

1. Fork and branch from `main`.
2. Keep changes focused; include tests or manual validation notes for CLI flows.
3. Submit a pull request describing the motivation, testing, and any documentation updates.

Open issues or discussions on GitHub for bugs, enhancement ideas, or documentation requests. Internal program members can also reach the maintainers via the usual NRCan channels.

For coding standards, testing expectations, and release guidance see the draft documents in `docs/dev/`.

---

## Documentation Links

Long-form documentation now lives in `docs/`:

- [`docs/README.md`](docs/README.md) — high-level documentation plan and folder map.
- [`docs/adrs/`](docs/adrs) — Architecture Decision Records (start with `ADR-000-template.md`).
- [`docs/architecture/`](docs/architecture) — system context, component catalogs, data flow notes.
- [`docs/ops/`](docs/ops) — operational runbooks and environment/deployment references.
- [`docs/user/`](docs/user) — CLI walkthroughs, configuration references, troubleshooting, glossary.
- [`docs/dev/`](docs/dev) — contribution guide, testing strategy, release/versioning plans.

The README will stay focused on onboarding and cross-link to richer documents as they evolve.

---
