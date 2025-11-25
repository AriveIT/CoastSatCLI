# CoastSatCLI Documentation Hub

Use this guide to navigate the `docs/` tree, understand the intent of each section, and contribute new material consistently. The root `ReadMe.md` stays focused on onboarding, so anything deeper than quick-start content belongs here.

---

## Folder Map

| Folder | Purpose | Key Files |
| --- | --- | --- |
| `adrs/` | Architecture Decision Records; capture context, decisions, and consequences for major changes. | `ADR-000-template.md`, `ADR-001-cli-stack.md`, `ADR-002-pipe-and-filter.md`, `ADR-003-docs-structure.md` |
| `architecture/` | System overviews, data flows, component catalogs, and deep dives into pipeline stages. | `system-overview.md`, `data-flow.md`, `components.md`, `complete-analysis.md` |
| `ops/` | Operational procedures for environment provisioning, runbooks, monitoring, and incident response. | `environment.md`, `runbook.md` |
| `user/` | Analyst-facing guides: CLI usage, configuration reference, troubleshooting, glossary. | `cli-guide.md`, `configuration.md`, `troubleshooting.md`, `glossary.md` |
| `dev/` | Contributor guidance for coding standards, testing, and release/versioning. | `contributing.md`, `testing.md`, `releases.md` |

Add new folders if a topic does not fit cleanly into the existing hierarchy, but consider starting with the structure above so contributors know where to look.

---

## How to Contribute Documentation

1. **Pick the right home**: reference the table above before creating new files. Architecture decisions go in `adrs/`, operational runbooks in `ops/`, etc.
2. **Follow naming conventions**:
   - ADRs use incremental numbering (`ADR-00X-topic.md`).
   - Other docs use lowercase-kebab or descriptive filenames ending in `.md`.
3. **Link wisely**:
   - Use relative paths (e.g., `[CLI Guide](user/cli-guide.md)`).
   - When updating the root README, link to the relevant doc instead of duplicating content.
4. **Keep sections scoped**: aim for focused documents rather than sprawling pages. If a doc exceeds ~200 lines, consider splitting it.
5. **Update cross-references**: whenever you add or rename a doc, update this README and any referencing files (root README, ADRs, CLI help text).

---

## Style & Tooling

- **Markdown**: stick to basic Markdown for portability. Add fenced code blocks with language hints (` ```bash `, ` ```json `) where appropriate.
- **Diagrams**: reference image files or Mermaid snippets stored under `docs/assets/` (create the folder if needed). Keep source files in Git when possible.
- **Terminology**: align with the glossary (`user/glossary.md`). If you introduce new jargon, add it there.
- **Testing references**: link to the testing plan (`dev/testing.md`) when describing verification steps.
- **Reviews**: treat doc PRs like code—request reviewers familiar with the subject area and ensure ADRs are added when documentation reflects a decision.

---

## Open Documentation Tasks

- [ ] Flesh out architecture diagrams once the modular pipeline refactor lands.
- [ ] Add a `docs/examples/` folder with sanitized `settings.json` and sample outputs to accompany the user guides.
- [ ] Capture ops automation scripts (cron/batch examples) in `ops/runbook.md` or a dedicated file.
- [ ] Publish documentation guidelines (linting, spellcheck) if we adopt a static site generator (MkDocs/Sphinx).

Track documentation issues in GitHub using the `docs` label so we can prioritize updates alongside code work.
