import modified_coastsat
from coastsat import SDS_shoreline
import wv_utils as wv
import wv_eval_plotting as wvep
import modified_coastsat
import metrics as m
from indices import *
from thresholding import *

from scipy.ndimage import median_filter
import numpy as np

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
    
def evaluate_methods(index_functions, threshold_functions, sim_bands, ref_sl_points, transects, collider_settings, sds_data, ensemble_index_functions=[], binarize=False, smooth=False):
    if ensemble1 in index_functions or ensemble2 in index_functions:
        assert ensemble_index_functions

    if smooth:
        sim_bands = smooth_bands(sim_bands)

    shoreline_metric = []
    transect_metric = []
    for index_fn in index_functions:
        for thresh_fn in threshold_functions:
            # prepare shoreline contours
            im_flat = sim_bands.reshape(-1, sim_bands.shape[-1])

            # compute index
            if index_fn == ensemble1:
                index = ensemble1(sim_bands, ensemble_index_functions, sds_data["cloud_mask"], sds_data["sl_buffer"]).flatten()
            elif index_fn == ensemble2:
                index = ensemble2(sim_bands, ensemble_index_functions, thresh_fn, sds_data["cloud_mask"], sds_data["sl_buffer"]).flatten()
            else:
                index = index_fn(im_flat)
            
            threshold = thresh_fn(index, sds_data["cloud_mask"], sds_data["sl_buffer"])

            if binarize:
                index = index > threshold
                threshold = 0.5

            contours = get_contours(index.reshape(sim_bands.shape[:-1]), threshold, sds_data)
            
            # compute metrics
            shoreline_dist = m.get_nearest_distance(ref_sl_points, contours)
            transect_dist, _ = m.get_median_distances(transects, ref_sl_points, contours, collider_settings)
            shoreline_metric.append(shoreline_dist)
            transect_metric.append(transect_dist)

    methods = np.array([index_fn.__name__ + "__" + thresh_fn.__name__ for index_fn in index_functions for thresh_fn in threshold_functions])
    shoreline_metric = np.array(shoreline_metric)
    transect_metric = np.array(transect_metric)

    return shoreline_metric, transect_metric, methods

def organize_metrics(shoreline_metric, transect_metric, methods):
    entries = []
    for i in range(len(methods)):
        # remove outliers from shoreline transect
        outlier_idx = m.get_outlier_idx(shoreline_metric[i], (0, 25))
        no_outlier_dist = np.delete(shoreline_metric[i], outlier_idx)

        # save
        entries.append(dict(
            method=methods[i],
            sl_mean=np.mean(no_outlier_dist),
            sl_std=np.std(no_outlier_dist),
            sl_n_outliers=len(outlier_idx),
            t_mean=np.nanmean(transect_metric[i]),
            t_std=np.nanstd(transect_metric[i]),
            t_mae=np.nanmean(np.abs(transect_metric[i]))
        ))
    return entries

def print_metrics(entries, sort_variable=None, first_col_width=35, col_width=10, section_buffer=3):
    if sort_variable:
        entries = sorted(entries, key=lambda entry: float('inf') if np.isnan(entry[sort_variable]) else entry[sort_variable])

    print(f"{''.ljust(first_col_width)} {'sl_mean'.ljust(col_width)} {'sl_std'.ljust(col_width)} {'sl_outlier'.ljust(col_width+section_buffer)}" 
        f"{'t_mean'.ljust(col_width)} {'t_std'.ljust(col_width)} {'t_mae'.ljust(col_width)}")
    for entry in entries:
        mean_string = f"{entry['sl_mean']:.3f}".ljust(col_width)
        std_string = f"{entry['sl_std']:.3f}".ljust(col_width)
        outlier_string = f"{entry['sl_n_outliers']}".ljust(col_width)

        t_mean_string = f"{entry['t_mean']:.3f}".ljust(col_width)
        t_std_string = f"{entry['t_std']:.3f}".ljust(col_width)
        t_mae_string = f"{entry['t_mae']:.3f}".ljust(col_width)

        print(f"{(entry['method'] + ':').ljust(first_col_width)} {mean_string} {std_string} {outlier_string}   "
            f"{t_mean_string} {t_std_string} {t_mae_string}")


