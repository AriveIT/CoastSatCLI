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


@dataclass
class ImageryOptions:
    save_geojson: bool = True
    save_plots: bool = True
    cache_enabled: bool = True
    max_dist_ref: float = 500.0
    skip_existing_jpg: bool = True


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

    preprocess_images(metadata, settings)
    cached_output = load_cached_output(settings, cache_enabled=options.cache_enabled)
    if cached_output is not None:
        return cached_output

    settings["reference_shoreline"] = SDS_preprocess.get_reference_sl_from_geojson(
        settings["inputs"]["reference_geojson"],
        settings["output_epsg"],
    )
    settings["max_dist_ref"] = options.max_dist_ref

    output = run_detection(metadata, settings)

    if options.save_geojson:
        write_geojson(output, settings)
    if options.save_plots and settings.get("save_figure", False):
        plot_mapped_shorelines(output, settings)
    return output


def preprocess_images(metadata: Dict[str, Any], settings: Dict[str, Any]) -> None:
    imagery_opts = settings.get("imagery_options", {})
    skip_existing = imagery_opts.get("skip_existing_jpg", True)
    capture_skipped = imagery_opts.get("capture_skipped_jpgs", False)
    debug_dir = None
    if capture_skipped:
        debug_dir = str(Path(settings["inputs"]["filepath"]) / "jpg_files" / "skipped")
    manifest, manifest_path = _load_jpg_manifest(settings)

    metadata_to_process = metadata
    if skip_existing:
        missing_indices = _compute_missing_jpg_indices(metadata, manifest, settings)
        if not missing_indices:
            print("[Imagery] Skipping JPG conversion; preprocessed files already exist.")
            return
        total_missing = sum(len(idxs) for idxs in missing_indices.values())
        print(f"[Imagery] Converting {total_missing} new scenes to JPG.")
        metadata_to_process = _filter_metadata_by_indices(metadata, missing_indices)

    SDS_preprocess.save_jpg(
        metadata_to_process,
        settings,
        use_matplotlib=True,
        debug_skipped_dir=debug_dir,
    )
    _update_jpg_manifest(manifest, metadata_to_process, manifest_path)
    print("[Step 4] Generating RGB time-lapse animation (this may take several minutes)...")


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
    output = SDS_shoreline.extract_shorelines(metadata, settings)
    output = SDS_tools.remove_duplicates(output)
    output = SDS_tools.remove_inaccurate_georef(output, 10)
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
