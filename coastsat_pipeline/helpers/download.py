from __future__ import annotations

from typing import Any, Dict, Tuple

from coastsat import SDS_download, SDS_preprocess, SDS_tools


def download_images(global_settings: Dict[str, Any], download_filters) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Downloads images and returns metadata
    """
    return SDS_download.retrieve_images({**global_settings, **download_filters})
