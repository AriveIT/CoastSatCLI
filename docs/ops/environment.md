# Environment & Deployment Notes

This guide standardizes how to provision CoastSatCLI environments for analysts and automation hosts. Pair it with the runbook for operational tasks.

---

## 1. Conda/Mamba Environment

### 1.1 Create the Environment
We now maintain a canonical `environment.yml` at the repo root.

```bash
conda env create -f environment.yml
conda activate coastsat
```

If you prefer `mamba` you can swap in `mamba env create`/`mamba activate`. For existing environments, run `conda env update -f environment.yml` (or `mamba env update`) to align with the latest dependencies.

### 1.2 Included Packages
- Geospatial stack: `geopandas`, `gdal`, `rasterio`, `shapely`, `fiona`, `rtree`, `pyproj`
- Analysis/science: `numpy`, `pandas`, `scipy`, `scikit-image`, `scikit-learn`, `matplotlib`, `astropy`, `tqdm`, `joblib`
- CLI/runtime: `typer`, `pyyaml`, `requests`, `imageio`, `imageio-ffmpeg`, `pyqt`, `pytest`
- Remote services: `earthengine-api`, `google-auth`, `pyfes`, `gdown`
- Dev tooling: `notebook`, `typer-cli`

Keep the environment isolated per user/machine to avoid DLL conflicts common with GDAL.

### 1.3 Updates
- When the `environment.yml` changes, run `conda env update -f environment.yml` (or `mamba env update`).
- For minor package bumps, prefer updating the YAML first to keep reproducibility.

---

## 2. External Credentials

| Service | Purpose | Setup |
| --- | --- | --- |
| Google Earth Engine | Imagery download (Landsat/Sentinel) | `gcloud auth application-default login` + `earthengine authenticate`; store project name in config/notebooks. |
| Google Cloud SDK | Required for GEE auth refresh | Install from <https://cloud.google.com/sdk/docs/install>; keep components updated (`gcloud components update`). |
| FES2022 tide model | Tide corrections | Download dataset to a shared drive, update `fes2022.yaml`, and reference absolute paths in `settings.json`. |
| Internal storage (NAS/SharePoint) | Archive outputs and imagery caches | Request access via NRCan IT; ensure path mappings are consistent across sessions. |

Document credential ownership in the ops runbook (who can refresh keys, revoke tokens, etc.).

---

## 3. Hardware & Storage Requirements

| Tier | CPU/GPU | RAM | Disk | Notes |
| --- | --- | --- | --- | --- |
| Analyst workstation | 4+ cores, optional mid-range GPU for notebooks | 16 GB minimum | 200 GB free (per batch of AOIs) | Recommended for day-to-day AOI processing. |
| Batch/automation host | 8+ cores, SSD storage | 32 GB | 1 TB+ | Supports overnight runs and multiple AOIs concurrently. |

Storage layout for each site:
```
<base>/<sitename>/
├─ inputs/      # ~10–100 MB (GeoJSON, KML)
├─ outputs/     # 100 MB–2 GB depending on plots/time series
└─ cache/temp   # imagery downloads; can exceed 20 GB per AOI
```

> **Tip:** Keep the imagery cache on a fast local disk and archive only the outputs to shared storage.

---

## 4. Backup & Retention

- **Inputs:** Versioned in GitHub or stored in a managed geospatial repository. Keep raw shoreline datasets outside project folders to avoid duplication.
- **Outputs:** Copy final `outputs/` contents to the program’s data lake weekly. Include `settings.json` and tide filter stats for provenance.
- **Imagery cache:** Consider disposable; delete when disk pressure arises after confirming outputs are archived.
- **Logs:** Preserve CLI logs and key plots for at least one audit cycle (suggested: 12 months) to support QA reviews.

---

## 5. Cloud / Remote Execution (Future)

For future cloud runners:
- Use the same `environment.yml` inside Docker images or managed notebook instances.
- Mount encrypted storage for `inputs/outputs`.
- Configure service accounts for GEE access; store credentials in a secure secret manager instead of local files.

Capture any deviations from this baseline in an ADR and update this document accordingly.
