# Glossary

Quick reference for terms and acronyms used throughout CoastSatCLI and the Canadian Coastal Change project. When a deeper explanation exists, follow the referenced documents.

| Term | Definition | Notes / Links |
| --- | --- | --- |
| **AOI (Area of Interest)** | Polygon describing the shoreline segment to analyze. | Stored under `inputs/aoi/`; must include CRS metadata. |
| **Reference shoreline** | Clipped shoreline geometry created from a larger dataset to match the AOI extent. | Used to seed transect generation; see `coastsat/SDS_transects.py`. |
| **Transect** | Line cast perpendicular to the shoreline to measure cross-shore distance over time. | Saved as GeoJSON with IDs; spacing/length configured during `init`. |
| **CoastSat** | Open-source toolkit for shoreline detection from satellite imagery. | CoastSatCLI orchestrates CoastSat modules in batch mode. |
| **CoastSatCLI** | Typer-based interface that initializes projects, runs analyses, and manages reruns. | Commands documented in `docs/user/cli-guide.md`. |
| **FES2022** | Finite Element Solution global tide model used for tide correction. | Requires local files + YAML config referenced in `settings.json`. |
| **Tide filter percentiles** | Lower/upper percentile thresholds applied to tide-adjusted detections to remove extreme events. | Configured via `tide_filter` block; see `docs/user/configuration.md`. |
| **Cross-shore distance** | Distance from the transect baseline to the detected shoreline at a given timestamp. | Core metric exported in CSVs; units depend on `output_epsg`. |
| **Slope estimation** | Spectral method that infers beach slope per transect for tide correction. | Outputs plots (`slope_spectrum_*.jpg`) and confidence intervals. |
| **GEE (Google Earth Engine)** | Cloud service providing access to Landsat/Sentinel imagery. | Requires authentication via `gcloud` and `earthengine` CLIs. |
| **QC (Quality Control)** | Visual and statistical checks applied to ensure shoreline detections are trustworthy. | QA/QC checklist lives in the CLI guide. |
| **Settings file** | `settings.json` containing all paths and parameters for a site. | Reference: `docs/user/configuration.md`. |
| **`site-rerun`** | CLI command that updates reference data/transects and optionally clears outputs for a clean rerun. | See CLI guide section 4. |
| **Imagery cache** | Local folder where CoastSat stores downloaded GeoTIFFs/metadata between runs. | Typically under `temp/` or OS-specific cache dirs; re-used to save time. |

Add new entries whenever jargon appears in documentation or code reviews. A consistent glossary improves onboarding and reduces ambiguity during QA discussions.
