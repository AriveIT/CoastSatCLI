import numpy as np
import skimage.filters as filters
import skimage.morphology as morphology
from scipy.signal import find_peaks

#########################
# Thresholds
#########################
def otsu(im, cloud_mask, ref_buffer):
    vec = apply_buffer_and_mask(im, cloud_mask, ref_buffer)
    return filters.threshold_otsu(vec)


def otsu_no_buffer(im, cloud_mask, ref_buffer):
    vec_idx = im.flatten()
    vec_mask = cloud_mask.flatten()

    vec = vec_idx[np.logical_and(~vec_mask, ~np.isnan(vec_idx))]
    return filters.threshold_otsu(vec)


def zero(im, cloud_mask, ref_buffer):
    return 0

# from Shoreliner
# finds minimum between the main peak on either side of the otsu threshold
def local_min_otsu(im, cloud_mask, ref_buffer):
    vec = apply_buffer_and_mask(im, cloud_mask, ref_buffer)
    n_bins = 256
    hist, bins = np.histogram(vec, n_bins, density=True)
    bins = np.array([bins[i]+(bins[i+1]-bins[i])/2 for i in range(len(bins)-1)])
    
    t_otsu = filters.threshold_otsu(vec, n_bins)

    peak_idx, properties = find_peaks(hist, height=(None, None))
    hist_peaks = bins[peak_idx]

    left_peaks = hist_peaks[hist_peaks < t_otsu]
    right_peaks = hist_peaks[hist_peaks >= t_otsu]

    left_heights = properties['peak_heights'][:len(left_peaks)]
    right_heights = properties['peak_heights'][-len(right_peaks):]

    if left_peaks.size==0:
        maxl = t_otsu 
    else:
        idx=np.argmax(left_heights)
        maxl = left_peaks[idx]

    if right_peaks.size==0:
        maxr = t_otsu
    else:
        idx=np.argmax(right_heights)
        maxr = right_peaks[idx]

    pdf_selected = hist[(bins>maxl)&(bins<maxr)]
    bins_selected = bins[(bins>maxl)&(bins<maxr)]
    if bins_selected.size==0:
        t_opti = t_otsu
    else:
        min_pdf = np.argmin(pdf_selected)
        t_opti = bins_selected[min_pdf]

    return t_opti

##########################
# Helpers
##########################
def apply_buffer_and_mask(im, cloud_mask, ref_buffer):

    # dilate ref_buffer by 5 pixels
    se = morphology.disk(5)
    im_ref_buffer_extra = morphology.binary_dilation(ref_buffer,se)

    # flatten images
    vec_buffer = im_ref_buffer_extra.flatten()
    vec_mask = cloud_mask.flatten()

    if len(im.shape) == 1:
        vec_idx = im
    elif len(im.shape) == 2:
        vec_idx = im.flatten()
    elif len(im.shape) == 3:
        vec_idx = im.reshape(-1, im.shape[-1])


    # keep pixels that are in the buffer and not in the cloud mask
    vec = vec_idx[np.logical_and(vec_buffer,~vec_mask)]

    nans = np.isnan(vec)
    if len(nans.shape) == 2:
        nans = np.logical_and.reduce(nans, axis=1)

    return vec[~nans]