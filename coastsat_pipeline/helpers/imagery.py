from __future__ import annotations

import pickle
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
from pyproj import CRS

from coastsat import SDS_preprocess, SDS_shoreline, SDS_tools

import shutil

from .imagery_quality import maybe_select_ideal_scenes, load_quality_config
from ..parameters import ImageryOptions


def run_batch_shoreline_detection(
    metadata: Dict[str, Any],
    settings: Dict[str, Any],
    inputs: Dict[str, Any],
    options: Optional[ImageryOptions] = None,
) -> Dict[str, Any]:
    """
    Perform batch shoreline detection and return the output dictionary.
    """
    options = options or ImageryOptions()

    scene_metrics_manifest, scene_metrics_path = _load_scene_metrics(settings)

    preprocess_images(metadata, settings, options, scene_metrics_manifest, scene_metrics_path)
    cached_output = load_cached_output(settings, cache_enabled=options.cache_enabled)
    if cached_output is not None:
        print("Using cached shorelines extraction output")
        return cached_output

    # Reload updated metrics and quality config after preprocessing/selection.
    scene_metrics_manifest, _ = _load_scene_metrics(settings)
    quality_cfg = load_quality_config(settings["inputs"]["filepath"])
    preprocessed_dir = Path(settings["inputs"]["filepath"]) / "jpg_files" / "preprocessed"
    quality_skip_dir = Path(settings["inputs"]["filepath"]) / "jpg_files" / "quality_skipped"
    metadata = _apply_quality_filter(
        metadata,
        scene_metrics_manifest,
        quality_cfg,
        preprocessed_dir=preprocessed_dir,
        skip_dir=quality_skip_dir,
    )

    output = run_detection(metadata, settings)

    if options.save_geojson:
        write_geojson(output, settings)
    if options.save_plots:
        plot_mapped_shorelines(output, settings)
    return output


def preprocess_images(
    metadata: Dict[str, Any],
    settings: Dict[str, Any],
    imagery_opts: ImageryOptions,
    scene_metrics_manifest: Dict[str, Any] | None = None,
    scene_metrics_path: Path | None = None,
) -> None:
    skip_existing = imagery_opts.skip_existing_jpg
    capture_skipped = imagery_opts.capture_skipped_jpgs
    debug_dir = None
    if capture_skipped:
        debug_dir = str(Path(settings["inputs"]["filepath"]) / "jpg_files" / "skipped")
    manifest, manifest_path = _load_jpg_manifest(settings)
    if scene_metrics_manifest is None or scene_metrics_path is None:
        scene_metrics, scene_metrics_file = _load_scene_metrics(settings)
    else:
        scene_metrics = scene_metrics_manifest
        scene_metrics_file = scene_metrics_path
    metrics_buffer: list[Dict[str, Any]] = []

    metadata_to_process = metadata
    if skip_existing:
        missing_indices = _compute_missing_jpg_indices(metadata, manifest, settings)
        if not missing_indices:
            print("[Imagery] Skipping JPG conversion; preprocessed files already exist.")
            return
        total_missing = sum(len(idxs) for idxs in missing_indices.values())
        print(f"[Imagery] Converting {total_missing} new scenes to JPG.")
        metadata_to_process = _filter_metadata_by_indices(metadata, missing_indices)

    if not imagery_opts.skip_jpg:
        SDS_preprocess.save_jpg(
            metadata_to_process,
            settings,
            use_matplotlib=True,
            debug_skipped_dir=debug_dir,
            metrics_callback=metrics_buffer.append,
        )
    _update_jpg_manifest(manifest, metadata_to_process, manifest_path)
    _update_scene_metrics(scene_metrics, metrics_buffer, scene_metrics_file)
    if imagery_opts.prompt_for_ideal_selection:
        maybe_select_ideal_scenes(
            site_dir=settings["inputs"]["filepath"],
            scene_metrics=scene_metrics,
            enable_prompt=True,
            jpg_dir=Path(settings["inputs"]["filepath"]) / "jpg_files" / "preprocessed",
        )


def load_cached_output(settings: Dict[str, Any], cache_enabled: bool = True) -> Optional[Dict[str, Any]]:
    if not cache_enabled:
        return None
    filepath = settings["inputs"]["filepath"]
    sitename = settings["inputs"]["sitename"]
    cache_path = Path(filepath) / f"{sitename}_output.pkl"
    try:
        with cache_path.open("rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None


def run_detection(metadata: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    # this saves <sitename>_output.pkl and shorelines.kml
    # and removes duplicates and inaccurate georefs
    output = SDS_shoreline.extract_shorelines(metadata, settings)
    return output


def write_geojson(output: Dict[str, Any], settings: Dict[str, Any]) -> None:
    geomtype = "points"
    gdf = SDS_tools.output_to_gdf(output, geomtype)
    if gdf is None:
        raise RuntimeError("Output does not contain any mapped shorelines")
    gdf.crs = CRS(settings["output_epsg"])
    target = Path(settings["inputs"]["filepath"]) / f"{settings['inputs']['sitename']}_output_{geomtype}.geojson"
    gdf.to_file(target, driver="GeoJSON", encoding="utf-8")


def plot_mapped_shorelines(output: Dict[str, Any], settings: Dict[str, Any]) -> None:
    fig = plt.figure(figsize=[15, 8], tight_layout=True)
    plt.axis("equal")
    plt.xlabel("Eastings")
    plt.ylabel("Northings")
    plt.grid(linestyle=":", color="0.5")
    for i in range(len(output["shorelines"])):
        sl = output["shorelines"][i]
        date = output["dates"][i]
        plt.plot(sl[:, 0], sl[:, 1], ".", label=date.strftime("%d-%m-%Y"))
    fig.savefig(Path(settings["inputs"]["filepath"]) / "mapped_shorelines.jpg", dpi=200)
    plt.close(fig)


def _load_jpg_manifest(settings: Dict[str, Any]) -> tuple[Dict[str, set[str]], Path]:
    filepath_data = Path(settings["inputs"]["filepath"])
    manifest_path = filepath_data / "jpg_files" / "preprocessed_manifest.json"
    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {sat: set(files) for sat, files in data.items()}, manifest_path
    except FileNotFoundError:
        return {}, manifest_path


def _compute_missing_jpg_indices(
    metadata: Dict[str, Any],
    manifest: Dict[str, set[str]],
    settings: Dict[str, Any],
) -> Dict[str, list[int]]:
    jpg_dir = Path(settings["inputs"]["filepath"]) / "jpg_files" / "preprocessed"
    missing: Dict[str, list[int]] = {}
    for satname, sat_meta in metadata.items():
        filenames = sat_meta.get("filenames", [])
        processed = manifest.setdefault(satname, set())
        for idx, name in enumerate(filenames):
            date_str = name[:19]
            expected_file = jpg_dir / f"{date_str}_{satname}.jpg"
            file_exists = expected_file.exists()
            if name not in processed or not file_exists:
                missing.setdefault(satname, []).append(idx)
                processed.discard(name)
    return missing


def _filter_metadata_by_indices(metadata: Dict[str, Any], indices_map: Dict[str, list[int]]) -> Dict[str, Any]:
    subset: Dict[str, Any] = {}
    for satname, indices in indices_map.items():
        sat_meta = metadata[satname]
        new_meta: Dict[str, Any] = {}
        for key, values in sat_meta.items():
            if isinstance(values, list):
                new_meta[key] = [values[i] for i in indices]
            elif isinstance(values, np.ndarray):
                new_meta[key] = values[indices]
            else:
                new_meta[key] = values
        subset[satname] = new_meta
    return subset


def _update_jpg_manifest(manifest: Dict[str, set[str]], processed_metadata: Dict[str, Any], manifest_path: Path) -> None:
    jpg_dir = manifest_path.parent / "preprocessed"
    for satname, sat_meta in processed_metadata.items():
        filenames = sat_meta.get("filenames", [])
        if not filenames:
            continue
        entries = manifest.setdefault(satname, set())
        for name in filenames:
            date_str = name[:19]
            expected_file = jpg_dir / f"{date_str}_{satname}.jpg"
            if expected_file.exists():
                entries.add(name)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {sat: sorted(list(files)) for sat, files in manifest.items()}
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)


def _load_scene_metrics(settings: Dict[str, Any]) -> tuple[Dict[str, Any], Path]:
    filepath = Path(settings["inputs"]["filepath"]) / "jpg_files" / "scene_metrics.json"
    try:
        with filepath.open("r", encoding="utf-8") as f:
            return json.load(f), filepath
    except FileNotFoundError:
        return {}, filepath


def _update_scene_metrics(manifest: Dict[str, Any], entries: list[Dict[str, Any]], path: Path) -> None:
    if not entries:
        return
    for entry in entries:
        scene_id = entry.get("scene_id")
        if scene_id:
            manifest[scene_id] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _apply_quality_filter(
    metadata: Dict[str, Any],
    scene_metrics: Dict[str, Any],
    quality_config: Dict[str, Any],
    preprocessed_dir: Path,
    skip_dir: Path,
) -> Dict[str, Any]:
    satellites_cfg = (quality_config or {}).get("satellites") or {}
    if not satellites_cfg:
        print("No satellite configuration in quality configuration")
        return metadata
    filtered: Dict[str, Any] = {}
    for satname, sat_meta in metadata.items():
        reference = satellites_cfg.get(satname)
        if not reference:
            filtered[satname] = sat_meta
            continue
        filenames = sat_meta.get("filenames", [])
        keep: list[int] = []
        removed = 0
        for idx, scene_id in enumerate(filenames):
            metrics_entry = scene_metrics.get(scene_id)
            if _scene_meets_quality(metrics_entry, reference):
                keep.append(idx)
            else:
                removed += 1
        if removed:
            print(f"[Imagery] Removed {removed} scenes for satellite {satname} due to quality tolerances.")
            _copy_rejected_jpgs(filenames, keep, scene_metrics, preprocessed_dir, skip_dir)
            filtered[satname] = _subset_metadata(sat_meta, keep)
        else:
            filtered[satname] = sat_meta
    return filtered


def _scene_meets_quality(metrics: Dict[str, Any] | None, reference: Dict[str, Any]) -> bool:
    if not reference:
        return True
    if metrics is None:
        return True
    land = metrics.get("land_fraction")
    water = metrics.get("water_fraction")
    ref_land = reference.get("land_fraction")
    ref_water = reference.get("water_fraction")
    if land is None or water is None or ref_land is None or ref_water is None:
        return True
    base_tol = reference.get("base_tolerance", 0.10)
    scene_valid = metrics.get("valid_pixels")
    ref_valid = reference.get("valid_pixels") or scene_valid
    if scene_valid and ref_valid:
        ratio = max(ref_valid / max(scene_valid, 1), 1.0)
        effective_tol = min(0.5, base_tol * ratio)
    else:
        effective_tol = base_tol
    if abs(land - ref_land) > effective_tol:
        return False
    if abs(water - ref_water) > effective_tol:
        return False
    return True


def _subset_metadata(meta: Dict[str, Any], indices: list[int]) -> Dict[str, Any]:
    subset: Dict[str, Any] = {}
    for key, value in meta.items():
        if isinstance(value, list):
            subset[key] = [value[i] for i in indices]
        elif isinstance(value, np.ndarray):
            subset[key] = value[indices]
        else:
            subset[key] = value
    return subset


def _copy_rejected_jpgs(
    filenames: list[str],
    keep_indices: list[int],
    scene_metrics: Dict[str, Any],
    preprocessed_dir: Path,
    skip_dir: Path,
) -> None:
    keep_set = set(keep_indices)
    copied = 0
    skip_dir.mkdir(parents=True, exist_ok=True)
    for idx, scene_id in enumerate(filenames):
        if idx in keep_set:
            continue
        metrics_entry = scene_metrics.get(scene_id)
        if not metrics_entry:
            continue
        date = metrics_entry.get("date")
        sat = metrics_entry.get("satellite")
        if not date or not sat:
            continue
        source = preprocessed_dir / f"{date}_{sat}.jpg"
        if not source.exists():
            continue
        destination = skip_dir / source.name
        try:
            shutil.copy2(source, destination)
            copied += 1
        except Exception:
            continue
    if copied:
        print(f"[Imagery] Copied {copied} rejected scenes to {skip_dir}.")
