# Component Catalog

This catalog describes the modules that make up CoastSatCLI, their responsibilities, and how they interact within the pipe-and-filter workflow.

| Component | Location | Responsibility | Inputs | Outputs / Consumers |
| --- | --- | --- | --- | --- |
| CLI entry point | `cli/coastsatcli.py` | Typer-based command definitions (`init`, `run`, `site-rerun`, `show`). Dispatches to analysis scripts and handles shared options. | User prompts, `settings.json` paths. | Triggers scripts in project root; writes logs/status to console. |
| Dialog helpers | `CLI/dialogs.py` | Windows-friendly dialogs for selecting files/directories, collecting text input. | User interactions. | Structured data passed back to CLI commands. |
| File utilities | `CLI/file_utils.py` | Manage project directory scaffolding, copy/reference inputs, sanity-check file existence. | Paths, CLI responses. | Project tree under `<sitename>/`, normalized config entries. |
| Geo utilities | `CLI/geo_utils.py` | Validate CRS, reproject geometries, compute transect metadata. | AOI/shoreline GeoJSON, EPSG codes. | Cleaned GeoJSON ready for CoastSat ingestion. |
| Complete analysis (tide) | `Complete_Analysis.py` | Orchestrates CoastSat shoreline extraction plus tide correction. | `settings.json`, CoastSat modules, FES2022 config. | Outputs plots, CSVs, GeoJSON under `<sitename>/outputs/`. |
| Complete analysis (no tide) | `Complete_Analysis_No_Tide.py` | Same as above but skips FES2022 adjustments for workflows where tides are not needed. | `settings.json`. | Outputs excluding tide-adjusted CSVs. |
| CoastSat core | `coastsat/` modules (e.g., `SDS_transects.py`) | Handle transect generation, image processing, shoreline classification logic inherited from CoastSat. | Imagery, geometry inputs, classifier weights. | Shoreline detections and QC metrics consumed by analysis scripts. |
| Classifier training notebooks | `classification/train_new_classifier.ipynb` | Document how to retrain shoreline classifiers with new labeled data. | Training datasets, hyperparameters. | Updated model weights stored for inference. |
| Tests | `cli/test_*.py` | Validate CLI utilities (dialogs, geo ops, line merge, clipping). | Unit inputs/mocks. | Signal regressions during CI/manual runs. |

Additional automation (batch runners, packaging scripts) will be documented here as they are added.
