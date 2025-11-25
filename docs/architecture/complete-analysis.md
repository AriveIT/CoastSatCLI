# Complete Analysis Script Breakdown

The current `Complete_Analysis.py` script is a monolithic driver for the CoastSat workflow. To prepare for a more modular, UI-friendly architecture we decompose each step below, showing inputs, outputs, and how it could be isolated as a reusable filter. The no-tide variant follows the same steps minus the *Tide Adjustment* stage.

## Stage 0 — Configuration Loading (`load_settings`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Resolve CLI-generated `settings.json`, normalize paths, and validate tide-filter parameters. | Config path passed from CLI. | In-memory config dict with absolute paths (`inputs`, `output_dir`, `fes_config`, `tide_filter`). |

*Modularity ideas*: Move path resolution into a shared module so both CLI and scripts reuse the same logic. Emit a strongly typed settings object for easier validation and IDE support.

## Stage 1 — Initial Settings (`initial_settings`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Construct the CoastSat `inputs` and `settings` dictionaries (polygon, sat list, processing flags). | Normalized config. | `inputs` for imagery retrieval and `settings` for downstream processing. |

Steps include: loading AOI polygon (`SDS_tools.polygon_from_kml`), coercing it into a rectangle, setting hard-coded date ranges and sat lists, and configuring directories. This stage should eventually pull values from `settings.json` rather than hard-coded defaults.

## Stage 2 — Batch Shoreline Detection (`batch_shoreline_detection`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Download imagery, preprocess, and detect shorelines across all dates. | `metadata`, `settings`, `inputs`. | `output` dict containing cross-shore distances, timestamps, QC attributes, and intermediate files. |

Internal filters:
1. `SDS_download.retrieve_images` / `get_metadata`
2. `SDS_preprocess.preprocess_images`
3. `SDS_shoreline.run_shoreline_detection`

Each could become its own callable so the CLI (or UI) can pause/resume after any step, improving usability. Caching metadata separately also shortens reruns.

## Stage 3 — Shoreline Analysis (`shoreline_analysis`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Generate plots, GeoJSON exports, transect stats, and QC summaries from the raw detection output. | `output`, `settings`. | Files written to `<sitename>/outputs/plots`, CSVs, GeoJSON, and `cross_distance` arrays. |

Highlights:
- Creates stacked plots per transect and satellite.
- Saves `output['cross_distance']` (core time-series matrix) and metadata used later in tide correction and slope estimation.

*Modularity lever*: break plotting/export responsibilities into separate modules so headless automation can skip heavy plotting.

## Stage 4 — Tide Adjustment (`tidal_correction`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Apply FES2022 tides and optional percentile filtering to shoreline time series. | `output`, `cross_distance`, `transects`, `settings`, `slope_est`, `dates_sat`, `tides_sat`. | `cross_distance_tidally_corrected`, filter stats, updated GeoJSON attributes. |

Details:
- Loads tide harmonics via `pyfes`.
- Estimates slopes (if not provided) and adjusts shoreline positions.
- Applies percentile filter from `settings['tide_filter']`.

To eliminate duplicate scripts, convert this stage into an optional filter that can be toggled by config flags. The no-tide script would simply bypass it.

## Stage 5 — Visualization Enhancements (`improved_transects_plot`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Generate additional plots comparing raw vs. tide-corrected time series for each transect. | `output`, `transects`, `cross_distance_tidally_corrected`, `settings`. | JPEG/PNG artifacts stored alongside earlier plots. |

Potential refactor: expose as a reusable plotting module so analysts can regenerate visuals without reprocessing imagery.

## Stage 6 — Time Series Post Processing (`time_series_post_processing`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Smooth, interpolate, and annotate shoreline time series prior to trend/slope calculations. | `transects`, `settings`, `cross_distance_tidally_corrected`, `output`. | Updated `output` with cleaned series, anomaly flags, and summary CSVs. |

This is a good candidate for splitting into smaller functions (e.g., interpolation, anomaly tagging, export) to improve readability.

## Stage 7 — Slope Estimation (`slope_estimation`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Derive beach slopes per transect using spectral analysis and produce supporting plots. | `settings`, `cross_distance`, `output`. | `slope_est` dict, confidence intervals, spectra plots, serialized stats. |

Opportunity: share slopes between runs when nothing upstream changed, or compute them lazily only when tide correction is requested.

## Stage 8 — Trend Calculation (`calculate_and_save_trends`)
| Purpose | Inputs | Outputs |
| --- | --- | --- |
| Compute long-term shoreline trends, merge them with slope/tide summaries, and save CSV/GeoJSON for reporting. | `transects`, `cross_distance_tidally_corrected`, `output`, `settings`, `slope_est`, `trend_dict`. | Final CSVs, updated transect GeoJSON with attributes, optional aggregated stats for dashboards. |

## Stage 9 — Main Driver (`main`)
| Purpose | Steps |
| --- | --- |
| Glue logic that wires the stages together. | Parse CLI args → load settings → run stages 1–8 → persist logs/errors. |

---

## Modularization Path

To address the main quality attributes—**usability** and **modularity**—consider the following refactors:

1. **Stage isolation**: convert each stage above into a dedicated module/function with explicit input/output contracts. Persist intermediate artifacts (e.g., metadata JSON, tide-adjusted arrays) so analysts can resume partway through the pipeline.
2. **Config-driven toggles**: add flags in `settings.json` for optional filters (tide correction, plotting, slope estimation). The CLI then orchestrates a single `complete_analysis` entry point with switches instead of separate scripts.
3. **Task orchestration layer**: introduce a lightweight pipeline runner that treats each stage as a filter object. This will make it easier to build a GUI or batch scheduler around the same steps.
4. **Enhanced logging & progress reporting**: emit structured status updates per stage to improve usability and support long-running jobs.

Documenting the pipeline at this granularity should guide the upcoming rearchitecture and keep the CLI, GUI, and ops automation aligned.
