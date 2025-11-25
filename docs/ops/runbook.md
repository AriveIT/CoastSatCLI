# Operations Runbook

This runbook supports analysts and operators who schedule CoastSatCLI runs, monitor health, and respond to incidents.

---

## 1. Recurring Tasks

| Task | Frequency | Owner | Notes |
| --- | --- | --- | --- |
| Verify environment (`conda env export`, `python cli/coastsatcli.py --help`) | Monthly or after OS updates | Local analyst | Ensures dependencies remain in sync with `environment.yml`. |
| Check GEE quota (`earthengine quotas`) | Weekly during campaigns | Ops lead | Watch for approaching daily request limits; stagger runs if needed. |
| Disk usage audit (`Get-ChildItem -Recurse | Measure-Object Length -Sum`) | Weekly | Ops lead | Ensure imagery cache and outputs have enough space; archive old sites. |
| Backup outputs to data lake | Weekly | Data steward | Copy `<sitename>/outputs/` + `settings.json`; verify checksums. |
| Review open issues labeled `ops` or `bug` | Weekly | PM / Tech lead | Prioritize fixes before large batch runs. |

---

## 2. Pre-Run Checklist

1. **Environment active** (`conda activate coastsat`).
2. **Credentials valid** (`gcloud auth list`, `earthengine authenticate`).
3. **Disk space** — at least 50 GB free per AOI being processed concurrently.
4. **Network status** — confirm access to GEE and shared storage.
5. **Config validation** — run `python cli/coastsatcli.py show --config ...` to ensure paths resolve before long runs.

For batch execution, maintain a spreadsheet or YAML manifest listing each AOI, status, and last successful run date.

---

## 3. Health Checks During Runs

- Monitor console logs for each stage (download, preprocess, shoreline, tide correction). Prolonged silence (>30 min) may indicate a stalled process.
- For automated scripts, redirect stdout/stderr to log files and tail them periodically.
- Watch OS resource monitors:
  - CPU pegged at 100% for hours is expected during preprocessing.
  - RAM usage approaching physical limits may require reducing concurrent runs.

---

## 4. Common Incident Playbooks

### 4.1 Earth Engine Authentication Failure
1. Stop the current run.
2. Re-authenticate: `gcloud auth application-default login` and `earthengine authenticate`.
3. Re-run the command; imagery downloads will resume where they left off (cached metadata).
4. If the issue persists, check the Google status page and escalate to the ops lead.

### 4.2 Disk Full During Run
1. Cancel the current process (Ctrl+C) to avoid corrupt outputs.
2. Delete or archive unused imagery caches (`temp/` folders) to free space.
3. Resume by re-running `coastsatcli.py run --config ...`; the pipeline will regenerate missing outputs.
4. Report the incident so storage planning can be updated.

### 4.3 Tide Model File Missing
1. Confirm the path in `settings.json` points to an accessible drive.
2. If the shared drive is offline, notify IT and pause related runs.
3. Re-link `fes2022.yaml` via `site-rerun` once the drive is restored.

### 4.4 Unexpected Output (QA Failure)
1. Log the issue in GitHub with screenshots/plots.
2. Re-run with `--verbose` logging to capture additional context.
3. If reproducible, tag the issue `bug` and assign to the pipeline maintainer.

---

## 5. Escalation & Communication

- **Primary contacts:** Tech lead (pipeline), Ops lead (infrastructure), Data steward (archives). Document names/emails internally.
- **Channel:** Coastal-change Teams/Slack channel for urgent incidents; GitHub issues for tracking.
- **Escalation path:** Analyst → Ops lead → Tech lead → Program manager (if blocking deliverables).

---

## 6. Post-Run Tasks

- Update the AOI tracker with completion status, date, and notable observations.
- Archive outputs per the environment guide.
- File issues for any manual workarounds used during the run so we can improve automation.

Keep this runbook updated as we automate more steps or introduce central orchestration.
