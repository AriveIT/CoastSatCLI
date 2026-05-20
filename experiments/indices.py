from thresholding import apply_buffer_and_mask
import numpy as np

BLUE_IDX, GREEN_IDX, RED_IDX, NIR_IDX, SWIR1_IDX, SWIR2_IDX = 0, 1, 2, 3, 4, 5

################
# Water Indices
################
def mndwi(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return (green - swir1) / (swir1 + green)

def ndwi(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return (green - nir) / (nir + green)

def awei_sh(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return blue + 2.5 * green - 1.5 * (nir + swir1) - 0.25 * swir2

def awei_ns(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return 4 * (green - swir1) - (0.25 * nir + 2.75 * swir2)

def scowi(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return blue + 2 * (green - nir) - 0.75 * swir1 - 0.5 * swir2

def wi2015(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return 1.7204 + 171 * green + 3 * red - 70 * nir - 45 * swir1 - 71 * swir2

def andwi(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    numerator = blue + green + red - nir - swir1 - swir2
    denom = blue + green + red + nir + swir1 + swir2
    return numerator / denom

def wri(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return (green + red) / (nir + swir1)

def ewi(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return (blue - red - nir) / (blue + red + nir)

def nwi(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    numerator = blue - nir - swir1 - swir2
    denom = blue + nir + swir1 + swir2
    return numerator / denom

def wi2019(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    numerator = 1.75 * green - red - 1.08 * swir1
    denom = green + swir1
    return numerator / denom

def tct_wetness(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return -(0.1511*blue + 0.1973*green + 0.3283*red + 0.3407*nir + 0.7117*swir1 + 0.4559*swir2)

def ddwi(sample):
    blue, green, red, nir, swir1, swir2 = unpack_bands(sample)
    return nir - green

################
# Ensemble
################
def ensemble1(sim_bands, ensemble_index_functions, cloud_mask, sl_buffer):
    ensemble_index = np.zeros(sim_bands.shape[:-1])
    for ind_func in ensemble_index_functions:
        im_flat = sim_bands.reshape(-1, sim_bands.shape[-1])
        index_im = ind_func(im_flat).reshape(sim_bands.shape[:-1])

        # standardize index values within buffer to [0, 1]
        vec = apply_buffer_and_mask(index_im, cloud_mask, sl_buffer)
        standardized_index_im = standardize(index_im, np.min(vec), np.max(vec))

        ensemble_index += standardized_index_im

    return ensemble_index / len(ensemble_index_functions)

def ensemble2(sim_bands, ensemble_index_functions, thresh_fn, cloud_mask, sl_buffer):
    ensemble_index = np.zeros(sim_bands.shape[:-1])
    for ind_func in ensemble_index_functions:
        
        im_flat = sim_bands.reshape(-1, sim_bands.shape[-1])
        index_im = ind_func(im_flat).reshape(sim_bands.shape[:-1])
        threshold = thresh_fn(index_im, cloud_mask, sl_buffer)

        ensemble_index += index_im < threshold
    return ensemble_index / len(ensemble_index_functions)

################
# Helpers
################
def unpack_bands(sample):
    return sample[:,[BLUE_IDX, GREEN_IDX, RED_IDX, NIR_IDX, SWIR1_IDX, SWIR2_IDX]].T

def standardize(data, minimum, maximum):
    return (data - minimum) / (maximum - minimum)

