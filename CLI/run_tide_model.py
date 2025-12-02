"""
Standalone helper to generate a tide time-series CSV using the FES2022 model.

Typical usage:
    python cli/run_tide_model.py --config path/to/settings.json --output tides.csv
or
    python cli/run_tide_model.py --fes-config C:/fes/fes2022.yaml --lon -123.5 --lat 48.5
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence, Tuple

import pytz
import pyfes
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape

import sys
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from coastsat import SDS_slope, SDS_tools


DEFAULT_START = "2013-01-01T00:00:00Z"
DEFAULT_END = "2025-12-31T00:00:00Z"
DEFAULT_TIMESTEP_MIN = 15


@dataclass
class TideRunConfig:
    fes_config_path: Path
    lon: float | None = None
    lat: float | None = None
    aoi_path: Path | None = None
    sitename: str | None = None


def coords_to_geometry(coord_wrapped) -> Polygon | LineString | Point:
    if not coord_wrapped:
        raise ValueError("AOI coordinates are empty.")
    coords = coord_wrapped[0]
    if not coords:
        raise ValueError("AOI coordinate sequence is empty.")
    if len(coords) >= 3:
        polygon = Polygon(coords)
        if polygon.is_valid and polygon.area > 0:
            return polygon
    if len(coords) >= 2:
        return LineString(coords)
    return Point(coords[0])


def parse_kml_path(path: Path):
    tree = ET.parse(str(path))
    namespace = {"kml": "http://www.opengis.net/kml/2.2"}
    # look for all coordinate lists
    coords = []
    for coord_node in tree.findall(".//kml:coordinates", namespaces=namespace):
        text = coord_node.text or ""
        tokens = text.replace("\n", " ").replace("\t", " ").split()
        for token in tokens:
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                except ValueError:
                    continue
                coords.append([lon, lat])
    if len(coords) >= 3 and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def load_aoi_geometry(path: Path):
    path = path.expanduser().resolve()
    ext = path.suffix.lower()
    if ext in (".kml", ".kmz"):
        coords = parse_kml_path(path)
        if coords:
            return coords_to_geometry([coords])
        return coords_to_geometry(SDS_tools.polygon_from_kml(str(path)))
    if ext in (".geojson", ".json"):
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        geom_payload = None
        if "features" in payload and payload["features"]:
            geom_payload = payload["features"][0]["geometry"]
        elif "geometry" in payload:
            geom_payload = payload["geometry"]
        if geom_payload is None:
            raise ValueError(f"No geometry found in {path}")
        return shape(geom_payload)
    raise ValueError(f"Unsupported AOI format: {path}")


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO-8601 strings (with or without timezone) and return UTC-aware datetime."""
    sanitized = value.strip()
    if sanitized.endswith("Z"):
        sanitized = sanitized[:-1] + "+00:00"
    dt = datetime.fromisoformat(sanitized)
    if dt.tzinfo is None:
        return pytz.utc.localize(dt)
    return dt.astimezone(pytz.utc)


def load_settings_config(config_path: Path) -> Tuple[dict, Path]:
    config_path = config_path.expanduser().resolve()
    with config_path.open("r", encoding="utf-8") as fp:
        config = json.load(fp)
    return config, config_path.parent


def resolve_tide_run_config(args: argparse.Namespace) -> TideRunConfig:
    config_dict = None
    base_dir = None
    if args.config:
        config_dict, base_dir = load_settings_config(Path(args.config))

    fes_config = args.fes_config
    sitename = args.sitename
    lon = args.lon
    lat = args.lat
    aoi_path = Path(args.aoi_path).expanduser().resolve() if args.aoi_path else None

    if config_dict:
        inputs = config_dict.get("inputs", {})
        sitename = sitename or inputs.get("sitename")
        if not fes_config:
            fes_cfg = inputs.get("fes_config")
            if fes_cfg:
                fes_config = str(Path(fes_cfg).expanduser())
        if not lon and not lat:
            lon = inputs.get("centroid_lon")
            lat = inputs.get("centroid_lat")
        if not aoi_path:
            aoi_candidate = inputs.get("aoi_path")
            if aoi_candidate:
                aoi_path = (base_dir / aoi_candidate).expanduser().resolve()

    if not fes_config:
        raise ValueError("A FES2022 YAML file is required (pass --fes-config or include in settings.json).")

    fes_path = Path(fes_config).expanduser().resolve()
    if not fes_path.exists():
        raise FileNotFoundError(f"FES config not found: {fes_path}")

    if (lon is None or lat is None) and not aoi_path:
        raise ValueError("Either provide --lon/--lat or ensure settings.json contains an AOI path.")

    if lon is not None and lat is None or lat is not None and lon is None:
        raise ValueError("Both --lon and --lat must be supplied together.")

    return TideRunConfig(
        fes_config_path=fes_path,
        lon=float(lon) if lon is not None else None,
        lat=float(lat) if lat is not None else None,
        aoi_path=aoi_path,
        sitename=sitename,
    )


def determine_centroid(config: TideRunConfig, ocean_tide, load_tide) -> Tuple[float, float]:
    if config.lon is not None and config.lat is not None:
        lon = config.lon
        if lon < 0:
            lon += 360.0
        return lon, config.lat

    geom = None
    if config.aoi_path:
        try:
            geom = load_aoi_geometry(config.aoi_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[run_tide_model] Warning: failed to load AOI geometry ({exc}); falling back to point centroid.")

    if geom is None:
        if config.lon is None or config.lat is None:
            raise ValueError("No AOI geometry available and lon/lat not provided.")
        lon = config.lon
        if lon < 0:
            lon += 360.0
        return lon, config.lat

    polygon_geom = None
    if isinstance(geom, Polygon):
        polygon_geom = geom
    elif isinstance(geom, MultiPolygon):
        polygon_geom = max(geom.geoms, key=lambda g: g.area, default=None)

    if polygon_geom and polygon_geom.area > 0:
        try:
            centroid = SDS_tools.select_valid_centroid(polygon_geom, ocean_tide, load_tide)
            lon = centroid[0]
            if lon < 0:
                lon += 360.0
            return lon, centroid[1]
        except Exception as exc:  # noqa: BLE001
            print(f"[run_tide_model] Warning: centroid refinement failed, falling back to raw geometry ({exc}).")

    centroid_point = geom.centroid if geom is not None else None
    if centroid_point is None or centroid_point.is_empty:
        raise ValueError(f"Could not derive centroid from AOI: {config.aoi_path}")
    lon = centroid_point.x
    if lon < 0:
        lon += 360.0
    return lon, centroid_point.y


def compute_tide_series(
    coords: Tuple[float, float],
    start: datetime,
    end: datetime,
    timestep_seconds: int,
    ocean_tide,
    load_tide,
) -> Tuple[Sequence[datetime], Sequence[float]]:
    if end <= start:
        raise ValueError("End datetime must be after start datetime.")
    return SDS_slope.compute_tide(coords, [start, end], timestep_seconds, ocean_tide, load_tide)


def write_csv(path: Path, timestamps: Sequence[datetime], tides: Sequence[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        fp.write("dates,tide\n")
        for date, tide in zip(timestamps, tides):
            iso = date.isoformat()
            fp.write(f"{iso},{tide:.6f}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a tide time series CSV using FES2022.")
    parser.add_argument("--config", help="Path to settings.json (optional).")
    parser.add_argument(
        "--fes-config",
        help="Absolute path to FES2022 YAML. Required if --config is omitted or missing fes_config.",
    )
    parser.add_argument("--lon", type=float, help="Longitude in degrees east (negative for west).")
    parser.add_argument("--lat", type=float, help="Latitude in degrees north.")
    parser.add_argument(
        "--aoi-path",
        help="AOI polygon (KML/GeoJSON). Used to auto-pick centroid when lon/lat are omitted.",
    )
    parser.add_argument("--sitename", help="Optional sitename label for logs when no config is provided.")
    parser.add_argument(
        "--start",
        default=DEFAULT_START,
        help=f"ISO start datetime in UTC (default: {DEFAULT_START}).",
    )
    parser.add_argument(
        "--end",
        default=DEFAULT_END,
        help=f"ISO end datetime in UTC (default: {DEFAULT_END}).",
    )
    parser.add_argument(
        "--step-minutes",
        type=float,
        default=DEFAULT_TIMESTEP_MIN,
        help=f"Timestep in minutes between samples (default: {DEFAULT_TIMESTEP_MIN}).",
    )
    parser.add_argument(
        "--output",
        default="tide_timeseries.csv",
        help="Output CSV path (default: tide_timeseries.csv).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cfg = resolve_tide_run_config(args)
    start = parse_iso_datetime(args.start)
    end = parse_iso_datetime(args.end)

    timestep_seconds = int(args.step_minutes * 60)
    if timestep_seconds <= 0:
        raise ValueError("Step must be positive.")

    handlers = pyfes.load_config(str(cfg.fes_config_path))
    ocean_tide = handlers["tide"]
    load_tide = handlers["radial"]

    lon, lat = determine_centroid(cfg, ocean_tide, load_tide)

    timestamps, tide_values = compute_tide_series((lon, lat), start, end, timestep_seconds, ocean_tide, load_tide)
    output_path = Path(args.output).expanduser().resolve()
    write_csv(output_path, timestamps, tide_values)

    print(f"Wrote {len(timestamps)} tide samples to {output_path}")
    if cfg.sitename:
        print(f"Site: {cfg.sitename}")
    print(f"Centroid used: lon={lon:.6f}, lat={lat:.6f}")
    print(f"Range: {start.isoformat()} to {end.isoformat()} | step = {timestep_seconds} s")


if __name__ == "__main__":
    main()
