# Stage 09 — Pipeline Driver / Orchestration

Stage 09 represents the glue logic currently in `main(config_path)` inside `Complete_Analysis.py`. It ties all previous functions together, handles logging, and exits on error. In the refactored system this becomes the pipeline runner plus CLI integration.

---

## Current Behavior

- **Function:** `main(config_path)`
- **Responsibilities:**
  - Load configuration and print site info.
  - Sequentially call each stage function:
    1. `load_settings`
    2. `initial_settings`
    3. `batch_shoreline_detection`
    4. `shoreline_analysis`
    5. `slope_estimation`
    6. `tidal_correction`
    7. `improved_transects_plot`
    8. `time_series_post_processing`
    9. `calculate_and_save_trends`
  - Catch minimal errors and print completion message.
- There is no structured context object; functions pass large dictionaries around. CLI commands shell out to this script directly.

---

## Target Design

- Replace the monolithic `main` with:
  - `PipelineContext`: shared state object populated at Stage 00 and modified by each filter.
  - `PipelineStage` classes organized in a stage registry (see ADR 004).
  - `PipelineRunner` that iterates through enabled stages, handles logging, and allows opt-in/out per config.
- CLI (`coastsatcli.py run`) will construct the context, choose the runner, and capture/report errors.

### Planned Implementation Steps
1. **Stage registry**
   - Define the default stage order (Stages 00–08) in a central registry.
   - Allow config/CLI flags to skip or insert stages (e.g., no tide correction).
2. **Runner implementation**
   - Implement runner logic per ADR 004 (stage classes, context, logging hooks).
   - Provide progress callbacks so future UI layers can display status.
3. **Error handling**
   - Ensure failures in one stage provide clear messages and optionally allow resuming from a specific stage.
4. **Integration**
   - Modify CLI to instantiate the runner instead of calling legacy scripts.
   - Keep legacy script available behind a flag until the new pipeline is proven.

### Interface Sketch
```python
runner = PipelineRunner(
    stages=[
        ConfigLoadStage(),
        InitializationStage(),
        ImageryStage(),
        AnalysisStage(),
        SlopeEstimationStage(),
        TideCorrectionStage(),
        ImprovedTransectsPlotStage(),
        TimeSeriesPostProcessingStage(),
        TrendCalculationStage(),
    ]
)
runner.run(context)
```

---

## Migration Tasks

- [ ] Implement `PipelineContext`, `PipelineStage`, and `PipelineRunner`.
- [ ] Build adapters for existing functions to conform to stage interfaces during transition.
- [ ] Add CLI flag to choose between legacy script and new runner.
- [ ] Write integration tests that run the pipeline on a sample `settings.json`.
- [ ] Remove `Complete_Analysis.py` once the new pipeline is stable and documented.

---

## Open Questions / TODOs

- How should we persist pipeline state to resume mid-run (optional feature)?
- What level of progress reporting is required for batch UI / logging systems?
- Do we need to support conditional branching (e.g., skip imagery download if already cached) via config or stage metadata?
- How will we version/check compatibility of stages to ensure runners remain consistent across releases?
