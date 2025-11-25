# Contribution Guide

This guide replaces the lightweight section in the README and describes how to propose changes, request reviews, and keep documentation/tests in sync.

---

## 1. Branching & Workflow

1. Fork or create a feature branch off `main`.
2. Keep branches focused on a single feature/fix (e.g., `feature/pipe-filter-runner`).
3. Rebase frequently to avoid large merge conflicts, especially while the pipeline refactor is underway.
4. Open a pull request against `main` when ready for review.

We do not enforce a release branch today; once we introduce tagged releases, hotfix branches will target the latest tag.

---

## 2. Coding Standards

- **Language:** Python 3.11. Use type hints where practical; prefer explicit `typing` imports over `Any`.
- **Formatting:** Follow `black`-style conventions (4-space indents, double quotes). Run `ruff`/`flake8` if available.
- **Imports:** Group standard library, third-party, and local modules separately.
- **Docstrings:** Use short descriptive docstrings (Google or NumPy style). Reference CLI commands or docs where relevant.
- **Logging:** Prefer `typer.echo` for CLI output and `logging` for script internals to keep verbosity configurable.
- **Configuration:** Do not hardcode paths; read from `settings.json` or CLI arguments.

---

## 3. Pull Request Checklist

Before requesting review:

- [ ] Tests pass (`pytest cli` or targeted modules) or manual validation documented.
- [ ] Docs updated if the behavior or command parameters changed (README and `docs/` as appropriate).
- [ ] Added ADR if the change represents a significant architectural decision.
- [ ] Screenshots or sample output included when UI/plot changes are involved.
- [ ] `git status` shows only relevant files; new docs/tests committed together with code.

Include a short summary in the PR template:
```
## Summary
- ...
- ...

## Testing
- [ ] pytest cli
- [ ] Manual run: python cli/coastsatcli.py run --config ...
```

---

## 4. Review Expectations

- At least one reviewer familiar with the CLI and one with CoastSat internals should sign off on complex pipeline changes.
- Reviewers verify:
  - Code clarity and adherence to standards.
  - Adequate test coverage or manual validation steps.
  - Docs and ADRs updated where necessary.
- Approvals require all CI checks to pass. If CI is unavailable, attach logs from local runs.

---

## 5. Communication & Issue Triage

- Use GitHub issues for bugs and feature requests; apply labels (`bug`, `enhancement`, `docs`, `pipeline`) to aid triage.
- For urgent production issues (e.g., blocking analysis runs), notify the coastal-change Slack/Teams channel after filing an issue.
- ADRs should be referenced in issues/PRs when they influence the decision.

---

## 6. Related Documents

- Testing strategy: [`docs/dev/testing.md`](testing.md)
- Release/versioning plan: [`docs/dev/releases.md`](releases.md)
- Architecture decisions: [`docs/adrs/`](../adrs)
