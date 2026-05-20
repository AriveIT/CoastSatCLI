import os, sys
import numpy as np
import matplotlib.pyplot as plt
import shapely
import geopandas as gpd
from shapely.geometry import LineString
from rasterio.features import rasterize

# coastsat modules
sys.path.insert(0, os.pardir)
from coastsat import SDS_download, SDS_preprocess, SDS_shoreline, SDS_tools, SDS_classify, SDS_transects
from osgeo import gdal
gdal.UseExceptions()

import modified_coastsat

##########################
# Initialization
##########################
def load_tif(fn, is_swir=False):
    im = gdal.Open(fn, gdal.GA_ReadOnly)
    n_bands = im.RasterCount

    if n_bands > 1:
        bands = np.stack([im.GetRasterBand(k+1).ReadAsArray() for k in range(n_bands)], 2)
    else:
        bands = im.GetRasterBand(1).ReadAsArray()
    
    norm_factor = 16384 if is_swir else 2048

    im = None
    return bands / norm_factor


def load_sim_tif(fn):
    im = gdal.Open(fn, gdal.GA_ReadOnly)
    n_bands = im.RasterCount
    bands = np.stack([im.GetRasterBand(k+1).ReadAsArray() for k in range(n_bands)], 2)
    
    im = None
    return bands


def load_ref_sl(path):
    ref_sl_gdf = gpd.read_file(path)

    ref_sl_list = []
    for line in ref_sl_gdf.geometry:
        coords = np.array(line.coords)
        
        ref_sl_list.append(coords)

    return ref_sl_list

def ref_sl_to_pxl(ref_sl_list, georef):
    ref_sl_pxl_list = []
    for ref_sl in ref_sl_list:
        ref_sl_pxl_list.append(SDS_tools.convert_world2pix(ref_sl, georef))

    return ref_sl_pxl_list 

##########################
# EDA
##########################
def plot_hists(bands, n_bands):
    n_row, n_col = 2, 4
    fig, axs = plt.subplots(n_row, n_col, figsize=(12, 8), tight_layout=True)
    axs = axs.ravel()

    for i in range(n_bands):
        axs[i].hist(bands[:,:,i].ravel(), log=True)
        axs[i].set_title(f"Band {i}, Max: {np.max(bands[:,:,i].ravel())}")


def plot_bands(bands, n_bands, cloud_mask, band_names=None):
    band_names = band_names or [
        "Coastal Blue",
        "Blue",
        "Green",
        "Yellow",
        "Red",
        "Red Edge",
        "NIR1",
        "NIR2"
    ]
    
    n_row = 2
    n_col = 4
    fig, axs = plt.subplots(n_row, n_col, figsize=(12, 8), tight_layout=True)
    axs = axs.ravel()

    for i in range(n_bands):
        im_adj = SDS_preprocess.rescale_image_intensity(bands[:,:,i], cloud_mask, 99.9)
        axs[i].imshow(im_adj)
        axs[i].set_title(f"Band {i}: {band_names[i]}")
        axs[i].axis(False)


def crop(a, x_start, x_dim, y_start, y_dim):
    return a[y_start:y_start + y_dim, x_start:x_start + x_dim]


def plot_preprocessing_steps(base_dir, deg_type):
    fig, axs = plt.subplots(1, 3, figsize=(20, 4))
    axs = axs.ravel()
    for ax in axs: ax.axis(False)
    name = "ms"

    # cropping
    crop_ms_fn = get_crop_tif_name(name, base_dir)
    crop_bands = load_tif(crop_ms_fn)
    cloud_mask = np.full(crop_bands.shape[:-1], False)
    im_adj = SDS_preprocess.rescale_image_intensity(crop_bands[:,:,[4, 2, 1]], cloud_mask, 99.9)
    axs[0].imshow(im_adj)
    axs[0].set_title("1. Cropping")
    del crop_bands

    # pansharpening
    ps_ms_fn = get_ps_tif_name(base_dir)
    ps_bands = load_tif(ps_ms_fn)
    cloud_mask = np.full(ps_bands.shape[:-1], False)
    im_adj = SDS_preprocess.rescale_image_intensity(ps_bands[:,:,[4, 2, 1]], cloud_mask, 99.9)
    axs[1].imshow(im_adj)
    axs[1].set_title("2a. Pansharpening")
    del ps_bands

    # degrading
    deg_fn = get_degraded_tif_name(name, deg_type, base_dir)
    deg_bands = load_tif(deg_fn)
    cloud_mask = np.full(deg_bands.shape[:-1], False)
    im_adj = SDS_preprocess.rescale_image_intensity(deg_bands[:,:,[4, 2, 1]], cloud_mask, 99.9)
    axs[2].imshow(im_adj)
    axs[2].set_title(f"2b. Degrading ({deg_type})")
    del deg_bands

    plt.show()
    plt.close(fig)

##########################
# Cropping
##########################
def get_intersection_bounds(fns):
    bounds = [SDS_tools.get_image_bounds(fn) for fn in fns]
    intersection_bounds = shapely.intersection_all(bounds)
    return np.array(intersection_bounds.exterior.xy).T, intersection_bounds


def snap_window_to_grid(gt, ulx, uly, lrx, lry):
    """Snap a bounding box to the nearest pixel edges of a given geotransform."""
    px = gt[1]   # pixel width
    py = gt[5]   # pixel height (negative)
    origin_x = gt[0]
    origin_y = gt[3]

    # Snap by rounding to nearest pixel boundary
    snapped_ulx = origin_x + np.floor((ulx - origin_x) / px) * px
    snapped_lrx = origin_x + np.ceil((lrx - origin_x) / px) * px
    snapped_uly = origin_y + np.ceil((uly - origin_y) / py) * py   # py is negative so ceil shrinks
    snapped_lry = origin_y + np.floor((lry - origin_y) / py) * py

    return snapped_ulx, snapped_uly, snapped_lrx, snapped_lry


def get_window_from_bounds(bounds):
    upper_left_x = np.min(bounds[:,0])
    upper_left_y = np.max(bounds[:,1])
    lower_right_x = np.max(bounds[:,0])
    lower_right_y = np.min(bounds[:,1])
    return (upper_left_x,upper_left_y,lower_right_x,lower_right_y)


def crop_tif(fn, name, base_dir, window):
    crop_fn = get_crop_tif_name(name, base_dir)
    gdal.Translate(crop_fn, fn, projWin=window)
    return crop_fn


def crop_tifs(swir_fn, pan_fn, ms_fn, aoi_world, base_dir):
    fns = [swir_fn, pan_fn, ms_fn]
    names = ["swir", "pan", "ms"]
    infos = [get_raster_info(fn) for fn in fns]

    window = get_window_from_bounds(aoi_world)

    crop_fns = []
    for fn, info, name in zip(fns, infos, names):
        snapped_window = snap_window_to_grid(info["gt"], *window)
        crop_fn = crop_tif(fn, name, base_dir, snapped_window)
        crop_fns.append(crop_fn)

    return crop_fns


##########################
# Co-registration
##########################
def coreg_tif(fn, name, base_dir, opts, resample_alg):
    coreg_fn = get_coreg_tif_name(name, base_dir)
    gdal.Warp(coreg_fn, fn, **opts, resampleAlg=resample_alg)
    return coreg_fn

def coreg_tifs(base_dir, resample_alg):
    names = ["swir", "pan", "ms"]
    crop_fns = [get_crop_tif_name(name, base_dir) for name in names]
    infos = [get_raster_info(fn) for fn in crop_fns]
    ref_info = infos[1] # pan

    warp_opts = dict(
        outputBounds=(ref_info["ulx"], ref_info["lry"], ref_info["lrx"], ref_info["uly"]),
        xRes=ref_info["xres"],
        yRes=ref_info["yres"],
        targetAlignedPixels=False,
        dstSRS=ref_info["srs"],
        format="GTiff",
    )

    coreg_fns = [coreg_tif(fn, name, base_dir, warp_opts, resample_alg) for fn, name in zip(crop_fns, names)]

    return coreg_fns

##########################
# Pansharpening
##########################
def pansharpen(base_dir):

    # load ms and pan
    coreg_ms_fn = get_coreg_tif_name("ms", base_dir)
    coreg_pan_fn = get_coreg_tif_name("pan", base_dir)
    im_ms = load_tif(coreg_ms_fn)
    im_pan = load_tif(coreg_pan_fn)

    # pansharpen bands within panchromatic band
    cloud_mask = np.zeros(im_pan.shape, dtype=bool)
    bands_to_sharpen = [1, 2, 3, 4, 5]
    ps_bands = modified_coastsat.pansharpen(im_ms[:,:,bands_to_sharpen], im_pan, cloud_mask)

    # smush back together with non-pansharpened bands (their resolution has also been increased)
    im_ms_ps = np.append(im_ms[:,:,[0]], ps_bands, axis=2)
    im_ms_ps = np.append(im_ms_ps, im_ms[:,:,[6, 7]], axis=2)

    ds = gdal.Open(coreg_ms_fn)
    ps_ms_fn = get_ps_tif_name(base_dir)
    write_geotiff(ps_ms_fn, im_ms_ps, ds)

    ds = None
    return ps_ms_fn


##########################
# Degradation
##########################
# assumes recieving cropped 
def naive_degradation(target_res, resample_alg, base_dir):
    deg_type = f"naive_res_{target_res}"
    os.makedirs(os.path.join(base_dir, deg_type), exist_ok=True)

    names = ["swir", "ms"] # we don't care about panchromatic band
    crop_fns = [get_crop_tif_name(name, base_dir) for name in names]
    crop_infos = [get_raster_info(crop_fn) for crop_fn in crop_fns]
    ref_info = crop_infos[0] # reference grid/image

    warp_opts = dict(
        outputBounds=(ref_info["ulx"], ref_info["lry"], ref_info["lrx"], ref_info["uly"]),
        xRes=target_res,
        yRes=target_res,
        targetAlignedPixels=False,
        dstSRS=ref_info["srs"],
        format="GTiff",
    )

    degraded_fns = [get_degraded_tif_name(name, deg_type, base_dir) for name in names]
    for degraded_fn, crop_fn in zip(degraded_fns, crop_fns):
        gdal.Warp(degraded_fn, crop_fn, **warp_opts, resampleAlg=resample_alg)
    
    return degraded_fns

def naive_band_smushing(ms_deg_fn, swir_deg_fn, base_dir):
    ms_degraded_bands = load_tif(ms_deg_fn)
    swir_degraded_bands = load_tif(swir_deg_fn, is_swir=True)

    sim_bands = ms_degraded_bands[:,:,[1, 2, 4, 6]]
    sim_bands = np.append(sim_bands, swir_degraded_bands[:,:,[1,5]], axis=2)

    ds = gdal.Open(ms_deg_fn)
    sim_fn = get_sim_tif_name("naive_res_10", base_dir)
    write_geotiff(sim_fn, sim_bands, ds)

    ds = None
    return sim_fn

##########################
# Shoreline
##########################
def create_shoreline_buffer(im_shape, ref_sls, buffer_size): # from vos

    # Default to empty binary mask
    im_buffer = np.zeros(im_shape, dtype='uint8')

    shapes = []
    for ref_sl in ref_sls:
        if len(ref_sl) < 2:
            continue  # skip degenerate lines
        try:
            line = LineString(ref_sl)
            buffered = line.buffer(buffer_size)  # buffer in image CRS units
            shapes.append(buffered)
        except Exception as e:
            print(f"[Warning] Could not buffer reference shoreline: {e}")

    if shapes:
        # Rasterize buffered geometries into binary mask with dtype uint8
        im_buffer = rasterize(
            [(shape, 1) for shape in shapes],
            out_shape=im_shape,
            fill=0,
            dtype='uint8'
        )

    # Convert to bool to maintain compatibility with rest of workflow
    return im_buffer.astype(bool)


def shoreline_to_points(ref_sl, delta=0.5):

    all_points = []
    for l in ref_sl:
        line = LineString(l)

        
        distances = np.arange(0, line.length, delta)
        points = [line.interpolate(distance).coords for distance in distances] + [line.boundary.geoms[1].coords]
        points = np.array(points).reshape(-1, 2)
        all_points.append(points)


    return np.concat(all_points)


##########################
# Misc
##########################
def write_geotiff(filename, arr, in_ds):
    arr_type = gdal.GDT_Float32

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(filename, arr.shape[1], arr.shape[0], arr.shape[-1], arr_type)
    out_ds.SetProjection(in_ds.GetProjection())
    out_ds.SetGeoTransform(in_ds.GetGeoTransform())
    
    for i in range(arr.shape[-1]):
        band = out_ds.GetRasterBand(i+1)
        band.WriteArray(arr[:,:,i])
        band.FlushCache()
        band.ComputeStatistics(False)


def get_raster_info(fn):
    ds = gdal.Open(fn)
    gt = ds.GetGeoTransform()
    xsize = ds.RasterXSize
    ysize = ds.RasterYSize
    proj = ds.GetProjection()
    ds = None

    ulx = gt[0]
    uly = gt[3]
    lrx = gt[0] + xsize * gt[1]
    lry = gt[3] + ysize * gt[5]  # gt[5] is negative
    
    return {"gt": gt, "ulx": ulx, "uly": uly, "lrx": lrx, "lry": lry,
            "xres": gt[1], "yres": abs(gt[5]), "srs": proj}


def get_crop_tif_name(name, base_dir):
    return os.path.join(base_dir, "cropped", f"{name}_cropped.tif")

def get_coreg_tif_name(name, base_dir):
    return os.path.join(base_dir, "coreg", f"{name}_cropped.tif")

def get_degraded_tif_name(name, deg_type, base_dir):
    return os.path.join(base_dir, deg_type, f"{name}_degraded.tif")

def get_sim_tif_name(deg_type, base_dir):
    return os.path.join(base_dir, deg_type, "sim.tif")

def get_ps_tif_name(base_dir):
    return os.path.join(base_dir, "pansharpened", f"ms_ps.tif") # can only be ms