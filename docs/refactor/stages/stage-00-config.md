# Stage 00 — Configuration Load

Stage 00 converts a raw `settings.json` path (plus any CLI overrides) into a validated, strongly typed `PipelineContext`. It is the first “filter” in the new pipeline and replaces the current `load_settings` function plus scattered CLI path munging.

---

## Current Behavior

- **Functions:** `load_settings` inside `Complete_Analysis.py` and helpers inside `CLI/file_utils.py`.
- **Responsibilities today:**
  - Read `settings.json` relative to the site directory.
  - Resolve relative paths for AOI, reference shoreline, transects, and output directories.
  - Expand `fes_config` and other tide references to absolute paths.
  - Normalize tide filter data (`lower_percentile`, `upper_percentile`).
  - Provide rudimentary validation (ensuring `output_epsg` exists).

Because this logic is embedded in the monolithic script and partially duplicated in the CLI, we have inconsistent behavior when analysts edit configs manually.

---

## Target Design

- **Inputs:** Path to `settings.json` (absolute or relative) plus optional overrides from the CLI/GUI (e.g., `--override-output-dir` in future).
- **Outputs:** `PipelineContext` populated with:
  - Parsed `Settings` dataclass (schema).
  - Absolute paths for all referenced files.
  - Derived metadata (site directory, cache/temp directories, timestamp for run).
  - Flags describing tide mode (FES vs CSV vs none) and whether tide filters are enabled.

### Planned Implementation Steps
1. **Schema definition**
   - Introduce a `Settings` dataclass or lightweight schema (manual validation now, optional `pydantic` later).
   - Required fields: `inputs.sitename`, `inputs.aoi_path`, `inputs.reference_shoreline`, `inputs.transects`, `output_dir`, `output_epsg`.
   - Optional fields: `inputs.shoreline_path`, `inputs.fes_config`, `inputs.tide_csv_path`, `inputs.reference_elevation`, `inputs.beach_slope`, `tide_filter`.
2. **Path resolution**
   - Determine `site_dir` (parent folder of `settings.json`).
   - For every relative path, convert to absolute using `site_dir`.
   - Record both the absolute and relative forms in the context so downstream exports can rebuild relative references if needed.
3. **Validation**
   - Ensure required paths exist (AOI, reference shoreline, transects, tide configs) unless explicitly optional.
   - Confirm tide filter bounds satisfy `0 <= lower < upper <= 100`.
   - Detect mutually exclusive tide modes (cannot supply both `fes_config` and `tide_csv_path`).
4. **Context population**
   - Create a `PipelineContext` instance storing:
     - `settings`: normalized dataclass.
     - `paths`: dictionary with resolved directories (inputs, outputs, temp, logs).
     - `run_metadata`: start time, CLI options, feature flags.
   - Provide helper methods on the context for downstream stages (e.g., `context.require_fes_config()`).

### Interfaces
```python
@dataclass
class Settings:
    inputs: InputsConfig
    output_dir: Path
    output_epsg: int
    tide_filter: Optional[TideFilter]
    # future fields: date range, sat list, feature flags

class ConfigLoadStage(PipelineStage):
    name = "config"
    description = "Load and validate settings.json"

    def run(self, context: PipelineContext) -> None:
        context.settings = parse_and_validate(context.entry_config_path)
        context.paths = build_path_registry(context.settings)
```

---

## Migration Tasks

- [ ] Extract existing `load_settings` logic into a shared module and cover with unit tests.
- [ ] Define `Settings` and `PipelineContext` dataclasses under `pipeline/`.
- [ ] Implement `ConfigLoadStage` that populates the context and replaces direct script usage.
- [ ] Update CLI (`coastsatcli.py run`) to instantiate the context with the config path and hand it to the runner.
- [ ] Ensure `site-rerun` command reuses the same stage so both CLI and runner normalize configs identically.

---

## Open Questions / TODOs

- **Expose date ranges / satellite lists?** We do want these adjustable via config, but it may be easier to evolve once a UI exists. The stage should be written so new fields are easy to plumb through the schema/context later.
- **Persist normalized settings?** Lean toward writing an optional `settings.resolved.json` (behind a flag) to aid debugging, while still keeping everything in memory for the runner.
- **Error handling strategy:** Raise structured exceptions for fatal validation failures; the CLI/GUI can catch and present user-friendly messages. Non-blocking warnings (e.g., optional path missing) can be added to `context.notifications`.
- **Future overrides (env vars / CLI flags):** Placeholder for later. Decide whether to support environment-variable substitution or CLI-based overrides once the new interface work begins.

Document answers here as decisions are made so future contributors know how the configuration filter behaves.
- **Helper extraction checklist**
  1. Copy the current `load_settings` function from `Complete_Analysis.py` into `coastsat_pipeline/helpers/config.py`.
  2. Convert the helper to build and return the `Settings` dataclass (and nested `InputsConfig`, `TideConfig`) directly so the stage can simply assign `context.settings`.
  3. Update imports inside the helper to rely on standard library (`json`, `pathlib`) and shared utilities (no references back to `Complete_Analysis`).
  4. Ensure path resolution logic mirrors the original function; add unit tests in `tests/test_config_helper.py`.
  5. Modify `ConfigLoadStage` to call the helper returning `Settings`, removing duplicate dataclass construction in the stage.
