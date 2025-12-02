# Stage 05 — Tide Correction

Stage 05 follows the slope estimation step and applies tide adjustments using FES2022 or CSV-based tide data. It corresponds to the `tidal_correction` function in `Complete_Analysis.py`.

---

## Current Behavior

- **Function:** `tidal_correction(output, cross_distance, transects, settings, slope_est, dates_sat, tides_sat)`
- **Responsibilities:**
  - Load tide model configuration (`fes2022.yaml`) or CSV tide file.
  - Compute tide values for each shoreline detection timestamp.
  - Apply slope-based adjustments to cross-shore distances.
  - Apply percentile filters (`tide_filter`) to remove extreme tide events.
  - Update GeoJSON/CSV outputs with tide-adjusted positions.
  - Return `cross_distance_tidally_corrected`.

Pain points:
- Many positional parameters; stage access to context would make dependencies clearer.
- Tide stats (thresholds, removal counts) are logged but not structured.
- CSV-based tide mode logic is partially duplicated in CLI scripts.

---

## Target Design

- **Inputs:** `PipelineContext` with:
  - `cross_distance`, `dates_sat`, `tides_sat` from Stage 04.
  - `slope_est` results.
  - Tide configuration (FES or CSV) and filter settings from Stage 00.
  - Transect geometries/metadata.
- **Outputs:** context updated with:
  - `cross_distance_tidally_corrected`.
  - `tide_stats`: structured data capturing thresholds, removal counts, and any anomalies.
  - References to updated artifacts (e.g., GeoJSON with tide-adjusted attributes).

### Planned Implementation Steps
1. **Stage encapsulation**
   - Implement `TideCorrectionStage` that consumes context and mutates it with corrected arrays/stats.
   - Branch internally for FES vs CSV tide sources.
2. **Slope dependency**
   - Require Stage 04 to populate `slope_est` before running. If slopes are missing, either compute fallback values or skip tide correction with a warning.
3. **Filter stats**
   - Persist percentile thresholds and counts in context and include them in exported metadata for transparency.
4. **Output packaging**
   - Store corrected arrays in dataclasses for downstream stages (plots, time-series post-processing).
   - Provide hooks to regenerate GeoJSON/CSV outputs if needed (or call shared export utilities).

### Interface Sketch
```python
class TideCorrectionStage(PipelineStage):
    name = "tide"
    description = "Apply tide adjustments using FES2022 or CSV tides."

    def run(self, context: PipelineContext) -> None:
        corrected, stats = apply_tide_adjustments(
            cross_distance=context.cross_distance,
            dates_sat=context.dates_sat,
            slopes=context.slope_est,
            transects=context.transects,
            tide_config=context.settings.tide
        )
        context.cross_distance_tidally_corrected = corrected
        context.tide_stats = stats
```

---

## Migration Tasks

- [ ] Refactor tide correction logic into helper functions with explicit inputs/outputs.
- [ ] Unify FES vs CSV tide handling so both modes share validation and error reporting.
- [ ] Capture tide filter stats and write them into context and optional output files.
- [ ] Ensure corrected arrays replace raw ones in downstream stages (plots, time-series).
- [ ] Add tests covering both tide modes and percentile filtering with sample data.
- [ ] Move the legacy `tidal_correction` implementation into `coastsat_pipeline/helpers/tide.py` so the stage no longer imports from `Complete_Analysis`.

---

## Open Questions / TODOs

- **Tide model fallback:** No need to juggle multiple models; if the configured model/data fails, the stage should fail gracefully and report the issue.
- **Dataset location:** Assume FES datasets live on local disks; no special handling for network drives is required beyond standard path validation.
- **Diagnostics:** Emit per-transect tide diagnostics (e.g., points removed, average correction) and store them in context or output files for analyst review.
- **Dry-run mode:** Consider whether a dry-run/report-only mode adds value; if not, defer until user demand surfaces.
