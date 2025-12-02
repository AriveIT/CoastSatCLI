# CoastSat Pipeline Refactor — Implementation Plan

This document translates the stage-by-stage analysis into a concrete roadmap for building the new pipeline infrastructure while keeping the legacy scripts available. The new code will live under `coastsat_pipeline/` so we can iterate alongside the existing implementation.

---

## 1. Core Infrastructure

### 1.1 Package Setup
- Create `coastsat_pipeline/` package with submodules:
  - `context.py` — `PipelineContext` dataclass and helper methods.
  - `stage.py` — `PipelineStage` Protocol / base class with `name`, `description`, `should_run()`, `run()`.
  - `runner.py` — `PipelineRunner` that executes an ordered list of stages, logs progress, and handles errors.
  - `registry.py` — stage registry definition (default order + factory functions).

### 1.2 Context & Data Models
- Define typed data classes for artifacts shared across stages (e.g., `Settings`, `InputsConfig`, `SlopeResult`, `TransectTrend`).
- Provide serialization helpers where needed (e.g., to persist resolved settings for debugging).

### 1.3 Runner Behavior
- Runner responsibilities:
  - Initialize logging/progress callbacks.
  - Iterate through stages, calling `should_run(context)` and `run(context)`.
  - Capture timing/metrics per stage.
  - Bubble up structured errors so the CLI/UI can present meaningful messages.
- Support CLI flags to skip specific stages (e.g., `--no-tide`).

---

## 2. Incremental Stage Migration

Stage order mirrors the analyzed flow (Stage 00–08). For each stage we will:
1. Implement a new stage class under `coastsat_pipeline/stages/`.
2. Wrap existing functionality via adapters to keep behavior identical.
3. Add unit tests around the new stage interfaces.
4. Update the stage registry to include the new implementation.

### Stage 00: Config Load
- Port `load_settings` into `ConfigLoadStage`.
- Produce `Settings` dataclass and populate context paths/metadata.

### Stage 01: Initialization
- Implement `InitializationStage` to build CoastSat `inputs` and derived geometry info.
- Ensure directories are created and stored in context.

### Stage 02: Imagery Download & Detection
- Create `ImageryStage` that orchestrates download → preprocess → shoreline detection.
- Store metadata/output structures in context; respect caching flags.

### Stage 03: Shoreline Analysis
- `AnalysisStage` generates plots/exports and captures `cross_distance`, `dates_sat`, `tides_sat`.

### Stage 04: Slope Estimation
- `SlopeEstimationStage` uses typed results, optional plotting, and sparse-data flags.

### Stage 05: Tide Correction
- `TideCorrectionStage` consumes slopes + tide settings, emitting corrected arrays and stats.

### Stage 06: Improved Transect Plots
- `ImprovedTransectsPlotStage` handles comparison plots, recording artifact metadata.

### Stage 07: Time-Series Post Processing
- `TimeSeriesPostProcessingStage` cleans time series and prepares preliminary trend data.

### Stage 08: Trend Calculation
- `TrendCalculationStage` computes final metrics and writes CSV/GeoJSON via helpers.

---

## 3. CLI Integration

1. Update `coastsatcli.py run` command to:
   - Build `PipelineContext` with config path and CLI overrides.
   - Instantiate the new `PipelineRunner`.
   - Offer a `--legacy` flag to fall back to `Complete_Analysis.py` while refactor is in progress.
2. Add logging hooks so CLI displays stage-level progress.
3. Document how to enable/disable optional stages via CLI flags or `settings.json`.

---

## 4. Testing Strategy

- Unit tests per stage (using fixtures for configs, transects, etc.).
- Integration test that runs the entire pipeline on a small sample site (no tide + tide variants).
- Regression comparison: run legacy script and new pipeline on the same config and compare key outputs (CSV/GeoJSON) to ensure parity.

---

## 5. Migration & Cleanup

1. Land the new runner with Stage 00–01 to validate infrastructure.
2. Incrementally add stages, ensuring the CLI can toggle between legacy/new implementations.
3. Once all stages are migrated and tests pass, deprecate `Complete_Analysis*.py` with clear documentation.
4. Update README and docs to reference the new pipeline structure and commands.

---

## 6. Tracking & Ownership

- Use GitHub issues per stage with links back to `docs/refactor/plan.md` and the stage-specific design docs.
- Tag issues/PRs with `refactor` and the relevant stage number.
- Keep `coastsat_pipeline/PLAN.md` updated with progress and any deviations from this roadmap.

This plan sets the foundation for implementing the new pipeline alongside the legacy scripts, enabling gradual rollout and easier review.
