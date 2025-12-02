# Stage 01 — Initialization & Input Preparation

This stage builds on the validated configuration to assemble the CoastSat `inputs` and `settings` structures expected by downstream modules. It roughly corresponds to the current `initial_settings` function in `Complete_Analysis.py`.

---

## Current Behavior

- `initial_settings(config)` performs the following:
  - Reads the AOI polygon via `SDS_tools.polygon_from_kml` and reduces it to the “smallest rectangle”.
  - Hard-codes date range (`1984-01-01` → `2025-01-01`) and satellite list (`['L5','L7','L8','L9']`).
  - Sets the sitename and working directories (`filepath`, `output_dir`).
  - Creates the `inputs` dictionary consumed by CoastSat download routines.
  - Initializes the `settings` dict (plotting options, filter flags) using defaults baked into the script.
  - Leaves TODOs for selecting satellites and date range from config/CLI.

Pain points:
- Dates/satellite lists are not configurable per site.
- Geometry transformations are implicit; errors surface later in the pipeline.
- Outputs are simple dictionaries, making validation and testing harder.

---

## Target Design

- **Inputs:** `PipelineContext` populated by Stage 00, including resolved paths to AOI/reference/transects and environment data.
- **Outputs:** Updated `PipelineContext` with:
  - `inputs_config`: dataclass capturing polygon, dates, satellites, filepaths.
  - `analysis_settings`: dataclass for CoastSat/plotting options.
  - Pre-computed geometry metadata (bounding boxes, EPSG).

### Planned Implementation Steps
1. **Dataclasses**
   - Define `InputsConfig` with fields:
     - `polygon`: geometry (likely shapely/pydantic type).
     - `dates`: tuple/list of ISO strings.
     - `sat_list`: list of satellite codes.
     - `sitename`, `filepath`, `shoreline_path`, etc.
   - Define `AnalysisSettings` capturing flags currently hard-coded.
2. **Geometry handling**
   - Load AOI polygon using `geo_utils` helpers; add validation (non-empty, CRS known).
   - Compute bounding boxes or simplified polygons once to avoid repeated work downstream.
   - Store derived metadata in context (`context.geometry_info`).
3. **Configurable defaults**
   - Every parameter currently set inside `initial_settings` (dates, satellite list, transect spacing/length, imagery extent rules, etc.) should be surfaced as configuration knobs:
     - First-class fields in `settings.json`.
     - CLI/UI overrides that feed into Stage 00 and propagate here.
     - Sensible defaults when values are omitted, but no hard-coded constants buried in the stage.
4. **Directory setup**
   - Confirm output directories exist (create as needed) but avoid heavy filesystem writes later.
   - Precompute paths for intermediate artifacts (temp/cache/logs).
5. **Validation / telemetry**
   - If AOI conversion fails, raise a descriptive exception early.
   - Record chosen satellites/date range in logs/context for traceability.

### Example Interface
```python
class InitializationStage(PipelineStage):
    name = "init"
    description = "Build CoastSat inputs/settings structures."

    def run(self, context: PipelineContext) -> None:
        context.inputs_config = build_inputs(context.settings, context.paths)
        context.analysis_settings = build_analysis_settings(context.settings)
        context.geometry_info = derive_geometry(context.inputs_config)
```

---

## Migration Tasks

- [ ] Create dataclasses for inputs/settings and add unit tests around their constructors/defaults.
- [ ] Move AOI loading and CRS detection logic from `initial_settings` into shared utility functions (likely `pipeline/geo.py`).
- [ ] Add configuration hooks for date range and satellite list (initially optional).
- [ ] Ensure Stage 01 writes any derived fields back into the context for use by download/preprocess stages.
- [ ] Update the runner to call Stage 01 after Stage 00 and verify the existing scripts can consume the new dataclasses (via adapters during transition).
- [ ] Extract the current `initial_settings` logic into `coastsat_pipeline/helpers/initialization.py` (or sub-helpers) so Stage 01 no longer imports from `Complete_Analysis`.

---

## Open Questions / TODOs

- Should we support multiple AOIs per site at this stage, or keep the single-AOI assumption?
- Do we persist the derived geometry info for debugging (e.g., save to `inputs/cache/geometry.json`)?
- How will we handle user-provided transect parameters (spacing, length) once they are exposed via config/UI? (Need validation and fallbacks.)
- Any additional metadata needed for batch scheduling (priority, analyst name) that belongs here?
