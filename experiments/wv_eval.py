import modified_coastsat
from coastsat import SDS_shoreline, SDS_tools
import wv_utils as wv
import wv_eval_plotting as wvep
import modified_coastsat
import metrics as m
from indices import *
from thresholding import *
import local_sl_extraction as lse
import spectral_unmixing as su

from scipy.ndimage import median_filter
import numpy as np
from tqdm import tqdm
from itertools import product
import matplotlib.pyplot as plt

def extract_shoreline(sim_bands, index_fn, thresh_fn, sds_data):
    im_flat = sim_bands.reshape(-1, sim_bands.shape[-1])
    index = index_fn(im_flat)
    threshold = thresh_fn(index, sds_data["cloud_mask"], sds_data["sl_buffer"])
    return get_contours(index.reshape(sim_bands.shape[:-1]), threshold, sds_data)

def smooth_bands(bands, kernel_size=3):
    return median_filter(bands, kernel_size)

def get_contours(index, threshold, sds_data):
    contours = modified_coastsat.find_wl_contours1(index, sds_data["cloud_mask"], sds_data["sl_buffer"], threshold)
    return SDS_shoreline.process_shoreline(contours, sds_data["cloud_mask"], sds_data["im_nodata"],
                                    sds_data["georef"], sds_data["image_epsg"], sds_data["sds_settings"])
    
def evaluate_methods(
        index_functions,
        threshold_functions,
        sim_bands,
        ref_sl_points,
        transects,
        collider_settings,
        sds_data,
        ensemble_index_functions=[],
        binarize=False,
        smooth=False,
        lse1=False,
        lse2=False,
        le_buffer=30,
        le_spacing=50,
        zones=None,
        optimal_thresholds=False,
        spectral_unmixing=False):
    
    if ensemble1 in index_functions or ensemble2 in index_functions:
        assert ensemble_index_functions
    assert not (lse1 and lse2)

    info = {}
    if smooth:
        sim_bands = smooth_bands(sim_bands)
    if lse1 or lse2:
        coords_pxl = SDS_tools.convert_world2pix(ref_sl_points[::int(le_spacing // 0.5)], sds_data["georef"])

    thresholds = []
    shoreline_metric = []
    transect_metric = []
    for index_fn, thresh_fn in tqdm(product(index_functions, threshold_functions)):
            # prepare shoreline contours
            im_flat = sim_bands.reshape(-1, sim_bands.shape[-1])

            # compute index
            if index_fn == ensemble1:
                index = ensemble1(sim_bands, ensemble_index_functions, thresh_fn, sds_data["cloud_mask"], sds_data["sl_buffer"]).flatten()
            elif index_fn == ensemble2:
                index = ensemble2(sim_bands, ensemble_index_functions, thresh_fn, sds_data["cloud_mask"], sds_data["sl_buffer"]).flatten()
            elif index_fn == "spectral_unmixing_1":
                im_ind = ensemble2(sim_bands, ensemble_index_functions, otsu, sds_data["cloud_mask"], sds_data["sl_buffer"])
                index = su.spectral_unmixing_1(sim_bands, im_ind, sds_data)
            elif index_fn == "spectral_unmixing_2":
                im_ind = ensemble2(sim_bands, ensemble_index_functions, otsu, sds_data["cloud_mask"], sds_data["sl_buffer"])
                index = su.spectral_unmixing_2(sim_bands, im_ind, sds_data)
                index[index < 0.6] = np.nan
                
            else:
                index = index_fn(im_flat)
            index = index.reshape(sim_bands.shape[:-1])
            
            # if spectral unmixing
            if spectral_unmixing:
                index = su.spectral_unmixing_1(sim_bands, index, sds_data)

            # shoreline extraction (index, threshold, contouring)
            if lse1:
                contours, ts = lse.local_sl_extraction_1(coords_pxl, index, thresh_fn, le_buffer, sds_data, binarize)
            elif lse2:
                if zones is None:
                    zones = lse.get_zone_indicators(index, coords_pxl, sds_data, buffer_size=50, p_thresh=0.05)
                masks = lse.get_masks_from_zone_indicators(zones, coords_pxl, sim_bands.shape[:-1])
                contours, ts = lse.local_sl_extraction_2(masks, thresh_fn, index, zones, coords_pxl, sds_data)
                thresholds.append(ts)

            elif optimal_thresholds:
                contours, t = get_optimal_threshold(index, ref_sl_points, sds_data)
                thresholds.append(t)

            else:
                t = thresh_fn(index, sds_data["cloud_mask"], sds_data["sl_buffer"])
                if binarize:
                    index = index > t
                    t = 0.5
                contours = get_contours(index.reshape(sim_bands.shape[:-1]), t, sds_data)
                thresholds.append(t)
            

            # compute metrics
            shoreline_dist = m.get_nearest_distance(ref_sl_points, contours)
            transect_dist, _ = m.get_median_distances(transects, ref_sl_points, contours, collider_settings)
            shoreline_metric.append(shoreline_dist)
            transect_metric.append(transect_dist)

    index_fn_names = [index_fn if type(index_fn) == str else index_fn.__name__ for index_fn in index_functions]
    methods = np.array([index_fn_name + "__" + thresh_fn.__name__ for index_fn_name in index_fn_names for thresh_fn in threshold_functions])
    shoreline_metric = np.array(shoreline_metric)
    transect_metric = np.array(transect_metric)
    info["thresholds"] = thresholds
    return shoreline_metric, transect_metric, methods, info


def get_optimal_threshold(index_im, ref_sl_points, sds_data, n_steps=200, outlier_idx=None):
    min_index = np.nanmin(index_im[sds_data["sl_buffer"]])
    max_index = np.nanmax(index_im[sds_data["sl_buffer"]])
    best_t = min_index
    best_c = None
    min_error = np.inf
    thresholds = np.linspace(min_index, max_index, n_steps)

    for t in thresholds:

        contours = get_contours(index_im, t, sds_data)
        shoreline_dist = m.get_nearest_distance(ref_sl_points, contours)
        if outlier_idx is not None: shoreline_dist = shoreline_dist[~outlier_idx]
        mean_dist = np.nanmean(shoreline_dist)
        if mean_dist < min_error:
            best_t = t
            best_c = contours
            min_error = mean_dist
            # print(f"t = {t:.3f}: {mean_dist:.3f}")
    
    return best_c, best_t


####################
# Outputting Metrics
####################
def organize_metrics(shoreline_metric, transect_metric, methods, outlier_idx=None):
    entries = []
    outlier_idx = (np.sum(shoreline_metric > 25, axis=0)) > 10 if (outlier_idx is None) else outlier_idx
    for i in range(len(methods)):
        no_outlier_dist = shoreline_metric[i, ~outlier_idx]

        # save
        entries.append(dict(
            method=methods[i],
            sl_mean=np.mean(no_outlier_dist),
            sl_mean_all=np.mean(shoreline_metric[i]),
            sl_std=np.std(shoreline_metric[i]),
            sl_n_outliers=len(shoreline_metric[i, shoreline_metric[i] > 25]),
            t_mean=np.nanmean(transect_metric[i]),
            t_std=np.nanstd(transect_metric[i]),
            t_mae=np.nanmean(np.abs(transect_metric[i]))
        ))
    return entries, outlier_idx

def print_metrics(entries, sort_variable=None, file=None, first_col_width=35, col_width=12, section_buffer=3):
    if sort_variable:
        entries = sorted(entries, key=lambda entry: float('inf') if np.isnan(entry[sort_variable]) else entry[sort_variable])

    # headers
    print(f"{f'Sorted by {sort_variable}'.ljust(first_col_width)} {'sl_mean'.ljust(col_width)} {'sl_mean_all'.ljust(col_width)} {'sl_std'.ljust(col_width)} {'sl_outlier'.ljust(col_width+section_buffer)}" 
        f"{'t_mean'.ljust(col_width)} {'t_std'.ljust(col_width)} {'t_mae'.ljust(col_width)}", file=file)
    
    # body
    for entry in entries:
        mean_string = f"{entry['sl_mean']:.3f}".ljust(col_width)
        all_mean_string = f"{entry['sl_mean_all']:.3f}".ljust(col_width)
        std_string = f"{entry['sl_std']:.3f}".ljust(col_width)
        outlier_string = f"{entry['sl_n_outliers']}".ljust(col_width)

        t_mean_string = f"{entry['t_mean']:.3f}".ljust(col_width)
        t_std_string = f"{entry['t_std']:.3f}".ljust(col_width)
        t_mae_string = f"{entry['t_mae']:.3f}".ljust(col_width)

        print(f"{(entry['method'] + ':').ljust(first_col_width)} {mean_string} {all_mean_string} {std_string} {outlier_string}   "
            f"{t_mean_string} {t_std_string} {t_mae_string}", file=file)
