import numpy as np
from shapely.geometry import LineString

from coastsat import SDS_shoreline, SDS_tools
import modified_coastsat


def get_points_along_ref_sl(ref_sl, delta):
    if not isinstance(ref_sl, list):
        line = LineString(ref_sl)
        all_points = get_points_along_single_sl(line, delta)
    else:
        all_points = []
        for sl in ref_sl:
            line = LineString(sl)
            points = get_points_along_single_sl(line, delta)
            all_points.append(points)
        all_points = np.concatenate(all_points)

    return np.array(all_points)

def get_points_along_single_sl(line, delta):
    distances = np.arange(0, line.length, delta)
    return [line.interpolate(distance).coords[0] for distance in distances] + [line.boundary.geoms[-1].coords[0]]

# returns coords for ll and ur vertices
# Inputs and outputs are in pixel space
def get_bounding_box_pxl(point, buffer):
    x_min = np.round(point[0] - buffer).astype(int)
    x_max = np.round(point[0] + buffer).astype(int)
    y_min = np.round(point[1] + buffer).astype(int)
    y_max = np.round(point[1] - buffer).astype(int)
    return (x_min, y_min), (x_max, y_max)


# isolate contour points that are closest to current reference point
def filter_contour_points(contours_pxl, coords_pxl, px_idx):
    cur = np.linalg.norm(contours_pxl - coords_pxl[px_idx], axis=1)
    m1 = np.linalg.norm(contours_pxl - coords_pxl[px_idx-1], axis=1) if px_idx > 0 else None
    p1 = np.linalg.norm(contours_pxl - coords_pxl[px_idx+1], axis=1) if px_idx < len(coords_pxl) - 1 else None

    if m1 is None: return contours_pxl[cur < p1]
    elif p1 is None: return contours_pxl[cur < m1]
    else: return contours_pxl[(cur < p1) & (cur < m1)]


# cuts mask down to image shape
def get_mask_bounds(ll_px, ur_px, im_ind_shape):
    y_max = np.min([ll_px[1], im_ind_shape[0]])
    y_min = np.max([ur_px[1], 0])
    x_max = np.min([ur_px[0], im_ind_shape[1]])
    x_min = np.max([ll_px[0], 0])
    return y_min, y_max, x_min, x_max


def local_sl_extraction(coords_px, im_ind, thresh_func, buffer_size, sds_data):
    final_contour = []
    for px_idx in range(len(coords_px)):
        ll_px, ur_px = get_bounding_box_pxl(coords_px[px_idx], buffer_size)

        # make mask
        mask_y_min, mask_y_max, mask_x_min, mask_x_max = get_mask_bounds(ll_px, ur_px, im_ind.shape)
        mask = np.zeros(im_ind.shape, dtype=bool)
        mask[mask_y_min:mask_y_max, mask_x_min:mask_x_max] = 1 # note: have to swap x and y for indexing
        mask &= sds_data["sl_buffer"]

        # prep contours
        threshold = thresh_func(im_ind, sds_data["cloud_mask"], mask)
        contours = modified_coastsat.find_wl_contours1(im_ind, sds_data["cloud_mask"], mask, threshold)
        contours = SDS_shoreline.process_shoreline(contours, sds_data["cloud_mask"], sds_data["im_nodata"],
                                        sds_data["georef"], sds_data["image_epsg"], sds_data["sds_settings"])
        contours_pxl = SDS_tools.convert_world2pix(contours, sds_data["georef"])

        # append contour points nearby to reference point (px_idx)
        good_contour_pxl = filter_contour_points(contours_pxl, coords_px, px_idx)
        if len(good_contour_pxl) > 0: final_contour.append(good_contour_pxl)

    final_contour = np.concatenate(final_contour)[:,[1,0]]
    return SDS_tools.convert_pix2world(final_contour, sds_data["georef"])