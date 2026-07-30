import os, sys
from datetime import timedelta

# coastsat modules
sys.path.insert(0, os.pardir)
from coastsat import SDS_download, SDS_preprocess, SDS_shoreline, SDS_tools, SDS_classify
from general_utils import modified_coastsat

def init_dir_structure(base_dir, exp_name):
    data_dir = os.path.join(base_dir, "data")
    aoi_dir = os.path.join(data_dir, "aoi")
    ref_sl_dir = os.path.join(data_dir, "ref_sl")
    transect_dir = os.path.join(data_dir, "transects")
    
    plots_dir = os.path.join(base_dir, exp_name, "plots")

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(aoi_dir, exist_ok=True)
    os.makedirs(ref_sl_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(transect_dir, exist_ok=True)


# dl_dict should be from image_plotting_parameters.get_download_dict
# aoi_path and ref_sl_path should be from image_plotting_parameters.get_paths (these paths will likely have to be modified)
def init_site(sitename, output_epsg, output_dir, dl_dict, aoi_path, ref_sl_path):
    data_path = os.path.join(output_dir, "data", sitename)
    polygon = SDS_tools.polygon_from_kml(aoi_path)
    polygon = SDS_tools.smallest_rectangle(polygon)
    ref_sl = SDS_preprocess.get_reference_sl_from_geojson(ref_sl_path, output_epsg)

    return dl_dict, data_path, ref_sl, polygon

def download(sitename, dl_dict, data_path, polygon):
    one_day = timedelta(days=1)
    format = "%Y-%m-%d"
    for satname in dl_dict.keys():
        for date in dl_dict[satname]:
            date_range = [date.strftime(format), (date + one_day).strftime(format)]

            cur_inputs = {
                'dates': date_range,
                'sat_list': [satname],
                'filepath': data_path,
                'sitename': sitename,
                'polygon': polygon
            }
            modified_coastsat.retrieve_images(cur_inputs)

    inputs = {
        'filepath': data_path,
        'sitename': sitename
    }
    return SDS_download.get_metadata(inputs), inputs


def load_and_preprocess(metadata, inputs, buffer_settings):
    ims = []
    cloud_masks = []
    fns = []
    georefs = []
    im_buffers = []
    im_nodatas = []
    im_epsgs = []

    for satname in metadata.keys():
        filenames = metadata[satname]['filenames']
        filepath = modified_coastsat.get_filepath(inputs, satname)

        for i in range(len(filenames)):
            fn = modified_coastsat.get_filenames(filenames[i], filepath, satname)


            im_ms, georef, cloud_mask, im_extra, im_QA, im_nodata = modified_coastsat.preprocess_single(
                            fn, satname, cloud_mask_issue=False, pan_off=False, s2cloudless_prob=60)

            im_buffer = SDS_shoreline.create_shoreline_buffer(cloud_mask.shape, georef, metadata[satname]['epsg'][i], buffer_settings)

            ims.append(im_ms)
            cloud_masks.append(cloud_mask)
            fns.append(fn)
            georefs.append(georef)
            im_buffers.append(im_buffer)
            im_nodatas.append(im_nodata)
            im_epsgs.append(metadata[satname]['epsg'][i])

    return ims, cloud_masks, fns, georefs, im_buffers, im_nodatas, im_epsgs