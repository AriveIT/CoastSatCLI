# ADR 004: Pipeline Runner Architecture

- **Status:** Accepted
- **Date:** 2025-11-24
- **Context:**
  - `Complete_Analysis.py` and `Complete_Analysis_No_Tide.py` are large scripts that bundle configuration, imagery downloads, shoreline detection, tide correction, plotting, and exports.
  - We are refactoring the workflow into a pipe-and-filter architecture (ADR-002) to improve usability, modularity, and testability.
  - Future user interfaces (CLI/GUI) need a consistent API to run the pipeline, report progress, and optionally skip stages.
- **Decision:**
  - Implement a new pipeline runner composed of stage classes (Option B from `docs/refactor/runner-options.md`):
    - Define a `PipelineStage` interface (Python `abc`/`typing.Protocol`) with `should_run(context)` and `run(context)` methods plus metadata (name, description, dependencies).
    - Use a `PipelineContext` dataclass to hold configuration, paths, and intermediate artifacts shared between stages.
    - Provide a `PipelineRunner` that iterates through a registry of stage instances, logging progress and honoring config-driven toggles (e.g., tide correction enabled/disabled).
    - Build everything with Python standard-library abstractions (no external frameworks required).
- **Consequences:**
  - Pros:
    - Clear boundaries for each stage, enabling independent testing, retries, and resuming.
    - Runner can expose hooks/callbacks for progress reporting, making it easy to integrate with future GUIs.
    - Incremental migration: wrap existing functions as stage implementations before rewriting internals.
  - Cons:
    - Requires additional scaffolding (context class, stage registry) before feature work can continue.
    - Slightly more boilerplate than a pure functional pipeline, though it enables richer metadata/control.
- **Migration Plan:**
  1. Create `pipeline/` package with context, stage base class/protocol, and runner.
  2. Wrap existing functions (`load_settings`, `initial_settings`, etc.) as stage classes.
  3. Add feature flag in CLI to opt into the new runner, keeping legacy scripts as default until parity is verified.
  4. Expand tests to cover the runner and each stage before flipping the default behavior.
- **Related Documents:**
  - ADR-002 (pipe-and-filter workflow)
  - `docs/refactor/plan.md`
  - `docs/refactor/runner-options.md`
