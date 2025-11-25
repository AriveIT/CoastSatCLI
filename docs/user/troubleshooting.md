# Troubleshooting Guide

Use this guide to diagnose common issues encountered while running CoastSatCLI. If a problem persists after trying the suggestions below, capture the logs and escalate through the project’s support channel.

---

## 1. Installation & Dependency Errors

### 1.1 Mamba/Conda Environment Fails to Resolve Packages
- **Symptom:** `PackagesNotFoundError` or dependency conflicts.
- **Fix:** Clean caches and retry with explicit versions.
  ```bash
  conda clean --all
  conda update conda
  conda install python=3.11 geopandas gdal rasterio
  ```
- Ensure the `conda-forge` channel is first in your configuration (Miniforge handles this automatically).

### 1.2 GDAL / PROJ DLL Errors
- **Symptom:** `ImportError: DLL load failed` when importing `gdal` or `fiona`.
- **Fix:** Activate the environment before launching IDEs (`conda activate coastsat`) and avoid mixing Conda-installed GDAL with system-level installations. Reinstall GDAL inside the environment if needed.

### 1.3 `pyfes` Not Found
- **Symptom:** `ModuleNotFoundError: pyfes`.
- **Fix:** Install via Conda (`conda install pyfes -y`) and confirm the `fes2022` data files are downloaded; see the README for dataset links.

---

## 2. Earth Engine & Google Cloud Authentication

### 2.1 `EEException: Please authorize access`
- Run:
  ```bash
  gcloud auth application-default login
  earthengine authenticate
  ```
- Verify your project name in `settings.json` matches the one returned by `gcloud config get-value project`.

### 2.2 Frequent Re-Authentication Prompts
- Update components and reissue default credentials:
  ```bash
  gcloud components update
  gcloud auth application-default login
  ```
- Ensure you are not running the CLI from an elevated PowerShell session with different credentials.

---

## 3. Tide Model Configuration Issues

| Error | Likely Cause | Resolution |
| --- | --- | --- |
| `FileNotFoundError: fes2022.yaml` | `settings.json` points to a relative path or missing file. | Use absolute paths for `fes_config` and confirm network drives are mounted. |
| `pyfes: missing constituent files` | Dataset download incomplete. | Re-run the FES2022 installer/extractor and update the YAML to point to the correct directory. |
| `ValueError: tide_filter percentiles ...` | Percentiles not within `(0,100)` or lower >= upper. | Edit via `site-rerun` to set valid values (e.g., 5 and 95). |

For CSV-based tides, verify the file contains timestamps and water levels in the expected columns; malformed CSVs will surface as Pandas parsing errors.

---

## 4. Geometry & Transect Problems

### 4.1 `ValueError: AOI has invalid geometry`
- Validate the AOI in GIS software (look for self-intersections).
- Use `geo_utils.detect_or_prompt_epsg` via the CLI to ensure CRS metadata is present.
- Simplify polygons if they exceed 100 sq km; GEE retrieval may fail otherwise.

### 4.2 Transects Missing or Overlapping
- Check the spacing/length parameters entered during `init`. Extremely small spacing can create overlapping transects.
- Re-run `site-rerun` and regenerate transects with updated parameters. This preserves other inputs while fixing transects.

### 4.3 Reference Shoreline Empty
- Ensure the shoreline dataset actually overlaps the AOI; the CLI clips shoreline geometries to the AOI extent.
- If the shoreline CRS differs from the AOI, make sure `load_aoi_and_shoreline` successfully reprojected; otherwise convert both layers to a common CRS before running `init`.

---

## 5. Performance & Resource Limits

| Symptom | Mitigation |
| --- | --- |
| `MemoryError` during preprocessing | Close other applications, increase swap/virtual memory, or process smaller AOIs (split long coastlines into segments). |
| Slow downloads | Verify network connectivity to Earth Engine; consider running overnight or batching AOIs to reuse cached imagery. |
| Long plotting stage | Use future config flags (planned) to skip heavy plots when running in headless batch mode, or delete existing plots to reduce re-rendering. |

---

## 6. Where to Get Help

- Check recent ADRs (`docs/adrs/`) for pending changes that might affect your run.
- Review `docs/ops/runbook.md` for escalation steps (to be filled out).
- When filing an issue, include:
  - OS + Python version (`python --version`).
  - Command executed and full stack trace.
  - Snippet of `settings.json` (redact sensitive paths).
  - Any relevant log files under `<sitename>/outputs/`.
