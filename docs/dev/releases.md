# Release & Versioning Plan

We do not yet publish packages or tagged releases, but to prepare for broader distribution we define the conventions below. Adopt them once the pipeline refactor stabilizes.

---

## 1. Versioning Scheme

- Use **Semantic Versioning (MAJOR.MINOR.PATCH)**.
  - Increment **MAJOR** when making incompatible CLI/setting changes.
  - Increment **MINOR** for new features or workflow stages.
  - Increment **PATCH** for bug fixes or documentation updates.
- Pre-release tags (`-alpha`, `-beta`, `-rc`) can be used while large refactors are under review.

---

## 2. Release Process (Future State)

1. Create a release branch from `main` (e.g., `release/v1.2.0`).
2. Update `ReadMe.md`, `docs/`, and `CHANGELOG.md` with the release highlights.
3. Bump version identifiers in code (to be introduced once we package the CLI).
4. Run the full test/QA checklist, including manual runs on representative AOIs.
5. Tag the release (`git tag v1.2.0`) and push tag + branch.
6. Draft a GitHub Release with:
   - Summary of changes (features, bug fixes, breaking changes).
   - Links to ADRs and docs updated for the release.
   - Known issues or upcoming work.
7. After verification, merge the release branch back into `main`.

---

## 3. Distribution Options

| Option | Notes |
| --- | --- |
| GitHub Releases (source zip) | Baseline approach; sufficient until we package the CLI. |
| Internal installer/zip | Bundle scripts plus dependencies for offline analysts; requires coordination with ops. |
| PyPI package | Long-term goal once the CLI is modular and tests are automated. Needs dependency pinning and entry points. |

Document the chosen distribution method in a future ADR once we commit to one.

---

## 4. Post-Release Verification

- Re-run `coastsatcli.py init` + `run` on at least two sample sites (with/without tide) using the release tag.
- Confirm documentation links in the README and `docs/` reference the correct version/tag.
- Monitor issue tracker and ops channels for 1–2 weeks for regression reports.

---

## 5. Rollback Procedure

- If a release causes critical regressions:
  1. Announce the issue in the coastal-change channel and create a GitHub issue marked `priority`.
  2. Revert the release merge commit or tag a hotfix release (e.g., `v1.2.1`) that restores the previous behavior.
  3. Update the release notes with rollback details and mitigation steps for analysts.

---

## 6. Related Work

- Testing requirements: [`docs/dev/testing.md`](testing.md)
- ADRs influencing release decisions: [`docs/adrs/`](../adrs)
- Ops documentation for deployment/archiving: [`docs/ops/`](../ops)
