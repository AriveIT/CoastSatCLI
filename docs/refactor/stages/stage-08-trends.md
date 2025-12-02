# Stage 08 — Trend Calculation & Export

Stage 08 mirrors `calculate_and_save_trends(transects, cross_distance_tidally_corrected, output, settings, slope_est, trend_dict)` in the current script. It produces the final shoreline-change metrics, updates transect GeoJSON attributes, and writes CSV summaries.

## Migration Status

- ✅ `TrendCalculationStage` now calls `coastsat_pipeline.helpers.trends.compute_and_save_trends`, preferring the cleaned cross-distance arrays from Stage 07 when available.
- ✅ `helpers/trends.py` defines `TransectTrend`/`TrendExportResult`, logs progress, and exports GeoJSON artifacts via GeoPandas.
- ✅ Tests cover both the helper behavior (`tests/test_trends_helper.py`) and the pipeline stage wiring.

---

## Current Behavior

- **Function:** `calculate_and_save_trends(...)`
- **Responsibilities:**
  - Compute long-term shoreline change trends per transect using the processed time-series data.
  - Merge slope/tide stats and other metadata into the results.
  - Update transect GeoJSON files with new attributes (trend values, QC flags).
  - Write CSV summaries (trend tables) and optional debug files.
  - Return the final `trend_dict`.

Pain points:
- Logic is closely tied to file I/O (writing GeoJSON/CSV) within the same function.
- Trend dict is loosely structured; downstream consumption is implicit.
- Lack of modularity makes it hard to plug in alternate trend methods or additional outputs.

---

## Target Design

- **Inputs:** `PipelineContext` containing:
  - `cross_distance_processed` (from Stage 07).
  - `cross_distance_tidally_corrected` (if needed for reference).
  - `trend_dict` (preliminary metrics from Stage 07).
  - `transects`, `slope_est`, `tide_stats`.
  - Output paths / configuration for CSV/GeoJSON exports.
- **Outputs:** context updated with:
  - `trend_results`: structured records per transect (trend value, confidence intervals, QC flags).
  - References to exported files (CSV, GeoJSON, additional artifacts).

### Planned Implementation Steps
1. **Computation vs I/O**
   - Separate pure trend computation from file-writing.
   - Implement `compute_trends(transects, processed_timeseries, config)` returning structured results.
   - Have a helper handle exports (CSV/GeoJSON) using the computed results.
2. **Data structures**
   - Define `TransectTrend` dataclass with fields: `transect_id`, `trend_value`, `confidence`, `slope`, `flags`, etc.
   - Store list of `TransectTrend` in context for future reporting.
3. **Exports**
   - Write CSV/GeoJSON using standardized helper functions with consistent schemas.
   - Include tide filter stats, slope info, and QC flags in exports.
4. **Validation**
   - Ensure transects flagged as sparse/noisy carry through to final outputs, possibly with warnings.

### Interface Sketch
```python
class TrendCalculationStage(PipelineStage):
    name = "trends"
    description = "Compute shoreline change trends and export final artifacts."

    def run(self, context: PipelineContext) -> None:
        trends = compute_trends(
            transects=context.transects,
            cross_distance=context.cross_distance_processed,
            config=context.settings.trends
        )
        export_trend_outputs(trends, context.paths, context.output_options)
        context.trend_results = trends
```

---

## Migration Tasks

- [ ] Refactor trend computation into testable helpers separated from I/O.
- [ ] Define `TransectTrend` (or similar) dataclass and adopt it across the pipeline.
- [ ] Update CSV/GeoJSON writers to rely on the structured data rather than ad-hoc dicts.
- [ ] Ensure trend results include slope/tide metadata and QC flags.
- [ ] Add tests verifying CSV/GeoJSON contents and schema.
- [ ] Move the legacy `calculate_and_save_trends` logic into `coastsat_pipeline/helpers/trends.py` and update `TrendCalculationStage` to call it.

---

## Open Questions / TODOs

- Multiple trend algorithms (linear, robust, etc.) may be added later; design the stage so additional methods can be plugged in when requirements solidify.
- Outstanding items (extra exports, schema versioning, rerun change logs) remain to be answered; capture decisions once stakeholders provide direction.
