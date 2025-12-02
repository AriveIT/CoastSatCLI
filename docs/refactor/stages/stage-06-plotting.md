# Stage 06 — Enhanced Transect Plotting

Stage 06 corresponds to `improved_transects_plot(output, transects, cross_distance_tidally_corrected, settings)` in the current script. It generates additional visualizations that compare raw vs tide-corrected shoreline positions and provide QC context per transect.

---

## Current Behavior

- **Function:** `improved_transects_plot(output, transects, cross_distance_tidally_corrected, settings)`
- **Responsibilities:**
  - Iterate through transects and create plots showing:
    - Raw shoreline detections vs tide-corrected detections.
    - Metadata annotations (dates, satellites).
  - Save plots (JPEG/PNG) to `outputs/plots/` (naming convention `transect_<id>_comparison.jpg` etc.).
  - Rely on Matplotlib and existing CoastSat utilities for layout.

Pain points:
- Plots are generated in a single pass without checking for previously generated files.
- Configuration options (resolution, file format, whether to include raw lines) are hard-coded.
- No structured metadata (e.g., to display in a UI or report) beyond the images themselves.

---

## Target Design

- **Inputs:** `PipelineContext` with:
  - `output` artifacts from Stage 03 (raw detections).
  - `cross_distance_tidally_corrected` from Stage 05.
  - Transect geometry and IDs.
  - Plotting configuration (image size, DPI, file format, toggles).
- **Outputs:** context augmented with:
  - List of generated plot paths (`context.plot_artifacts`).
  - Optional metadata describing each plot (transect ID, timestamps included).

### Planned Implementation Steps
1. **Stage implementation**
   - Create `ImprovedTransectsPlotStage` that loops over transects and renders comparison plots.
   - Provide config options for:
     - Output format / DPI.
     - Whether to include raw detections, corrected detections, or both.
     - Subset of transects to plot (e.g., only flagged ones).
2. **Reuse & idempotency**
   - Skip regenerating plots if they already exist and inputs haven’t changed (optional future optimization).
3. **Metadata capture**
   - Record plot path + transect ID + timestamp range in context (and optionally JSON sidecar files) for downstream tooling.
4. **Error handling**
   - Continue processing even if a single transect plot fails; log errors and flag plots missing.

### Interface Sketch
```python
class ImprovedTransectsPlotStage(PipelineStage):
    name = "plots_comparison"
    description = "Render transect plots comparing raw and tide-corrected shorelines."

    def run(self, context: PipelineContext) -> None:
        artifacts = render_transect_plots(
            output=context.output_data,
            transects=context.transects,
            corrected=context.cross_distance_tidally_corrected,
            config=context.settings.plotting
        )
        context.plot_artifacts.extend(artifacts)
```

---

## Migration Tasks

- [ ] Extract plotting logic into a helper module (`pipeline/plots.py`) with unit-testable functions.
- [ ] Add configuration schema for plotting parameters (Stage 00) and propagate through context.
- [ ] Capture plot metadata in a structured format (list of dataclasses).
- [ ] Ensure the stage consumes tide-corrected data when available but can fall back to raw data if tide correction was skipped.
- [ ] Document runtime/size implications so batch automation can toggle this stage.
- [ ] Move the legacy `improved_transects_plot` implementation into `coastsat_pipeline/helpers/plotting.py` and update `ImprovedTransectsPlotStage` to call it, with options for color ranges/output names.

---

## Open Questions / TODOs

- Should we limit plots to transects that fail QC (e.g., flagged in Stage 07) to save time, or always render all?
- Do we need to generate additional plot types (e.g., cumulative distance charts) beyond the current comparison plots?
- Should plots include overlays like cloud masks or quality flags from earlier stages?
- How do we best surface missing plots or plotting errors to users (context log vs summary report)?
