import numpy as np
from shapely.geometry import LineString
from scipy.spatial import KDTree
from scipy.stats import ks_2samp

from coastsat import SDS_shoreline, SDS_tools
import modified_coastsat
import wv_utils as wv
import spectral_unmixing as su


###############################
# local_sl_extraction Take 2
###############################

def local_sl_extraction_2(masks, thresh_func, im_ind, zone_indicators, coords_pxl, sds_data):
    thresholds = []
    final_contour = []

    ref_tree = KDTree(coords_pxl)
    mask_bin = masks.astype(bool)
    for i, mask in enumerate(mask_bin):
        # prep contours
        threshold = thresh_func(im_ind, sds_data["cloud_mask"], mask)
        thresholds.append(threshold)
        contours = modified_coastsat.find_wl_contours1(im_ind, sds_data["cloud_mask"], mask, threshold)

        contours = SDS_shoreline.process_shoreline(contours, sds_data["cloud_mask"], sds_data["im_nodata"],
                                        sds_data["georef"], sds_data["image_epsg"], sds_data["sds_settings"])
        contours_pxl = SDS_tools.convert_world2pix(contours, sds_data["georef"])
        
        contours_pxl = filter_contour_points_2(contours_pxl, ref_tree, zone_indicators, cur_zone=i)
        if len(contours_pxl) > 0: final_contour.append(contours_pxl)
        
        
    final_contour_pxl = np.concatenate(final_contour)[:,[1,0]]
    final_contour_world = SDS_tools.convert_pix2world(final_contour_pxl, sds_data["georef"])

    return final_contour_world, thresholds

def get_zone_indicators(im_ind, coords_pxl, sds_data, buffer_size=50, p_thresh=0.05):
    p_values = []
    # masks = []

    prev_mask = get_mask(coords_pxl[0], buffer_size, im_ind.shape, sds_data["sl_buffer"])
    prev_ind_sample = im_ind[prev_mask]
    for px_idx in range(len(coords_pxl)):

        # make mask
        mask = get_mask(coords_pxl[px_idx], buffer_size, im_ind.shape, sds_data["sl_buffer"])
        ind_sample = im_ind[mask]
        # prev_ind_sample = im_ind[prev_mask]

        res = ks_2samp(ind_sample, prev_ind_sample, axis=None, nan_policy="omit")
        p_values.append(res.pvalue)

        # if res.pvalue >= p_thresh:
        #     prev_mask |= mask
        # else:
        #     masks.append(prev_mask)
        #     prev_mask = mask
        
        prev_mask = mask
        prev_ind_sample = ind_sample
    p_values = np.array(p_values)
    
    # merge degenerate zones (single point) to previous zone
    zone_indicators = p_values < p_thresh
    degen_idx = np.where(zone_indicators[1:] & zone_indicators[:-1])[0]
    zone_indicators[degen_idx] = 0

    return np.cumsum(zone_indicators)

def get_masks_from_zone_indicators(zones, coords_pxl, im_shape):
    masks = []

    for idx in range(zones[-1] + 1):
        zone_coords_pxl = coords_pxl[zones == idx,:]
        mask = wv.create_shoreline_buffer(im_shape, [zone_coords_pxl], 10, skip_degen=False)
        masks.append(mask)
    return np.stack(masks)

# this function is not used but I thought it was kinda fun so I didn't want to delete it
def partition_buffer_into_zones(p_values, p_thresh, sl_buffer, coords_pxl):
    zones = np.cumsum(p_values < p_thresh) # shoreline point coords_pxl[i] belongs to zone[i]
    n_zones = zones[-1] + 1
    masks = np.zeros((n_zones, *sl_buffer.shape))
    ref_tree = KDTree(coords_pxl)

    buffer_idx = np.transpose(np.nonzero(sl_buffer))[:,[1,0]] # positions of each pixel inside sl_buffer
    query_idx = ref_tree.query(buffer_idx)[1] # nearest shoreline point to each pixel inside sl_buffer
    zone_idx = zones[query_idx] # get zones of points closest to each pixel
    masks[zone_idx, buffer_idx[:,1], buffer_idx[:,0]] = 1 # set zone masks where buffer pixels are nearest to points in zone

# make sure points are in right zone
def filter_contour_points_2(contours_pxl, ref_tree, zone_indicators, cur_zone):
    _, idx = ref_tree.query(contours_pxl)
    zones = zone_indicators[idx]
    return contours_pxl[zones == cur_zone]

# for custom spectral unmixing
def local_sl_extraction_su(sim_bands, masks, thresh_func, sds_data, im_ind=None, percentages=None):
    thresholds = []
    final_contour = []
    assert (im_ind is None) != (percentages is None) # only one of them are filled (for clarity of intention)

    for mask in masks:

        if percentages is None:
            percentages = su.spectral_unmixing_1(sim_bands, im_ind, mask).reshape(192, 360)
        threshold = thresh_func(percentages, sds_data["cloud_mask"], mask)
        thresholds.append(threshold)
        contours = modified_coastsat.find_wl_contours1(percentages, sds_data["cloud_mask"], mask, threshold)

        contours = SDS_shoreline.process_shoreline(contours, sds_data["cloud_mask"], sds_data["im_nodata"],
                                        sds_data["georef"], sds_data["image_epsg"], sds_data["sds_settings"])
        contours_pxl = SDS_tools.convert_world2pix(contours, sds_data["georef"])
        if len(contours_pxl) > 0: final_contour.append(contours_pxl)
        
    final_contour_pxl = np.concatenate(final_contour)[:,[1,0]]
    final_contour_world = SDS_tools.convert_pix2world(final_contour_pxl, sds_data["georef"])

    return final_contour_world, thresholds

#############################
# local_sl_extraction Take 1
##############################
def local_sl_extraction_1(coords_pxl, im_ind, thresh_func, buffer_size, sds_data, binarize, mask_type="square", n_buffer=None, coords_kdtree=None):
    assert mask_type in ["square", "shoreline", "cluster"]
    assert (mask_type == "square") or n_buffer
    assert (mask_type != "cluster") or coords_kdtree

    final_contour = []
    thresholds = []
    ref_tree = KDTree(coords_pxl)
    for px_idx in range(len(coords_pxl)):

        # make mask
        if mask_type == "shoreline":
            mask = get_mask_along_shoreline(coords_pxl, px_idx, buffer_size, n_buffer, im_ind.shape)
        elif mask_type == "square":
            mask = get_mask(coords_pxl[px_idx], buffer_size, im_ind.shape, sds_data["sl_buffer"])

        # prep contours
        threshold = thresh_func(im_ind, sds_data["cloud_mask"], mask)
        thresholds.append(threshold)
        if binarize:
            im_ind = im_ind > threshold
            threshold = 0.5
        contours = modified_coastsat.find_wl_contours1(im_ind, sds_data["cloud_mask"], mask, threshold)

        contours = SDS_shoreline.process_shoreline(contours, sds_data["cloud_mask"], sds_data["im_nodata"],
                                        sds_data["georef"], sds_data["image_epsg"], sds_data["sds_settings"])
        contours_pxl = SDS_tools.convert_world2pix(contours, sds_data["georef"])

        # append contour points nearby to reference point (px_idx)
        good_contour_pxl = filter_contour_points(contours_pxl, ref_tree, px_idx)
        if len(good_contour_pxl) > 0: final_contour.append(good_contour_pxl)

    final_contour = np.concatenate(final_contour)[:,[1,0]]
    return SDS_tools.convert_pix2world(final_contour, sds_data["georef"]), thresholds


# isolate contour points that are closest to current reference point
def filter_contour_points(contours_pxl, ref_tree, px_idx):
    _, idx = ref_tree.query(contours_pxl)
    return contours_pxl[idx == px_idx]


#####################
# Helpers
#####################
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

# cuts mask down to image shape
def get_mask_bounds(ll_px, ur_px, im_ind_shape):
    y_max = np.min([ll_px[1], im_ind_shape[0]])
    y_min = np.max([ur_px[1], 0])
    x_max = np.min([ur_px[0], im_ind_shape[1]])
    x_min = np.max([ll_px[0], 0])
    return y_min, y_max, x_min, x_max

def get_mask(coord_pxl, buffer_size, im_ind_shape, sl_buffer):
    ll_px, ur_px = get_bounding_box_pxl(coord_pxl, buffer_size)
    mask_y_min, mask_y_max, mask_x_min, mask_x_max = get_mask_bounds(ll_px, ur_px, im_ind_shape)
    mask = np.zeros(im_ind_shape, dtype=bool)
    mask[mask_y_min:mask_y_max, mask_x_min:mask_x_max] = 1 # note: have to swap x and y for indexing
    mask &= sl_buffer
    return mask

def get_mask_along_shoreline(coords_pxls, pxl_idx, buffer_size, n_buffer, im_shape):
    left = max(pxl_idx - n_buffer, 0)
    right = min(pxl_idx + n_buffer, len(coords_pxls) - 1)
    return wv.create_shoreline_buffer(im_shape, [coords_pxls[left:right]], buffer_size, skip_degen=False)

def get_nearby_mask(coords_pxls, pxl_idx, coords_kdtree, n_buffer, im_shape, buffer_size):
    _, idx = coords_kdtree.query(coords_pxls[pxl_idx], k=n_buffer)
    return wv.create_shoreline_buffer(im_shape, [coords_pxls[idx]], buffer_size, skip_degen=False)