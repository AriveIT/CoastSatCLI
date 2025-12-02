# Stage 07 — Time-Series Post Processing

Stage 07 captures `time_series_post_processing(transects, settings, cross_distance_tidally_corrected, output)` in the current script. It smooths/cleans the tide-corrected time series, prepares trend dictionaries, and exports intermediate data for the final trend calculations.

---

## Current Behavior

- **Function:** `time_series_post_processing(...)`
- **Responsibilities:**
  - Optionally reload previous output pickle (commented out today).
  - Plot mapped shorelines if `save_figure` is enabled (similar to Stage 06, but currently disabled).
  - Compute per-transect time series arrays from `cross_distance_tidally_corrected`.
  - Apply basic post-processing (smoothing, outlier handling) before trend calculations.
  - Return updated `cross_distance` (possibly cleaned) and an initial `trend_dict`.

Pain points:
- Function mixes plotting (commented) with data manipulation.
- Post-processing steps are implicit; unclear what transformations occur without reading code.
- Returns loosely structured data (`trend_dict` as dict) that feeds Stage 08.

---

## Target Design

- **Inputs:** `PipelineContext` containing:
  - `cross_distance_tidally_corrected`.
  - Transect metadata and settings (smoothing parameters, QC thresholds).
  - Tide stats if needed for QA.
- **Outputs:** context updated with:
  - `cross_distance_processed` (cleaned time series).
  - `trend_dict` or a structured data class describing preliminary trend metrics.
  - Flags/annotations for transects with sparse data or QC issues.

### Planned Implementation Steps
1. **Encapsulation**
   - Implement `TimeSeriesPostProcessingStage` that performs smoothing/outlier removal and prepares data for final trend computation.
   - Separate plotting (if reintroduced) into Stage 06 or a dedicated plotting helper.
2. **Configurable processing**
   - Expose smoothing window sizes, interpolation methods, and QC thresholds in config (Stage 00).
3. **Sparse data handling**
   - Integrate the sparse-data flag introduced in Stage 04 to annotate transects with insufficient observations.
4. **Outputs**
   - Store processed arrays and intermediate metrics in context (`context.cross_distance_processed`, `context.trend_dict_prelim`).
   - Provide summary stats (e.g., number of transects processed/skipped).

### Interface Sketch
```python
class TimeSeriesPostProcessingStage(PipelineStage):
    name = "timeseries_post"
    description = "Clean tide-corrected time series and prepare trend inputs."

    def run(self, context: PipelineContext) -> None:
        processed, trend_dict = process_time_series(
            transects=context.transects,
            cross_distance=context.cross_distance_tidally_corrected,
            settings=context.settings.timeseries
        )
        context.cross_distance_processed = processed
        context.trend_dict = trend_dict
```

---

## Migration Tasks

- [ ] Extract time-series smoothing/outlier logic into dedicated helper functions with tests.
- [ ] Ensure sparse-data flags are applied and stored in context.
- [ ] Define a schema for `trend_dict` (e.g., dataclass per transect) to avoid loosely typed dicts.
- [ ] Remove/relocate plotting code so this stage focuses purely on data prep.
- [ ] Add logging to summarize how many transects were processed, flagged, or skipped.
- [ ] Move the legacy `time_series_post_processing` implementation into `coastsat_pipeline/helpers/timeseries.py` (with options for seasonal/monthly plots) and update `TimeSeriesPostProcessingStage` to call it.

---

## Open Questions / TODOs

- Specific post-processing steps (smoothing, clipping, interpolation) will be finalized during the upcoming post-processing test phase; for now keep existing logic and capture findings later.
- Consider allowing custom plugins after the test phase if analysts need manual QC hooks.
- Evaluate whether intermediate QA CSVs are useful once we finish the test phase.
- Flag transects that remain noisy after processing so they can be reviewed manually before final trend estimation (do not auto-exclude yet).
