# Stage 04 — Slope Estimation

Stage 04 captures the logic in `slope_estimation(settings, cross_distance, output)`, which computes beach slopes for each transect to support tide correction and trend analysis.

---

## Current Behavior

- **Function:** `slope_estimation(settings, cross_distance, output)` in `Complete_Analysis.py`.
- **Responsibilities:**
  - Iterate over transects, extract time series, and compute slopes using spectral analysis (`SDS_slope` utilities).
  - Generate diagnostic plots (e.g., slope spectrum) saved under `outputs/slopes/`.
  - Return:
    - `slope_est`: dict of transect ID → slope estimate.
    - `dates_sat`: date arrays for each satellite/transect.
    - `tides_sat`: tide values aligned with detections.
- The function depends on data produced by Stage 03 (`cross_distance`, `output`) and writes files needed for QA.

Pain points:
- Mixed responsibilities (computation + plotting + data export).
- Outputs are plain dicts/arrays without strong typing.
- No caching; recomputes slopes even if inputs unchanged.

---

## Target Design

- **Inputs:** `PipelineContext` with:
  - `cross_distance` arrays from Stage 03.
  - Transect metadata (IDs, geometries).
  - Slope configuration (e.g., spectral window sizes) from Stage 00.
- **Outputs:** context enriched with:
  - `slope_est`: structured data class or dict with slope values and confidence intervals.
  - `slope_artifacts`: references to plots and diagnostic files.
  - `dates_sat`, `tides_sat` arrays required by Stage 05 (tide correction).

### Planned Implementation Steps
1. **Encapsulate computation**
   - Create `SlopeEstimationStage` that wraps the existing `SDS_slope` workflow.
   - Allow reuse of computed slopes when configuration and inputs have not changed (future optimization).
2. **Plotting controls**
   - Support config flag to skip slope plots during headless/batch runs.
   - Standardize file naming and capture artifact paths in context.
3. **Data structures**
   - Define `SlopeResult` dataclass: `transect_id`, `slope_value`, `confidence_interval`, `metadata`.
   - Store `dates_sat`/`tides_sat` in context fields for later stages.
4. **Error handling**
   - Handle cases where slope estimation fails for a transect (e.g., insufficient data) by logging and marking slope as `None`, allowing tide correction to fall back gracefully.

### Interface Sketch
```python
class SlopeEstimationStage(PipelineStage):
    name = "slope"
    description = "Estimate transect slopes via spectral analysis."

    def run(self, context: PipelineContext) -> None:
        result = estimate_slopes(
            cross_distance=context.cross_distance,
            transects=context.transects,
            config=context.settings.slope
        )
        context.slope_est = result.slopes
        context.slope_artifacts = result.artifacts
        context.dates_sat = result.dates_sat
        context.tides_sat = result.tides_sat
```

---

## Migration Tasks

- [ ] Refactor the current slope estimation code into reusable helpers with typed outputs.
- [ ] Add config options for spectral parameters and plotting toggles.
- [ ] Capture plot paths and attach them to context for downstream reporting.
- [ ] Ensure `dates_sat` and `tides_sat` are stored in context for the next stage instead of being returned as loose values.
- [ ] Write unit tests around slope estimation logic (using synthetic cross-distance data).

---

## Open Questions / TODOs

- **Caching:** Rather than caching internal state, we can persist slope results to CSV and have the pipeline load them when available. No dedicated cache mechanism needed beyond that.
- **Sparse data handling:** Introduce a sparse-data flag (e.g., if observations < threshold) so downstream stages and analysts know which transects may need manual review.
- **Plot ownership:** Revisit slope-related plotting once we document the later plotting stage (`improved_transects_plot`) to decide whether certain plots move there.
- **Diagnostics:** Determine if we need additional slope QA outputs (histograms, aggregated stats) after reviewing data requirements.
