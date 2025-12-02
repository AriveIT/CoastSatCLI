# Stage 03 — Shoreline Analysis & Exports

Stage 03 covers the existing `shoreline_analysis` function, which converts the raw shoreline detection output into plots, GeoJSON files, and CSV tables. This is where most user-facing artifacts are generated before tide correction.

---

## Current Behavior

- **Function:** `shoreline_analysis(output, settings)` in `Complete_Analysis.py`.
- **Responsibilities:**
  - Create directories under `<sitename>/outputs/` (`plots`, `time_series`, `debug`, etc.).
  - Generate composite plots (shoreline overlays, transect time series) using Matplotlib/CoastSat helpers.
  - Export GeoJSON/CSV files summarizing cross-shore distances, per-transect stats, and QC metadata.
  - Save intermediate arrays (`cross_distance`, `dates_sat`, `tides_sat`) for use in later stages.
  - Log status messages and catch exceptions per transect.

Pain points:
- Plotting, data export, and directory management are intertwined, making it hard to skip or rerun subsets.
- Heavy reliance on global settings flags; little validation that output directories exist/writable.
- Minimal separation between headless/batch runs versus interactive workflows.

---

## Target Design

- **Inputs:** `PipelineContext` containing:
  - `shoreline_output` from Stage 02 (raw detection results).
  - `analysis_settings` with plotting/export preferences.
  - Resolved output directories.
- **Outputs:** context enriched with:
  - `cross_distance` arrays and metadata needed by tide correction.
  - `analysis_artifacts` registry capturing generated file paths (plots, CSVs, GeoJSON).
  - QA/QC summaries for reporting/logging.

### Planned Implementation Steps
1. **Directory orchestration**
   - Ensure directory creation is centralized (possibly Stage 01 or a shared utility) so Stage 03 focuses on content generation.
2. **Substage separation**
   - Break `shoreline_analysis` into smaller helpers:
     - `export_time_series()`
     - `generate_plots()`
     - `write_debug_artifacts()`
   - Stage 03 orchestrates these helpers; future iterations could promote them to independent filters if needed.
3. **Headless controls**
   - Respect config flags for skipping heavy plots or debug outputs (useful for batch runs).
   - Provide consistent naming conventions for outputs to simplify downstream ingestion.
4. **Data packaging**
   - Store `cross_distance`, `dates_sat`, `tides_sat`, and any other arrays in structured dataclasses so Stage 04 can consume them cleanly.
5. **Error handling / QA**
   - When plot generation fails for a transect, record the error in context but allow the stage to continue (unless it’s fatal).
   - Produce summary metrics (number of transects processed, skipped) for logs and potential UI display.

### Interface Sketch
```python
class AnalysisStage(PipelineStage):
    name = "analysis"
    description = "Generate plots, CSVs, and GeoJSON artifacts from shoreline detections."

    def run(self, context: PipelineContext) -> None:
        outputs = generate_analysis_artifacts(
            shoreline_output=context.shoreline_output,
            settings=context.analysis_settings,
            paths=context.paths
        )
        context.analysis_artifacts = outputs.artifacts
        context.cross_distance = outputs.cross_distance
        context.dates_sat = outputs.dates_sat
        context.tides_sat = outputs.tides_sat
```

---

## Migration Tasks

- [ ] Extract directory creation logic into a shared helper so this stage assumes folders already exist.
- [ ] Refactor plotting/export code into reusable functions or classes (with unit tests where practical).
- [ ] Define data structures for `analysis_artifacts` (e.g., list of `OutputArtifact` entries with type/path/metadata).
- [ ] Add config toggles (Stage 00) for enabling/disabling plots, debug exports, etc.
- [ ] Capture per-transect QC summaries in context for potential dashboards or reporting.

---

## Open Questions / TODOs

- **Artifact tracking:** Track the individual artifact types we already generate (plots, CSVs, GeoJSON files). The volume is manageable, so per-artifact entries are acceptable; no need for coarse per-folder logging.
- **Tide-corrected vs raw plots:** Keep the existing raw plots in Stage 03 for early QA, but plan to add tide-corrected variants in the later stage (Stage 5) without duplicating logic.
- **Time-series plotting constraints:** Current “time series raw” plots try to cram all transects into one image, which breaks for large sites. Design this stage so it can produce paginated or per-transect plots instead of a single oversized figure.
- **Naming templates:** Not required right now; stick to the existing naming conventions managed by CoastSat.
- **Error surfacing:** Decide whether to log warnings in context (for UI display) or produce a lightweight QA report that downstream tooling can parse.
