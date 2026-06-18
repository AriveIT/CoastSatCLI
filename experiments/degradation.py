import numpy as np
import skgstat
from scipy.signal import convolve2d
from scipy.stats import multivariate_normal
import wv_utils as wv

######################
# Gaussian Degradation
######################
def get_sd_from_fwfm(pixel_width):
    return pixel_width / (2 * np.sqrt(2 * np.log(2)))

def get_adj_res(target_res, source_res):
    div = int(target_res // source_res)
    offset = np.argmin([abs(div * source_res - target_res), abs((div + 1) * source_res - target_res)]).astype(int)
    mul = div + offset
    adj_res = source_res * mul
    return adj_res, mul

def get_gaussian_kernel(radius, variance, res):
    width = int(radius * 2)
    locs = (np.stack(np.meshgrid(np.arange(width), np.arange(width)), axis=2) - (radius - 0.5)) * res

    mvn = multivariate_normal([0, 0], [[variance, 0], [0, variance]])
    kernel = mvn.pdf(locs.reshape(-1,2)).reshape(width, width)
    kernel /= np.sum(kernel) # make it sum to 1

    return kernel

# wastes some flops, but it's simple and readable
def strided_convolution(im, kernel, stride):
    if len(im.shape) == 3: output = np.stack([convolve2d(im[:,:,i], kernel, mode='valid') for i in range(im.shape[-1])], axis=2)
    elif len(im.shape) == 2: output = convolve2d(im, kernel, mode='valid')
    return output[::stride,::stride]

def gaussian_degradation(bands, source_res, target_res, kernel_radius):
    adj_res, mul = get_adj_res(target_res, source_res)
    sd = get_sd_from_fwfm(adj_res)
    kernel = get_gaussian_kernel(kernel_radius, sd**2, source_res)
    output = strided_convolution(bands, kernel, stride=mul)
    return output, adj_res, mul

def calc_offsets(source_res, kernel_radius, adj_res):
    x_offset = kernel_radius * source_res
    y_offset = -x_offset
    return x_offset, y_offset

def save_gaus_deg_tif(filename, bands, source_res, kernel_radius, adj_res, in_proj, in_gt):
    x_offset, y_offset = calc_offsets(source_res, kernel_radius, adj_res)
    ux = in_gt[0] + x_offset
    uy = in_gt[3] + y_offset

    gt = (ux, adj_res, 0.0, uy, 0.0, -adj_res)
    wv.write_geotiff(filename, bands, proj=in_proj, gt=gt)


#############################
# SNR Estimation and Matching
#############################
# SNR estimation
def directional_semivariogram_snr(bands, dir=None, estimator='cressie', n_lags=20, maxlag=10, model='gaussian'):
    x, y = np.meshgrid(np.arange(bands.shape[0]), np.arange(bands.shape[1]))
    if dir == "row": y *= 1000
    if dir == "col": x *= 1000
    coords = np.stack([x, y], axis=2).reshape(-1, 2)

    signal = []
    noise_std = []
    for i in range(bands.shape[-1]):
        values = bands[:,:,i].flatten()
        valid_idx = ~np.isnan(values) & ~np.isinf(values)
        V = skgstat.Variogram(coords[valid_idx], values[valid_idx], estimator=estimator, n_lags=n_lags, maxlag=maxlag, model=model, use_nugget=True)
        # print(np.mean(values[valid_idx]),  np.sqrt(V.parameters[2]))
        # snr.append(np.mean(values[valid_idx]) / np.sqrt(V.parameters[2]))
        signal.append(np.mean(values[valid_idx]))
        noise_std.append(np.sqrt(V.parameters[2]))

    signal = np.array(signal)
    noise_std = np.array(noise_std)
    return signal / noise_std, signal, noise_std

# add noise to each pixel (and band) considering that pixel's amplitude
def match_snr(source_bands, source_snr, target_snr):

    # calculate noise sd from amplitudes and snr
    source_std = source_bands / source_snr
    target_std = source_bands / target_snr

    # calculate noise for bands where source_snr > target_snr
    valid_idx = source_snr - target_snr > 0
    add_std = np.zeros(source_bands.shape)
    add_std[:,:,valid_idx] = np.sqrt(target_std[:,:,valid_idx] ** 2 - source_std[:,:,valid_idx] ** 2)

    # return noise
    noise = np.random.randn(*source_bands.shape) * add_std
    return np.clip(source_bands + noise, 0, 1)