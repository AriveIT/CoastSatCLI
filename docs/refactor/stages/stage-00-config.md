# Stage 00 — Configuration Load

Use this skeleton to capture the current behavior and target design for the configuration-loading filter.

## Current Behavior

- Function(s): `load_settings` in `Complete_Analysis.py` plus CLI path normalization.
- Responsibilities:
  - Resolve relative paths in `settings.json`.
  - Validate tide filter parameters.
  - Expand `fes_config` to absolute paths.
  - Ensure `output_dir` and required keys exist.

## Target Design

- Inputs: raw `settings.json` path from CLI/UI.
- Outputs: `PipelineContext` with typed settings object, validated paths, and derived metadata.
- Steps:
  1. Load JSON and apply schema validation (consider `pydantic` later if needed).
  2. Normalize/resolve paths relative to site directory.
  3. Validate tide filter ranges and tide mode (FES vs CSV).
  4. Store normalized data in context for downstream stages.

## Open Questions / TODOs

- Should date ranges/satellite lists move into `settings.json` at this stage?
- How to handle missing optional files (e.g., shoreline path) gracefully?
- Decide whether to write back normalized settings to disk or keep in-memory only.
