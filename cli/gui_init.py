"""
Gooey-based GUI for the legacy init workflow (settings.json creation).

Replicates the legacy Typer `init` flow: sets up project folders, detects EPSG,
clips shoreline, generates transects, writes settings.json, and optionally runs
analysis via the selected engine (legacy scripts or new pipeline).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List

import geopandas as gpd
from gooey import Gooey, GooeyParser

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cli.file_utils import setup_project_directories  # noqa: E402
from cli.geo_utils import (  # noqa: E402
    create_and_save_reference_shoreline,
    generate_and_save_transects,
    load_aoi_and_shoreline,
    pick_canadian_utm_epsg,
)
from cli.dialogs import run_analysis_from_config  # noqa: E402

IMAGE_DIR = ROOT_DIR / "assets" / "gooey_icons"


def _split_paths(raw: str) -> List[str]:
    """
    Gooey returns multi-file selections as a separator-delimited string.
    Support '|', ';', ',' and newlines to be tolerant across platforms.
    """
    parts: List[str] = []
    for chunk in raw.replace("\n", "|").replace(";", "|").replace(",", "|").split("|"):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def _validate_numeric(args) -> None:
    """Validate numeric GUI inputs early so we can fail fast with a clear message."""
    if args.transect_spacing <= 0:
        raise ValueError("Transect spacing must be > 0.")
    if args.transect_length <= 0:
        raise ValueError("Transect length must be > 0.")
    if args.transect_offset_ratio < 0 or args.transect_offset_ratio > 1:
        raise ValueError("Transect offset ratio must be between 0 and 1.")
    if args.transect_skip_threshold <= 0:
        raise ValueError("Transect skip threshold must be > 0.")
    if args.tide_method == "csv":
        float(args.beach_slope)
    if args.enable_tide_filter:
        lower = float(args.tide_lower_percentile)
        upper = float(args.tide_upper_percentile)
        if lower < 0 or upper > 100 or lower >= upper:
            raise ValueError("Tide percentiles must satisfy 0 <= lower < upper <= 100.")
    if args.epsg is not None and args.epsg <= 0:
        raise ValueError("EPSG must be a positive integer.")


def _build_tide_config(args) -> dict:
    """
    Normalize tide inputs from the GUI into the shape expected by init helpers.
    """
    tide_config: dict = {"method": args.tide_method}
    if args.tide_method == "fes":
        tide_config["fes_config"] = args.fes_config
    else:
        tide_config["tide_csv_path"] = args.tide_csv
        tide_config["reference_elevation"] = 0.0
        tide_config["beach_slope"] = float(args.beach_slope)
    if args.enable_tide_filter:
        tide_config["tide_filter"] = {
            "lower_percentile": float(args.tide_lower_percentile),
            "upper_percentile": float(args.tide_upper_percentile),
        }
    return tide_config


def _detect_epsg(aoi_path: Path, manual_epsg: int | None) -> int:
    """
    Try to auto-pick a Canadian UTM EPSG; allow manual override from the GUI.
    """
    if manual_epsg:
        return manual_epsg
    try:
        return pick_canadian_utm_epsg(str(aoi_path))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"EPSG detection failed for {aoi_path}: {exc}")


def _init_site(
    aoi_path: Path,
    sitename: str,
    shoreline_gdf: gpd.GeoDataFrame,
    tide_config: dict,
    base_dir: Path,
    epsg: int,
    transect_opts: dict,
) -> dict:
    """
    Core init routine: scaffold folders, clip shoreline to AOI, generate transects,
    write settings.json, and copy inputs into place. Returns paths for display.
    """
    paths = setup_project_directories(str(base_dir), sitename)
    site_dir = Path(paths["site_dir"])
    input_dir = Path(paths["input_dir"])
    output_dir = Path(paths["output_dir"])
    aoi_dest = Path(paths["aoi_dest"])
    ref_out_path = Path(paths["ref_out_path"])
    transects_out_path = Path(paths["transects_out_path"])

    aoi_gdf, _ = load_aoi_and_shoreline(str(aoi_path), "", preloaded_shoreline=shoreline_gdf)
    reference_gdf = create_and_save_reference_shoreline(
        shoreline_gdf=shoreline_gdf, aoi_gdf=aoi_gdf, output_path=str(ref_out_path)
    )

    generate_and_save_transects(
        reference_gdf=reference_gdf,
        epsg=epsg,
        spacing=transect_opts["spacing"],
        length=transect_opts["length"],
        offset_ratio=transect_opts["offset_ratio"],
        skip_threshold=transect_opts["skip_threshold"],
        output_path=str(transects_out_path),
    )

    shutil.copy2(aoi_path, aoi_dest)

    settings = {
        "inputs": {
            "sitename": sitename,
            "aoi_path": os.path.relpath(aoi_dest, start=site_dir),
            "reference_shoreline": os.path.relpath(ref_out_path, start=site_dir),
            "transects": os.path.relpath(transects_out_path, start=site_dir),
        },
        "output_dir": os.path.relpath(output_dir, start=site_dir),
        "output_epsg": epsg,
    }

    if tide_config["method"] == "fes":
        settings["inputs"]["fes_config"] = tide_config["fes_config"]
    else:
        settings["inputs"].update(
            {
                "tide_csv_path": tide_config["tide_csv_path"],
                "reference_elevation": tide_config["reference_elevation"],
                "beach_slope": tide_config["beach_slope"],
            }
        )
    if tide_config.get("tide_filter"):
        settings["tide_filter"] = tide_config["tide_filter"]

    settings_path = site_dir / "settings.json"
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=4)

    return {"settings_path": settings_path, "output_dir": output_dir, "epsg": epsg}


@Gooey(
    program_name="CoastSat Init GUI",
    default_size=(800, 720),
    clear_before_run=True,
    show_restart_button=False,
    image_dir=str(IMAGE_DIR),
    navigation="TABBED",
    tabbed_groups=True,
    progress_regex=r"^PROGRESS: (?P<pct>\d+)%",
    progress_expr="pct",
)
def main() -> None:
    parser = GooeyParser(description="Create CoastSat settings.json and optionally run analysis.")
    parser.add_argument("--engine", choices=["legacy", "pipeline"], default="legacy", help="Analysis engine to run after init.")
    parser.add_argument("--base_dir", required=True, widget="DirChooser", help="Base directory where the project folder will be created.")
    parser.add_argument("--sitename", required=True, help="Project name (used as folder name).")
    parser.add_argument("--shoreline", required=True, widget="FileChooser", help="Shoreline GeoJSON/Shapefile covering the AOI(s).")
    parser.add_argument("--mode", choices=["single", "batch"], default="single", help="Initialize one AOI or multiple.")
    parser.add_argument("--aoi", widget="FileChooser", help="AOI KML (single mode).")
    parser.add_argument("--aois", widget="MultiFileChooser", help="AOI KML files (batch mode).")

    # Tide inputs: choose FES or CSV, optional filter.
    tide_group = parser.add_argument_group("Tide correction")
    tide_group.add_argument("--tide_method", choices=["fes", "csv"], default="fes", help="Choose tide correction mode.")
    tide_group.add_argument("--fes_config", widget="FileChooser", help="FES2022 YAML config (for FES mode).")
    tide_group.add_argument("--tide_csv", widget="FileChooser", help="Tide CSV path (for CSV mode).")
    tide_group.add_argument("--beach_slope", default=0.1, help="Beach slope for CSV tide mode.", type=float)

    tide_filter_group = parser.add_argument_group("Tide filtering", gooey_options={"group": "Tide correction"})
    tide_filter_group.add_argument("--enable_tide_filter", action="store_true", help="Enable tide percentile filtering.")
    tide_filter_group.add_argument("--tide_lower_percentile", default=5.0, type=float, help="Lower percentile to keep (0-100).")
    tide_filter_group.add_argument("--tide_upper_percentile", default=95.0, type=float, help="Upper percentile to keep (0-100).")

    epsg_group = parser.add_argument_group("EPSG")
    epsg_group.add_argument("--epsg", type=int, help="Manual EPSG override. Leave blank to auto-detect from AOI.")

    # Transect geometry controls (advanced).
    tran_group = parser.add_argument_group("Transects (advanced)")
    tran_group.add_argument("--transect_spacing", default=100.0, type=float, help="Spacing between transects (m).")
    tran_group.add_argument("--transect_length", default=200.0, type=float, help="Transect total length (m).")
    tran_group.add_argument("--transect_offset_ratio", default=0.75, type=float, help="Fraction seaward vs landward (0-1).")
    tran_group.add_argument("--transect_skip_threshold", default=300.0, type=float, help="Skip shoreline segments shorter than this (m).")

    parser.add_argument("--run_now", action="store_true", help="Run analysis immediately after init.")

    args = parser.parse_args()

    try:
        _validate_numeric(args)
    except Exception as exc:  # noqa: BLE001
        print(f"Validation error: {exc}")
        return

    base_dir = Path(args.base_dir).expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    shoreline_path = Path(args.shoreline).expanduser().resolve()
    if not shoreline_path.exists():
        print(f"Shoreline file not found: {shoreline_path}")
        return

    try:
        shoreline_gdf = gpd.read_file(shoreline_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to read shoreline: {exc}")
        return

    if args.tide_method == "fes" and not args.fes_config:
        raise ValueError("Tide method FES is selected. Please select a FES config file")

    if args.mode == "single":
        if not args.aoi:
            print("Please select an AOI file for single mode.")
            return
        aoi_paths: Iterable[str] = [args.aoi]
        sitenames = [args.sitename]
    else:
        if not args.aois:
            print("Please select AOI files for batch mode.")
            return
        aoi_paths = _split_paths(args.aois)
        if not aoi_paths:
            print("No AOI files parsed from selection.")
            return
        sitenames = [f"{args.sitename}_{str(i + 1).zfill(3)}" for i in range(len(aoi_paths))]

    tide_config = _build_tide_config(args)
    tran_opts = {
        "spacing": float(args.transect_spacing),
        "length": float(args.transect_length),
        "offset_ratio": float(args.transect_offset_ratio),
        "skip_threshold": float(args.transect_skip_threshold),
    }

    results = []
    for aoi_path_str, sitename in zip(aoi_paths, sitenames):
        aoi_path = Path(aoi_path_str).expanduser().resolve()
        if not aoi_path.exists():
            print(f"AOI not found: {aoi_path}")
            return
        try:
            epsg = _detect_epsg(aoi_path, args.epsg)
        except Exception as exc:  # noqa: BLE001
            print(f"EPSG error for {aoi_path}: {exc}")
            return

        print(f"\nInitializing site '{sitename}' (EPSG {epsg})...")
        try:
            result = _init_site(
                aoi_path=aoi_path,
                sitename=sitename,
                shoreline_gdf=shoreline_gdf,
                tide_config=tide_config,
                base_dir=base_dir,
                epsg=epsg,
                transect_opts=tran_opts,
            )
            results.append(result)
            print(f"  settings.json: {result['settings_path']}")
            print(f"  outputs dir  : {result['output_dir']}")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to initialize {sitename}: {exc}")
            return

    print("\nInitialization complete.")

    if args.run_now:
        print("\nStarting analysis...")
        for r in results:
            exit_code = run_analysis_from_config(Path(r["settings_path"]), engine=args.engine)
            if exit_code == 0:
                print(f"  {r['settings_path'].parent.name}: success")
            else:
                print(f"  {r['settings_path'].parent.name}: failed (exit code {exit_code})")


if __name__ == "__main__":
    main()
