# Imagery QC & Ideal Scene Selection Plan

This document describes the planned end-to-end workflow for the forthcoming MNDWI-based imagery quality check. It is intentionally granular so implementation can be split across multiple tasks.

---

## Overview

1. **Capture Per-Scene Metrics** during Stage 02 preprocessing/classification.
2. **Persist Metrics** to a manifest stored next to the JPG cache. (Implemented)
3. **Prompt Analyst to Select Ideals** (per satellite) after JPG creation. (Implemented with Tkinter viewer)
4. **Persist Ideal Selections & Tolerances** to a new QC config file.
5. **Apply Secondary QC Filter** on reruns using stored metrics + tolerances. (Implemented)

Each step is described in detail below.

---

## Step 1 — Capture Per-Scene Metrics

### Owner
Stage 02 helper (`coastsat_pipeline/helpers/imagery.py`) and CoastSat modules (`SDS_preprocess`, `SDS_shoreline`, `SDS_classify`).

### Data to capture per scene
- `satellite`: L5/L7/L8/L9/S2.
- `scene_id`: filename or GEE identifier.
- `acquisition_date`.
- `cloud_cover_combined` and refined `cloud_cover` (post nodata removal).
- `valid_pixel_count` (total pixels minus clouds/nodata).
- `mndwi_land_fraction` and `mndwi_water_fraction` (only counting valid pixels).
- Optional: additional stats (MNDWI threshold used, QC flags, etc.)

### Implementation notes
- Extend `SDS_preprocess.save_jpg` (or a wrapper) to compute the metrics immediately after `preprocess_single` returns, before QC skips happen.
- If the scene fails the existing cloud thresholds, still record the metrics (so we know why it was skipped) and optionally dump the raw JPG into `jpg_files/skipped`.
- Return the metrics to the helper so it can persist them even when scenes are skipped.

---

## Step 2 — Persist Metrics Manifest

### Location
`<site>/outputs/jpg_files/scene_metrics.json` (or `.csv`). Lives alongside `preprocessed/`, `skipped/`, and `preprocessed_manifest.json`.

### Behavior
- Manifest is keyed by `scene_id` (or `<sat>_<date>`). Value is the metrics payload from Step 1.
- When reprocessing a scene, overwrite its entry with the latest metrics.
- Provide helper functions (`load_scene_metrics`, `update_scene_metrics`) similar to the JPG manifest helpers added earlier.

---

## Step 3 — Analyst Selection of Ideal Scenes

### Trigger
After Stage 02 finishes preprocessing JPGs (only when no prior `imagery_quality` config exists), or via a dedicated CLI command.

### UX
- Launch a simple viewer (Tkinter/PySimpleGUI/matplotlib) that lists satellites (L5/L7/L8/L9).
- For each satellite, display thumbnails (pulled from `jpg_files/preprocessed/<scene>.jpg`) with acquisition date, cloud %, valid pixel count, land/water fractions.
- Analyst selects one scene per satellite as the “ideal”.
- Optionally allow skipping a satellite if no scenes exist.

### Output
For each selected scene, capture:
- `scene_id`
- `land_fraction`
- `water_fraction`
- `valid_pixel_count`
- Analyst-defined `tolerance` (default provided, editable)

Persist the selections (Step 4).

---

## Step 4 — Persist Ideal QC Config

### File
`<site>/outputs/imagery_quality.json`

### Structure
```json
{
  "L5": {
    "scene_id": "LC05_L1TP_...",
    "land_fraction": 0.63,
    "water_fraction": 0.37,
    "valid_pixels": 450000,
    "base_tolerance": 0.10
  },
  "L7": { ... }
}
```

### Notes
- This file is independent of the original `settings.json` to keep Stage 00 immutable.
- Stage 02 checks for this file on startup; if absent, triggers Step 3. If present, loads tolerances for QC filtering.
- Provide a CLI command to reset/reselect ideals (`coastsatcli.py quality select --config ...`) for later adjustments.

---

## Step 5 — Apply Secondary QC Filter

### Inputs
- Per-scene metrics manifest (`scene_metrics.json`).
- Ideal QC config (`imagery_quality.json`).
- Settings flag (e.g., `settings["imagery_options"]["enforce_quality"]`, default true).

### Algorithm
For each scene:
1. Load metrics and find the ideal entry for the same satellite.
2. Compute `valid_ratio = scene.valid_pixels / ideal.valid_pixels` (clamped between 0 and 1).
3. Adjust tolerance: `effective_tol = ideal.base_tolerance / max(valid_ratio, eps)` or other scheme (document formula).
4. Compare `abs(scene.land_fraction - ideal.land_fraction)` (and similarly for water). If either exceeds `effective_tol`, mark the scene as invalid.
5. Invalid scenes:
   - Skip downstream (don’t include in `metadata_to_process` for detection).
   - Optionally copy their JPG to `jpg_files/skipped_quality` for review.
   - Record reason in manifest (e.g., `quality_fail: true`, `quality_delta: ...`).

### Logging/Reporting
- Emit summary: `Skipped 42 scenes (L5: 30, L7: 12) due to MNDWI deviation > tolerance`.
- Update `tide_filter_stats`-like structure (e.g., `imagery_quality_stats`) in `settings` or context for downstream stages.

---

## Additional Considerations

- **Backfill Manifest:** For existing projects rerun after upgrade, run a manifest backfill script to populate metrics for already-accepted JPGs.
- **Tests:** Add unit tests for manifest helpers, tolerance calculation, and quality filtering (mock metrics + config).
- **CLI Integration:** Document the new config files (`scene_metrics.json`, `imagery_quality.json`) in the user guide and refactor docs.
- **Performance:** Metric recording should add minimal overhead; if necessary, make the feature optional via `imagery_options.capture_scene_metrics`.
