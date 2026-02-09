from __future__ import annotations

from typing import Any, Dict, Tuple

from coastsat import SDS_download, SDS_preprocess, SDS_tools


def prepare_initial_settings(raw_config: Dict[str, Any], download_filters, analysis_settings) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Build the CoastSat inputs/settings structures using the same logic as the legacy
    initial_settings function. Returns (inputs, settings, metadata).
    """
    inputs = _build_inputs_dict(raw_config, download_filters)
    metadata = _retrieve_metadata(inputs)
    settings = _build_analysis_settings(raw_config, inputs, analysis_settings)
    return inputs, settings, metadata


def _build_inputs_dict(raw_config: Dict[str, Any], download_filters) -> Dict[str, Any]:
    inputs_section = raw_config["inputs"]

    polygon = SDS_tools.polygon_from_kml(inputs_section["aoi_path"])
    polygon = SDS_tools.smallest_rectangle(polygon)

    inputs = {
        "polygon": polygon,
        "sitename": inputs_section["sitename"],
        "filepath": raw_config["output_dir"],
        "reference_geojson": inputs_section["reference_shoreline"],
        "transect_geojson": inputs_section["transects"],
        "fes_config": inputs_section.get("fes_config"),
        "tide_csv_path": inputs_section.get("tide_csv_path")
    }
    inputs.update(download_filters)

    return inputs


def _retrieve_metadata(inputs: Dict[str, Any]) -> Dict[str, Any]:
    metadata = SDS_download.retrieve_images(inputs)
    return SDS_download.get_metadata(inputs)


# add other settings to the user defined parameters listed in analysis_settings
def _build_analysis_settings(raw_config: Dict[str, Any], inputs: Dict[str, Any], analysis_settings: Dict[str, Any]) -> Dict[str, Any]:
    settings = {
        "inputs": inputs,
        "output_epsg": raw_config["output_epsg"],
    }
    settings.update(analysis_settings)

    if raw_config.get("tide_filter"):
        settings["tide_filter"] = raw_config["tide_filter"]

    if "imagery_options" in raw_config:
        settings["imagery_options"] = raw_config["imagery_options"]

    settings["reference_shoreline"] = SDS_preprocess.get_reference_sl_from_geojson(
        inputs["reference_geojson"],
        settings["output_epsg"],
    )

    return settings
