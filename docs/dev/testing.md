# Testing Strategy

We are currently refactoring the pipeline into modular filters, so the testing plan focuses on what we can cover today and what we expect post-refactor. Use this document as the source of truth for required checks before merging.

---

## 1. Current Test Suite

- **Unit tests (`cli/tests/`):**
  - `test_linemerge.py`: validates transect merge helpers.
  - `test_clip_reference.py`: ensures shoreline clipping handles edge cases.
  - `test_tide_config_dialog.py`: checks dialog logic for tide settings.
- **Manual smoke tests:**
  - Run `coastsatcli.py init` + `run` on a known AOI (e.g., `tests/notide` config) and confirm outputs are generated.
  - Execute `site-rerun` to ensure transect regeneration works without data loss.
- **Notebook validation:**
  - `classification/train_new_classifier.ipynb` should execute start-to-finish when classifier updates are made.

Document manual steps in PR descriptions until we automate them.

---

## 2. Future Test Plan (Post-Refactor)

| Layer | Goal | Planned Approach |
| --- | --- | --- |
| Unit | Validate pure functions (geo utilities, file helpers, tide calculations). | Expand pytest coverage, add fixtures for sample GeoJSON/CSV files. |
| Integration | Verify CLI commands orchestrate filters correctly. | Use temporary directories and sample `settings.json` to run `init`, `run`, `site-rerun` end to end. |
| Data QA | Ensure sample AOIs produce expected plots and CSV stats. | Maintain golden outputs under `tests/data/` and compare key metrics. |
| Performance | Catch regressions in runtime for typical AOIs. | Add optional benchmarks (e.g., `pytest --benchmark`) once the pipeline is modular. |
| Classifier | Confirm training notebooks and inference scripts stay in sync. | Provide a small labeled dataset for CI (with downsampled imagery) to run a sanity-training pass. |

---

## 3. Tooling & Setup

- **Test runner:** `pytest`
- **Mock data:** store under `tests/data/` (GeoJSON, TIFF snippets, CSVs). Keep files lightweight and licensed for redistribution.
- **Linters/formatters:** adopt `ruff`/`black` once the refactor settles; document commands in this section when enforced.
- **CI (future):** GitHub Actions workflow to run unit/integration tests plus linting on every PR.

---

## 4. Required Checks per PR (Current State)

| Check | Required? | Notes |
| --- | --- | --- |
| `pytest cli` | ✅ | Run locally; attach output to PR if CI unavailable. |
| Manual CLI run (`init` + `run`) on small site | ✅ for pipeline changes | Mention which config you used (e.g., `tests/notide/settings.json`). |
| Docs updated | ✅ when behavior changes | README and relevant `docs/` sections. |
| ADR added/updated | ✅ if architectural change | Reference ADR number in PR description. |

---

## 5. Reporting & Tracking Failures

- Log issues in GitHub with steps to reproduce, OS/environment info, and relevant config snippets.
- Tag with `testing` when the failure indicates missing coverage or flaky behavior.
- Update this document when new categories of tests are added or when requirements change (e.g., after pipeline modularization).
