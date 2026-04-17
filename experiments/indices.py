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

################
# Helpers
################
def unpack_bands(sample):
    return sample[:,[BLUE_IDX, GREEN_IDX, RED_IDX, NIR_IDX, SWIR1_IDX, SWIR2_IDX]].T

