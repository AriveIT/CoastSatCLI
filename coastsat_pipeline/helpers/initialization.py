from __future__ import annotations

from typing import Any, Dict, Tuple

from coastsat import SDS_download, SDS_preprocess, SDS_tools

DEFAULT_DATES = ["1984-01-01", "2025-01-01"]
DEFAULT_SAT_LIST = ["L5", "L7", "L8", "L9"]


def prepare_initial_settings(raw_config: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Build the CoastSat inputs/settings structures using the same logic as the legacy
    initial_settings function. Returns (inputs, settings, metadata).
    """
    inputs = _build_inputs_dict(raw_config)
    metadata = _retrieve_metadata(inputs)
    settings = _build_analysis_settings(raw_config, inputs)
    return inputs, settings, metadata


def _build_inputs_dict(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    inputs_section = raw_config["inputs"]

    polygon = SDS_tools.polygon_from_kml(inputs_section["aoi_path"])
    polygon = SDS_tools.smallest_rectangle(polygon)

    dates = raw_config.get("dates", DEFAULT_DATES)
    sat_list = raw_config.get("sat_list", DEFAULT_SAT_LIST)

    return {
        "polygon": polygon,
        "dates": dates,
        "sat_list": sat_list,
        "sitename": inputs_section["sitename"],
        "filepath": raw_config["output_dir"],
        "reference_geojson": inputs_section["reference_shoreline"],
        "transect_geojson": inputs_section["transects"],
        "fes_config": inputs_section.get("fes_config"),
    }


def _retrieve_metadata(inputs: Dict[str, Any]) -> Dict[str, Any]:
    metadata = SDS_download.retrieve_images(inputs)
    return SDS_download.get_metadata(inputs)


def _build_analysis_settings(raw_config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    settings = {
        "cloud_thresh": raw_config.get("cloud_thresh", 0.2),
        "dist_clouds": raw_config.get("dist_clouds", 50),
        "output_epsg": raw_config["output_epsg"],
        "check_detection": raw_config.get("check_detection", False),
        "adjust_detection": raw_config.get("adjust_detection", False),
        "save_figure": raw_config.get("save_figure", True),
        "min_beach_area": raw_config.get("min_beach_area", 500),
        "min_length_sl": raw_config.get("min_length_sl", 250),
        "cloud_mask_issue": raw_config.get("cloud_mask_issue", False),
        "sand_color": raw_config.get("sand_color", "default"),
        "pan_off": raw_config.get("pan_off", False),
        "s2cloudless_prob": raw_config.get("s2cloudless_prob", 20),
        "inputs": inputs,
    }

    if raw_config.get("tide_filter"):
        settings["tide_filter"] = raw_config["tide_filter"]

    if "imagery_options" in raw_config:
        settings["imagery_options"] = raw_config["imagery_options"]

    settings["reference_shoreline"] = SDS_preprocess.get_reference_sl_from_geojson(
        inputs["reference_geojson"],
        settings["output_epsg"],
    )
    settings["max_dist_ref"] = raw_config.get("max_dist_ref", 500)

    return settings
