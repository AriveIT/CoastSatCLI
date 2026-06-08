import numpy as np
from thresholding import otsu, apply_buffer_and_mask
from scipy.signal import find_peaks
import skimage.filters as filters


# returns value of greatest peak left (on water side) of otsu threshold
def get_threshold(im_ind, sds_data):
    vec = apply_buffer_and_mask(im_ind, sds_data["cloud_mask"], sds_data["sl_buffer"])
    n_bins = 256
    hist, bins = np.histogram(vec, n_bins, density=True)
    bins = np.array([bins[i]+(bins[i+1]-bins[i])/2 for i in range(len(bins)-1)])
    t_otsu = filters.threshold_otsu(vec, n_bins)

    peak_idx, properties = find_peaks(hist, height=(None, None))
    hist_peaks = bins[peak_idx]
    left_peaks = hist_peaks[hist_peaks < t_otsu]
    left_heights = properties['peak_heights'][:len(left_peaks)]

    if left_peaks.size==0:
        maxl = t_otsu 
    else:
        idx=np.argmax(left_heights)
        maxl = left_peaks[idx]
    
    return maxl


def get_candidate_signature(im_ind, sim_bands, sds_data):
    thresh = get_threshold(im_ind, sds_data)
    water_pixels = sim_bands[sds_data["sl_buffer"] & (im_ind < thresh)]
    candidate_signature = np.mean(water_pixels, axis=0)
    return candidate_signature


# cap projection coefficients at 1
# don't want to remove a spectral signature with magnitude larger than the candidate signature
# (the excess is likely not due to water's signature)
def get_capped_proj_coefs(sim_bands, candidate_signature):
    proj_coefs = (np.dot(sim_bands, candidate_signature)) / np.dot(candidate_signature, candidate_signature)
    return np.fmin(proj_coefs, np.ones_like(proj_coefs))


# what percentage of signature does NOT match water signature
def get_signature_percentages(sim_bands, projections):
    total_norms = np.linalg.norm(sim_bands.reshape(-1, 6), axis=1)
    after_norms = np.linalg.norm(sim_bands.reshape(-1, 6) - projections, axis=1)
    return after_norms / total_norms


def spectral_unmixing_1(sim_bands, im_ind, sds_data):
    candidate_signature = get_candidate_signature(im_ind, sim_bands, sds_data)
    proj_coefs = get_capped_proj_coefs(sim_bands, candidate_signature)
    projections = np.matmul((proj_coefs).reshape(-1, 1), candidate_signature.reshape(1, -1))
    return get_signature_percentages(sim_bands, projections)