# Pipeline Refactor Plan

This document tracks the ongoing effort to refactor the CoastSatCLI pipeline into modular, reusable stages. It aligns with ADR 002 (pipe-and-filter workflow) and prepares the codebase for a future GUI/automation layer.

The plan now lives under `docs/refactor/` so we can add more detailed stage notes/ADRs alongside it.

---

## Goals & Constraints

- **Usability**: expose progress, allow pausing/resuming at stage boundaries, and make workflows configurable without editing scripts.
- **Modularity**: encapsulate each stage (config load → downloads → shoreline detection → tide correction → reporting) with clear inputs/outputs so we can swap implementations or rerun specific steps.
- **Parity**: maintain current behavior (tide/no-tide runs) while the refactor is in progress; use feature flags to toggle the new runner until fully validated.

Constraints:
- Existing CLI commands must keep working for analysts during the migration.
- Path resolution, logging, and tide filtering logic must remain consistent to preserve provenance.

---

## Stage Breakdown & Tasks

We begin by treating each existing function in `Complete_Analysis.py` as a coarse-grained filter. This ensures we cover all responsibilities before further decomposing large stages into sub-filters.

| Stage | Current Function(s) | Refactor Tasks | Owner | Status |
| --- | --- | --- | --- | --- |
| 0. Config load | `load_settings` (Complete_Analysis) + CLI path logic | - Move to shared module (`pipeline/config.py`).<br>- Emit typed settings dataclass.<br>- Add validation/lint step. | TBD | Not started |
| 1. Initialization | `initial_settings` | - Parameterize dates/sat lists.<br>- Isolate geometry handling.<br>- Cache results for reruns. | TBD | Not started |
| 2. Imagery download / preprocess | `batch_shoreline_detection` (calls CoastSat) | - Wrap download, preprocess, classification as separate filters.<br>- Introduce artifact caching metadata.<br>- Add logging hooks per substage. | TBD | Not started |
| 3. Shoreline analysis outputs | `shoreline_analysis` | - Split plotting/export logic from data prep.<br>- Provide headless mode (skip heavy plots). | TBD | Not started |
| 4. Tide correction | `tidal_correction` | - Convert to optional stage controlled by config.<br>- Persist intermediate tide stats for reuse.<br>- Support alternative tide sources (FES vs CSV) via strategy. | TBD | Not started |
| 5. Visualization enhancements | `improved_transects_plot` | - Expose as standalone plotting module.<br>- Allow analysts to rerun plots without entire pipeline. | TBD | Not started |
| 6. Post-processing | `time_series_post_processing` | - Separate smoothing/interpolation/export steps.<br>- Add hooks for QA checks. | TBD | Not started |
| 7. Slope estimation | `slope_estimation` | - Make slope computation lazy/config-driven.<br>- Cache results per transect. | TBD | Not started |
| 8. Trend calculation | `calculate_and_save_trends` | - Define consistent output schema.<br>- Add validation of CSV/GeoJSON attributes. | TBD | Not started |
| 9. Runner / orchestration | `main` in scripts | - Build pipeline runner (`pipeline/run.py`).<br>- Enable config flags to skip stages, choose tide mode.<br>- Integrate with CLI commands. | TBD | Not started |

Update the table as tasks progress (add links to PRs/issues).

---

## Workstreams & Deliverables

1. **ADR & Design**
   - Draft ADR for the pipeline runner interface (stage registry, context object, error handling). Decision: adopt Option B (stage classes) implemented with Python standard library abstractions (no external framework).
   - Document module layout proposal (`pipeline/` package).
2. **Shared Utilities**
   - Create `pipeline/context.py` for shared state (paths, logs).
   - Move duplicated logic (path resolution, tide filter validation) out of scripts.
3. **Stage Adapters**
   - Build wrappers that call existing functions but conform to the new interface.
   - Add feature flag in CLI to opt into the new runner for selected sites.
4. **Testing Expansion**
   - Add fixtures for sample configs and outputs.
   - Introduce integration tests exercising the new runner end-to-end.
5. **CLI Integration**
   - Replace script invocation with pipeline runner once stages stabilize.
   - Ensure `site-rerun` and future GUI components reuse the same API.
6. **Cleanup**
   - Deprecate `Complete_Analysis*.py` once parity confirmed.
   - Update docs and ADRs to reflect the final architecture.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Partial refactor breaks existing runs | Analysts blocked | Keep legacy scripts as default until new runner passes integration tests; offer opt-in flag. |
| Configuration drift | Inconsistent behavior | Centralize config parsing and validation; add schema checks. |
| Test coverage gaps | Regressions go unnoticed | Follow the testing plan; require unit + integration tests for each stage before merging. |
| Timeline creep | Endless refactor | Track progress via this document and issue tracker; timebox each stage. |

---

## Tracking & Links

- Issues/PRs: tag with `refactor`, `pipeline`, and reference this document.
- ADRs: `ADR-002` (pipe-and-filter), upcoming ADR for pipeline runner.
- Related docs: `docs/architecture/complete-analysis.md`, `docs/dev/testing.md`, `docs/dev/releases.md`.

Update this plan after each milestone or when priorities shift. Treat it as a living document for the refactor roadmap.
