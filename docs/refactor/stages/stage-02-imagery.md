# Stage 02 — Imagery Download & Shoreline Detection

This stage wraps the current `batch_shoreline_detection` workflow, which orchestrates CoastSat’s image retrieval, preprocessing, and shoreline classification. It will likely split into sub-filters later, but initially we treat it as one stage to match existing functionality.

---

## Current Behavior

- **Function:** `batch_shoreline_detection(metadata, settings, inputs)` in `Complete_Analysis.py`.
- **Responsibilities:**
  1. Retrieve imagery metadata via `SDS_download.retrieve_images` (or load cached metadata).
  2. Preprocess imagery with `SDS_preprocess.preprocess_images`.
  3. Run shoreline detection `SDS_shoreline.run_shoreline_detection`.
  4. Save intermediate outputs (metadata, `output` dict with cross distances, etc.).
  5. Perform cleanup/logging.
- The function expects `inputs` and `settings` dicts produced by Stage 01, uses a `metadata` cache, and returns an `output` dict containing shoreline detections, timestamps, etc.

Pain points:
- Large, monolithic function with intertwined concerns (download, preprocess, classify).
- Hard to retry specific steps without rerunning everything.
- Limited logging/progress reporting between subtasks.
- Metadata caching logic is implicit.

---

## Target Design

- **Inputs:** `PipelineContext` populated by Stages 00–01 (with `inputs_config`, `analysis_settings`, geometry info).
- **Outputs:** Updated context with:
  - `imagery_metadata`: details about downloaded imagery (dates, sources).
  - `shoreline_output`: data structure equivalent to existing `output` dict (cross distances, timestamps, QC info).
  - References to cached imagery files for downstream reuse.
- **Internal sub-filters:** (for future splitting)
  1. Metadata retrieval (GEE queries, caching).
  2. Preprocessing (cloud masking, reprojection).
  3. Shoreline classification.

### Planned Implementation Steps
1. **Wrapper Stage**
   - Implement `ImageryStage` that orchestrates the three subtasks sequentially, reusing existing CoastSat functions.
   - Provide structured logging between steps (download → preprocess → detect).
2. **Context Updates**
   - Store metadata and output data in context (e.g., `context.imagery_metadata`, `context.shoreline_output`).
   - Record cache paths to support reruns or future skip logic.
3. **Caching / Resume**
   - Detect when imagery metadata already exists and allow users to skip downloads through config flags (`reuse_metadata`, etc.).
   - Surface these flags via Stage 00 config to keep behavior consistent.
4. **Error Handling**
   - Fail fast if GEE auth or data retrieval fails; include actionable error messages.
   - Consider partial retry logic for download vs classification (future enhancement).

### Interface Sketch
```python
class ImageryStage(PipelineStage):
    name = "imagery"
    description = "Download imagery, preprocess, and run shoreline detection."

    def run(self, context: PipelineContext) -> None:
        metadata = download_metadata(context.inputs_config, context.run_options)
        processed = preprocess_images(metadata, context.analysis_settings)
        shoreline_output = detect_shorelines(processed, context.analysis_settings)
        context.imagery_metadata = metadata
        context.shoreline_output = shoreline_output
```

---

## Migration Tasks

- [ ] Wrap existing CoastSat download/preprocess/detect calls inside helper functions with clear inputs/outputs.
- [ ] Add logging hooks between substeps to support progress reporting.
- [ ] Define data structures for `imagery_metadata` and `shoreline_output` (typed dictionaries or dataclasses).
- [ ] Add config flags to control cache reuse, parallelism, and optional satellites, ensuring Stage 00 can parse them.
- [ ] Update tests (or add new ones) to cover metadata caching logic and ensure the stage short-circuits appropriately.
- [ ] Extract the legacy `batch_shoreline_detection` logic into `coastsat_pipeline/helpers/imagery.py` so the stage calls our helper rather than importing from `Complete_Analysis`.

---

## Open Questions / TODOs

- **Batch execution:** For now, batch runs will simply iterate sites serially via higher-level orchestration. Leave hooks for future parallelism but do not complicate Stage 02 yet.
- **Persistence strategy:** Metadata and classifier outputs involve thousands of images; plan to persist necessary artifacts to disk immediately (as CoastSat does today) while still storing lightweight references in context. Revisit if we add checkpointing.
- **Data pruning:** Once later stages detect cloudy/outlier imagery, consider deleting or archiving those files to reduce disk usage. Capture requirements before implementing cleanup logic.
- **Progress reporting:** CoastSat already logs progress internally. Stick with existing logging for now but keep the runner flexible so we can replace or augment progress callbacks in a future iteration.

---

## Planned Imagery QC Enhancements

We intend to layer an analyst-guided quality check on top of the existing cloud filters:

1. **Capture Per-Scene Metrics:** During preprocessing/classification we will record, per satellite scene, the cloud-cover stats, valid pixel counts, and MNDWI-derived land/water proportions in a manifest alongside the JPG cache.
2. **Analyst Picks “Ideal” Scenes:** After JPGs are generated, the CLI will prompt the user to review the imagery (one per satellite) and pick an ideal reference scene. The selection UI can be a simple scroller over the cached JPGs. The chosen scene’s metrics become the reference for that satellite/site.
3. **Secondary Filter:** On reruns (or immediately after selection) we will compare every scene’s stored land/water ratios against the reference. Tolerances will be configurable and scaled by the fraction of valid pixels so heavily masked scenes are given appropriate wiggle room. Scenes that deviate beyond the adjusted tolerance will be discarded (and optionally stored in the skipped folder for review).

This approach keeps the current cloud-threshold filtering as the first line of defense, while the second pass leverages richer MNDWI stats aligned with analyst expectations. The manifest makes the process reproducible and supports incremental reruns without reprocessing every scene.
