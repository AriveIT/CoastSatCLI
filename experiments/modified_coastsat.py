"""
based on kv coastsat
"""

import os, sys
import numpy as np
import pickle
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt

from datetime import datetime, timedelta
import time
import pytz
import ee
import re
import skimage.morphology as morphology
import skimage.measure as measure
import sklearn.decomposition as decomposition

from osgeo import gdal
from pyproj import CRS
from pylab import ginput

# coastsat modules
sys.path.insert(0, os.pardir)
from coastsat import SDS_download, SDS_preprocess, SDS_shoreline, SDS_tools, SDS_classify

def retrieve_images(inputs, project):
    """
    Downloads all images from Landsat 5, Landsat 7, Landsat 8, Landsat 9 and Sentinel-2
    covering the area of interest and acquired between the specified dates.
    The downloaded images are in .TIF format and organised in subfolders, divided
    by satellite mission. The bands are also subdivided by pixel resolution.

    KV WRL 2018

    Arguments:
    -----------
    inputs: dict with the following keys
        'sitename': str
            name of the site
        'polygon': list
            polygon containing the lon/lat coordinates to be extracted,
            longitudes in the first column and latitudes in the second column,
            there are 5 pairs of lat/lon with the fifth point equal to the first point:
            ```
            polygon = [[[151.3, -33.7],[151.4, -33.7],[151.4, -33.8],[151.3, -33.8],
            [151.3, -33.7]]]
            ```
        'dates': list of str
            list that contains 2 strings with the initial and final dates in
            format 'yyyy-mm-dd':
            ```
            dates = ['1987-01-01', '2018-01-01']
            ```
        'sat_list': list of str
            list that contains the names of the satellite missions to include:
            ```
            sat_list = ['L5', 'L7', 'L8', 'S2']
            ```
        'filepath_data': str
            filepath to the directory where the images are downloaded

    Returns:
    -----------
    metadata: dict
        contains the information about the satellite images that were downloaded:
        date, filename, georeferencing accuracy and image coordinate reference system

    """
    # initialise connection with GEE server
    SDS_download.authenticate_and_initialize(project)

    # check image availabiliy and retrieve list of images
    im_dict_T1, im_dict_T2 = check_images_available(inputs)

    excluded_epsg_codes = inputs.get('excluded_epsg_codes', [])

    # Filter images based on `excluded_epsg_codes` if provided
    if excluded_epsg_codes:
        for satname, im_list in im_dict_T1.items():
            im_dict_T1[satname] = [im_meta for im_meta in im_list if im_meta['bands'][0]['crs'] not in [f'EPSG:{code}' for code in excluded_epsg_codes]]

    # if user also wants to download T2 images, merge both lists
    if 'include_T2' in inputs.keys():
        for key in inputs['sat_list']:
            if key in ['S2','L9']: continue
            else: im_dict_T1[key] += im_dict_T2[key]

    # for S2 get s2cloudless collection for advanced cloud masking
    if 'S2' in inputs['sat_list'] and len(im_dict_T1['S2'])>0:
        im_dict_s2cloudless = SDS_download.get_s2cloudless(im_dict_T1['S2'], inputs)

    # create a new directory for this site with the name of the site
    im_folder = inputs['filepath']
    if not os.path.exists(im_folder): os.makedirs(im_folder)

    # QA band for each satellite mission
    qa_band_Landsat = 'QA_PIXEL'
    qa_band_S2 = 'QA60'
    # the cloud mask band for Sentinel-2 images is the s2cloudless probability ############################## add SWIR2
    bands_dict = {'L5':['B1','B2','B3','B4','B5','B7',qa_band_Landsat],
                  'L7':['B1','B2','B3','B4','B5','B7',qa_band_Landsat],
                  'L8':['B2','B3','B4','B5','B6','B7',qa_band_Landsat],
                  'L9':['B2','B3','B4','B5','B6','B7',qa_band_Landsat],
                  'S2':['B2','B3','B4','B8','s2cloudless','B11','B12',qa_band_S2]}
    
    # main loop to download the images for each satellite mission
    suffix = '.tif'
    for satname in im_dict_T1.keys():


        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, satname)
        
        # select bands for satellite sensor
        bands_id = bands_dict[satname]
        
        all_names = [] # list for detecting duplicates
        # loop through each image
        last_pct = -1
        for i in range(len(im_dict_T1[satname])):
            
            # get image metadata
            im_meta = im_dict_T1[satname][i]

            # get time of acquisition (UNIX time) and convert to datetime
            t = im_meta['properties']['system:time_start']
            im_timestamp = datetime.fromtimestamp(t/1000, tz=pytz.utc)
            im_date = im_timestamp.strftime('%Y-%m-%d-%H-%M-%S')

            if 'months' in inputs and im_timestamp.month not in inputs['months']:
                continue
            
            # skip L7 after 2022 as L9 is replacing it
            if im_timestamp.year >= 2022 and satname == 'L7':
                continue
            # additionally, skip L7 after Scan-Line-Correction failure
            if ('skip_L7_SLC' in inputs.keys() and
                    inputs['skip_L7_SLC'] and
                    satname == 'L7' and
                    im_timestamp >= pytz.utc.localize(datetime(2003,5,31))):
                continue
            
            # get epsg code
            im_epsg = int(im_meta['bands'][0]['crs'][5:])

            # get geometric accuracy, radiometric quality and tilename for Landsat
            if satname in ['L5','L7','L8','L9']:
                if 'GEOMETRIC_RMSE_MODEL' in im_meta['properties'].keys():
                    acc_georef = im_meta['properties']['GEOMETRIC_RMSE_MODEL']
                else:
                    acc_georef = 12 # average georefencing error across Landsat collection (RMSE = 12m)
                # add radiometric quality [image_quality 1-9 for Landsat]
                if satname in ['L5','L7']:
                    rad_quality = im_meta['properties']['IMAGE_QUALITY']
                elif satname in ['L8','L9']:
                    rad_quality = im_meta['properties']['IMAGE_QUALITY_OLI']
                # add tilename (path/row)
                tilename = '%03d%03d'%(im_meta['properties']['WRS_PATH'],im_meta['properties']['WRS_ROW'])
                
            # get geometric accuracy, radiometric quality and tilename for S2
            elif satname in ['S2']:
                # Sentinel-2 products don't provide a georeferencing accuracy (RMSE as in Landsat)
                # but they have a flag indicating if the geometric quality control was PASSED or FAILED
                # if passed a value of 1 is stored if failed a value of -1 is stored in the metadata
                # check which flag name is used for the image as it changes for some reason in the archive
                flag_names = ['GEOMETRIC_QUALITY_FLAG', 'GEOMETRIC_QUALITY', 'quality_check', 'GENERAL_QUALITY_FLAG']
                key = []
                for key in flag_names: 
                    if key in im_meta['properties'].keys(): 
                        break # use the first flag that is found
                if len(key) > 0:
                    acc_georef = im_meta['properties'][key]
                else:
                    print('WARNING: could not find Sentinel-2 geometric quality flag,'+ 
                          ' raise an issue at https://github.com/kvos/CoastSat/issues'+
                          ' and add you inputs in text (not a screenshot pls).')
                    acc_georef = 'PASSED'
                # add the radiometric image quality ['PASSED' or 'FAILED']
                flag_names = ['RADIOMETRIC_QUALITY', 'RADIOMETRIC_QUALITY_FLAG']
                key = []
                for key in flag_names: 
                    if key in im_meta['properties'].keys(): 
                        break # use the first flag that is found
                if len(key) > 0:
                    rad_quality = im_meta['properties'][key]
                else:
                    print('WARNING: could not find Sentinel-2 geometric quality flag,'+ 
                          ' raise an issue at https://github.com/kvos/CoastSat/issues'+
                          ' and add your inputs in text (not a screenshot pls).')
                    rad_quality = 'PASSED'
                # add tilename (MGRS name)
                tilename = im_meta['properties']['MGRS_TILE']
                
            # select image by id
            image_ee = ee.Image(im_meta['id'])
            
            # for S2 add s2cloudless probability band
            if satname == 'S2':
                if len(im_dict_s2cloudless[i]) == 0:
                    print('Warning: S2cloudless mask for image %s is not available yet, try again tomorrow.'%im_date)
                    continue
                im_cloud = ee.Image(im_dict_s2cloudless[i]['id'])
                cloud_prob = im_cloud.select('probability').rename('s2cloudless')
                image_ee = image_ee.addBands(cloud_prob)
            
            # download the images as .tif files
            bands = dict([])
            im_fn = dict([])
            # first delete dimensions key from dictionnary
            # otherwise the entire image is extracted (don't know why)
            im_bands = image_ee.getInfo()['bands']
            for j in range(len(im_bands)):
                if 'dimensions' in im_bands[j].keys():
                    del im_bands[j]['dimensions']
            
            #=============================================================================================#
            # Landsat 5 download
            #=============================================================================================#
            if satname == 'L5':
                fp_ms = filepaths[1]
                fp_mask = filepaths[2] 
                # select multispectral bands
                bands['ms'] = [im_bands[_] for _ in range(len(im_bands)) if im_bands[_]['id'] in bands_id]
                # adjust polygon to match image coordinates so that there is no resampling
                proj = image_ee.select('B1').projection()
                ee_region = SDS_download.adjust_polygon(inputs['polygon'],proj)
                # download .tif from EE (one file with ms bands and one file with QA band)
                count = 0
                while True:
                    try:    
                        fn_ms, fn_QA = SDS_download.download_tif(image_ee,ee_region,bands['ms'],fp_ms,satname) 
                        break
                    except Exception as e:
                        print(f'\nDownload failed with exception {e}, trying again...')
                        time.sleep(5)
                        count += 1
                        if count > 25:
                            raise Exception('Too many attempts, crashed while downloading image %s'%im_meta['id'])
                        else:
                            continue
                        
                # create filename for image
                for key in bands.keys():
                    im_fn[key] = im_date + '_' + satname + '_' + tilename + '_' + inputs['sitename'] + '_' + key + suffix
                # if multiple images taken at the same date add 'dupX' to the name (duplicate number X)
                duplicate_counter = 0
                while im_fn['ms'] in all_names:
                    duplicate_counter += 1
                    for key in bands.keys():
                        im_fn[key] = im_date + '_' + satname + '_' + tilename + '_' \
                            + inputs['sitename'] + '_' + key \
                            + '_dup%d'%duplicate_counter + suffix
                im_fn['mask'] = im_fn['ms'].replace('_ms','_mask')
                filename_ms = im_fn['ms']
                all_names.append(im_fn['ms'])
                
                # resample ms bands to 15m with bilinear interpolation
                fn_in = fn_ms
                fn_target = fn_ms
                fn_out = os.path.join(fp_ms, im_fn['ms'])
                SDS_download.warp_image_to_target(fn_in,fn_out,fn_target,double_res=True,resampling_method='bilinear')                
                
                # resample QA band to 15m with nearest-neighbour interpolation
                fn_in = fn_QA
                fn_target = fn_QA
                fn_out = os.path.join(fp_mask, im_fn['mask'])
                SDS_download.warp_image_to_target(fn_in,fn_out,fn_target,double_res=True,resampling_method='near')
                
                # delete original downloads
                for _ in [fn_ms,fn_QA]: os.remove(_)

            #=============================================================================================#
            # Landsat 7, 8 and 9 download
            #=============================================================================================#
            elif satname in ['L7', 'L8', 'L9']:
                fp_ms = filepaths[1]
                fp_pan = filepaths[2]
                fp_mask = filepaths[3] 
                # select bands (multispectral and panchromatic)
                bands['ms'] = [im_bands[_] for _ in range(len(im_bands)) if im_bands[_]['id'] in bands_id]
                bands['pan'] = [im_bands[_] for _ in range(len(im_bands)) if im_bands[_]['id'] in ['B8']]
                # adjust polygon for both ms and pan bands
                proj_ms = image_ee.select('B1').projection()
                proj_pan = image_ee.select('B8').projection()
                ee_region_ms = SDS_download.adjust_polygon(inputs['polygon'],proj_ms)
                ee_region_pan = SDS_download.adjust_polygon(inputs['polygon'],proj_pan)

                # download both ms and pan bands from EE
                count = 0
                while True:
                    try:    
                        fn_ms, fn_QA = SDS_download.download_tif(image_ee,ee_region_ms,bands['ms'],fp_ms,satname)
                        fn_pan = SDS_download.download_tif(image_ee,ee_region_pan,bands['pan'],fp_pan,satname)
                        break
                    except Exception as e:
                        print(f'\nDownload failed with exception {e}, trying again...')
                        time.sleep(5)
                        count += 1
                        if count > 25:
                            raise Exception('Too many attempts, crashed while downloading image %s'%im_meta['id'])
                        else:
                            continue
                
                # create filename for both images (ms and pan)
                for key in bands.keys():
                    im_fn[key] = im_date + '_' + satname + '_' + tilename + '_' + inputs['sitename'] + '_' + key + suffix
                # if multiple images taken at the same date add 'dupX' to the name (duplicate number X)
                duplicate_counter = 0
                while im_fn['ms'] in all_names:
                    duplicate_counter += 1
                    for key in bands.keys():
                        im_fn[key] = im_date + '_' + satname + '_' + tilename + '_' \
                            + inputs['sitename'] + '_' + key \
                            + '_dup%d'%duplicate_counter + suffix
                im_fn['mask'] = im_fn['ms'].replace('_ms','_mask')
                filename_ms = im_fn['ms']
                all_names.append(im_fn['ms']) 
                
                # resample the ms bands to the pan band with bilinear interpolation (for pan-sharpening later)
                fn_in = fn_ms
                fn_target = fn_pan
                fn_out = os.path.join(fp_ms, im_fn['ms'])
                SDS_download.warp_image_to_target(fn_in,fn_out,fn_target,double_res=False,resampling_method='bilinear')             
                
                # resample QA band to the pan band with nearest-neighbour interpolation
                fn_in = fn_QA
                fn_target = fn_pan
                fn_out = os.path.join(fp_mask, im_fn['mask'])
                SDS_download.warp_image_to_target(fn_in,fn_out,fn_target,double_res=False,resampling_method='near')

                # rename pan band
                try:
                    os.rename(fn_pan,os.path.join(fp_pan,im_fn['pan']))
                except:
                    os.remove(os.path.join(fp_pan,im_fn['pan']))
                    os.rename(fn_pan,os.path.join(fp_pan,im_fn['pan']))  
                # delete original downloads
                for _ in [fn_ms,fn_QA]: os.remove(_)

            #=============================================================================================#
            # Sentinel-2 download 
            #=============================================================================================#
            # 'S2':['B2','B3','B4','B8','s2cloudless','B11','B12',qa_band_S2]}
            elif satname in ['S2']:                
                fp_ms = filepaths[1]
                fp_swir1 = filepaths[2]
                fp_swir2 = filepaths[3]
                fp_mask = filepaths[4]    
                # select bands (10m ms RGB+NIR+s2cloudless, 20m SWIR1, 60m QA band)
                bands['ms'] = [im_bands[_] for _ in range(len(im_bands)) if im_bands[_]['id'] in bands_id[:5]]
                bands['swir1'] = [im_bands[_] for _ in range(len(im_bands)) if im_bands[_]['id'] in bands_id[5:6]]
                bands['swir2'] = [im_bands[_] for _ in range(len(im_bands)) if im_bands[_]['id'] in bands_id[6:7]]
                bands['mask'] = [im_bands[_] for _ in range(len(im_bands)) if im_bands[_]['id'] in bands_id[-1:]]
                # adjust polygon for both ms and pan bands
                proj_ms = image_ee.select('B1').projection()
                proj_swir1 = image_ee.select('B11').projection()
                proj_swir2 = image_ee.select('B12').projection()
                proj_mask = image_ee.select('QA60').projection()
                ee_region_ms = SDS_download.adjust_polygon(inputs['polygon'],proj_ms)
                ee_region_swir1 = SDS_download.adjust_polygon(inputs['polygon'],proj_swir1)
                ee_region_swir2 = SDS_download.adjust_polygon(inputs['polygon'],proj_swir2)
                ee_region_mask = SDS_download.adjust_polygon(inputs['polygon'],proj_mask)
                # download the ms, swir and QA bands from EE
                count = 0
                while True:
                    try:    
                        fn_ms = SDS_download.download_tif(image_ee,ee_region_ms,bands['ms'],fp_ms,satname)
                        fn_swir1 = SDS_download.download_tif(image_ee,ee_region_swir1,bands['swir1'],fp_swir1,satname)
                        fn_swir2 = SDS_download.download_tif(image_ee,ee_region_swir2,bands['swir2'],fp_swir2,satname)
                        fn_QA = SDS_download.download_tif(image_ee,ee_region_mask,bands['mask'],fp_mask,satname)
                        break
                    except Exception as e:
                        print(f'\nDownload failed with exception {e}, trying again...')
                        time.sleep(5)
                        count += 1
                        if count > 25:
                            raise Exception('Too many attempts, crashed while downloading image %s'%im_meta['id'])
                        else:
                            continue             
                
                # create filename for the three images (ms, swir and mask)
                for key in bands.keys():
                    im_fn[key] = im_date + '_' + satname + '_' + tilename + '_' + inputs['sitename'] + '_' + key + suffix
                # if multiple images taken at the same date add 'dupX' to the name (duplicate)
                duplicate_counter = 0
                while im_fn['ms'] in all_names:
                    duplicate_counter += 1
                    for key in bands.keys():
                        im_fn[key] = im_date + '_' + satname + '_' + tilename + '_' \
                            + inputs['sitename'] + '_' + key \
                            + '_dup%d'%duplicate_counter + suffix
                filename_ms = im_fn['ms']
                all_names.append(im_fn['ms']) 
                
                # resample the 20m swir1 and swir2 band to the 10m ms band with bilinear interpolation
                fn_in = fn_swir1
                fn_target = fn_ms
                fn_out = os.path.join(fp_swir1, im_fn['swir1'])
                SDS_download.warp_image_to_target(fn_in,fn_out,fn_target,double_res=False,resampling_method='bilinear') 
                
                fn_in = fn_swir2
                fn_target = fn_ms
                fn_out = os.path.join(fp_swir2, im_fn['swir2'])
                SDS_download.warp_image_to_target(fn_in,fn_out,fn_target,double_res=False,resampling_method='bilinear')

                # resample 60m QA band to the 10m ms band with nearest-neighbour interpolation
                fn_in = fn_QA
                fn_target = fn_ms
                fn_out = os.path.join(fp_mask, im_fn['mask'])
                SDS_download.warp_image_to_target(fn_in,fn_out,fn_target,double_res=False,resampling_method='near')
                
                # delete original downloads
                for _ in [fn_swir1,fn_QA]: os.remove(_)  
                # rename the multispectral band file
                os.rename(fn_ms,os.path.join(fp_ms, im_fn['ms']))
              
            # get image dimensions (width and height)
            image_path = os.path.join(fp_ms,im_fn['ms'])
            width, height = SDS_tools.get_image_dimensions(image_path)
            # write metadata in a text file for easy access
            filename_txt = im_fn['ms'].replace('_ms','').replace('.tif','')
            metadict = {'filename':filename_ms,'tile':tilename,'epsg':im_epsg,
                        'acc_georef':acc_georef,'image_quality':rad_quality,
                        'im_width':width,'im_height':height}
            with open(os.path.join(filepaths[0],filename_txt + '.txt'), 'w') as f:
                for key in metadict.keys():
                    f.write('%s\t%s\n'%(key,metadict[key]))

        
    # once all images have been downloaded, load metadata from .txt files
    metadata = SDS_download.get_metadata(inputs)
    
    # merge overlapping images (necessary only if the polygon is at the boundary of an image)
    # if 'S2' in metadata.keys():
    #     print("\n Called merge_overlapping_images\n")
    #     try:
    #         metadata = merge_overlapping_images(metadata,inputs)
    #     except:
    #         print('WARNING: there was an error while merging overlapping S2 images,'+
    #               ' please open an issue on Github at https://github.com/kvos/CoastSat/issues'+
    #               ' and include your script so we can find out what happened.')

    # save metadata dict
    with open(os.path.join(im_folder, inputs['sitename'] + '_metadata' + '.pkl'), 'wb') as f:
        pickle.dump(metadata, f)
    print('Satellite images downloaded from GEE and save in %s'%im_folder)
    return metadata

def check_images_available(inputs):
    """
    Scan the GEE collections to see how many images are available for each
    satellite mission (L5,L7,L8,L9,S2), collection (C02) and tier (T1,T2).
    
    Note: Landsat Collection 1 (C01) is deprecated. Users should migrate to Collection 2 (C02).
    For more information, visit: https://developers.google.com/earth-engine/landsat_c1_to_c2

    KV WRL 2018

    Arguments:
    -----------
    inputs: dict
        inputs dictionnary

    Returns:
    -----------
    im_dict_T1: list of dict
        list of images in Tier 1 and Level-1C
    im_dict_T2: list of dict
        list of images in Tier 2 (Landsat only)
    """

    dates = [datetime.strptime(_,'%Y-%m-%d') for _ in inputs['dates']]
    dates_str = inputs['dates']
    polygon = inputs['polygon']
    
    # check if dates are in chronological order
    if  dates[1] <= dates[0]:
        raise Exception('Verify that your dates are in the correct chronological order')

    # check if EE was initialised or not
    try:
        ee.ImageCollection('LANDSAT/LT05/C02/T1_TOA')
    except:
        ee.Initialize()
        
    
    # get images in Landsat Tier 1 as well as Sentinel Level-1C
    col_names_T1 = {'L5':'LANDSAT/LT05/C02/T1_TOA',
                    'L7':'LANDSAT/LE07/C02/T1_TOA',
                    'L8':'LANDSAT/LC08/C02/T1_TOA',
                    'L9':'LANDSAT/LC09/C02/T1_TOA',
                    'S2':'COPERNICUS/S2_HARMONIZED'}
    im_dict_T1 = dict([])
    sum_img = 0
    for satname in inputs['sat_list']:
        # if user specifies an S2 tile and satname is S2
        if 'S2tile' in inputs.keys() and satname == 'S2':
            im_list = SDS_download.get_image_info(col_names_T1[satname],satname,polygon,dates_str,
                                     S2tile=inputs['S2tile'])
        # if user specifies a Landsat tile (WRS path/row) and satname is Landsat
        elif 'LandsatWRS' in inputs.keys() and (not satname == 'S2'):
            im_list = SDS_download.get_image_info(col_names_T1[satname],satname,polygon,dates_str,
                                     LandsatWRS=inputs['LandsatWRS']) 
        # if user does not specify a tile
        else:
            # get all images (no tile filtering)
            im_list = SDS_download.get_image_info(col_names_T1[satname],satname,polygon,dates_str)
            # for S2, filter collection to only keep images with same UTM Zone projection 
            # (there duplicated images in different UTM projections)
            if satname == 'S2': 
                im_list = SDS_download.filter_S2_collection(im_list)
        sum_img = sum_img + len(im_list)
        im_dict_T1[satname] = im_list       
        

    # check if images already exist  
    # print('\nLooking for existing imagery...')
    filepath = inputs['filepath']
    if os.path.exists(filepath):
        metadata_existing = SDS_download.get_metadata(inputs)
        for satname in inputs['sat_list']:
            # remove from download list the images that are already existing
            if satname in metadata_existing:
                if len(metadata_existing[satname]['dates']) > 0:
                    # get all the possible availabe dates for the imagery requested
                    avail_date_list = [datetime.fromtimestamp(image['properties']['system:time_start'] / 1000, tz=pytz.utc).replace( microsecond=0) for image in im_dict_T1[satname]]
                    # if no images are available, skip this loop
                    if len(avail_date_list) == 0:
                        continue
                    # get the dates of the images that are already downloaded
                    downloaded_dates = metadata_existing[satname]['dates']
                    # if no images are already downloaded, skip this loop and use whats already in im_dict_T1[satname]
                    if len(downloaded_dates) == 0:
                        continue
                    # get the indices of the images that are not already downloaded 
                    idx_new = np.where([ not avail_date in downloaded_dates for avail_date in avail_date_list])[0]
                    im_dict_T1[satname] = [im_dict_T1[satname][index] for index in idx_new]

    # if only S2 is in sat_list, stop here as no Tier 2 for Sentinel
    if len(inputs['sat_list']) == 1 and inputs['sat_list'][0] == 'S2':
        return im_dict_T1, []

    # if user also requires Tier 2 images, check the T2 collections as well
    col_names_T2 = {'L5':'LANDSAT/LT05/C02/T2_TOA',
                    'L7':'LANDSAT/LE07/C02/T2_TOA',
                    'L8':'LANDSAT/LC08/C02/T2_TOA'}
    im_dict_T2 = dict([])
    sum_img = 0
    for satname in inputs['sat_list']:
        if satname in ['L9','S2']: continue # no Tier 2 for Sentinel-2 and Landsat 9
        im_list = SDS_download.get_image_info(col_names_T2[satname],satname,polygon,dates_str)
        sum_img = sum_img + len(im_list)
        im_dict_T2[satname] = im_list

    
    return im_dict_T1, im_dict_T2

# Main function to preprocess a satellite image (L5, L7, L8, L9 or S2)
def preprocess_single(fn, satname, cloud_mask_issue, pan_off, s2cloudless_prob=40):
    """
    Reads the image and outputs the pansharpened/down-sampled multispectral bands,
    the georeferencing vector of the image (coordinates of the upper left pixel),
    the cloud mask, the QA band and a no_data image.
    For Landsat 7-8 it also outputs the panchromatic band and for Sentinel-2 it
    also outputs the 20m SWIR band.

    KV WRL 2018

    Arguments:
    -----------
    fn: str or list of str
        filename of the .TIF file containing the image. For L7, L8 and S2 this
        is a list of filenames, one filename for each band at different
        resolution (30m and 15m for Landsat 7-8, 10m, 20m, 60m for Sentinel-2)
    satname: str
        name of the satellite mission (e.g., 'L5')
    cloud_mask_issue: boolean
        True if there is an issue with the cloud mask and sand pixels are being masked on the images
    pan_off : boolean
        if True, disable panchromatic sharpening and ignore pan band
    s2cloudless_prob: float [0,100)
        threshold to identify cloud pixels in the s2cloudless probability mask
        
    Returns:
    -----------
    im_ms: np.array
        3D array containing the pansharpened/down-sampled bands (B,G,R,NIR,SWIR1)
    georef: np.array
        vector of 6 elements [Xtr, Xscale, Xshear, Ytr, Yshear, Yscale] defining the
        coordinates of the top-left pixel of the image
    cloud_mask: np.array
        2D cloud mask with True where cloud pixels are
    im_extra : np.array
        2D array containing the 20m resolution SWIR band for Sentinel-2 and the 15m resolution
        panchromatic band for Landsat 7 and Landsat 8. This field is empty for Landsat 5.
    im_QA: np.array
        2D array containing the QA band, from which the cloud_mask can be computed.
    im_nodata: np.array
        2D array with True where no data values (-inf) are located

    """
    
    if isinstance(fn, list):
        fn_to_split = fn[0]
    elif isinstance(fn, str):
        fn_to_split = fn
    # split by os.sep and only get the filename at the end then split again to remove file extension
    fn_to_split=fn_to_split.split(os.sep)[-1].split('.')[0]
    # search for the year the tif was taken with regex and convert to int
    year = int(re.search('[0-9]+',fn_to_split).group(0))
        
    #=============================================================================================#
    # L5 images
    #=============================================================================================#
    if satname == 'L5':
        # filepaths to .tif files
        fn_ms = fn[0]
        fn_mask = fn[1]
        # read ms bands
        data = gdal.Open(fn_ms, gdal.GA_ReadOnly)
        georef = np.array(data.GetGeoTransform())
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
        im_ms = np.stack(bands, 2)
        # read cloud mask
        data = gdal.Open(fn_mask, gdal.GA_ReadOnly)
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
        im_QA = bands[0]
        cloud_mask = SDS_preprocess.create_cloud_mask(im_QA, satname, cloud_mask_issue)

        # check if -inf or nan values on any band and eventually add those pixels to cloud mask
        im_nodata = np.zeros(cloud_mask.shape).astype(bool)
        for k in range(im_ms.shape[2]):
            im_inf = np.isin(im_ms[:,:,k], -np.inf)
            im_nan = np.isnan(im_ms[:,:,k])
            im_nodata = np.logical_or(np.logical_or(im_nodata, im_inf), im_nan)
        # check if there are pixels with 0 intensity in the Green, NIR and SWIR bands and add those
        # to the cloud mask as otherwise they will cause errors when calculating the NDWI and MNDWI
        im_zeros = np.ones(cloud_mask.shape).astype(bool)
        for k in [1,3,4]: # loop through the Green, NIR and SWIR bands
            im_zeros = np.logical_and(np.isin(im_ms[:,:,k],0), im_zeros)
        # add zeros to im nodata
        im_nodata = np.logical_or(im_zeros, im_nodata)
        # update cloud mask with all the nodata pixels
        cloud_mask = np.logical_or(cloud_mask, im_nodata)

        # no extra image for Landsat 5 (they are all 30 m bands)
        im_extra = []

    #=============================================================================================#
    # L7, L8 and L9 images
    #=============================================================================================#
    elif satname in ['L7','L8','L9']:
        # filepaths to .tif files
        fn_ms = fn[0]
        fn_pan = fn[1]  
        fn_mask = fn[2]  
        # read ms bands
        data = gdal.Open(fn_ms, gdal.GA_ReadOnly)
        georef = np.array(data.GetGeoTransform())
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
        im_ms = np.stack(bands, 2)
        # read cloud mask
        data = gdal.Open(fn_mask, gdal.GA_ReadOnly)
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
        im_QA = bands[0]
        cloud_mask = SDS_preprocess.create_cloud_mask(im_QA, satname, cloud_mask_issue)
        # check if -inf or nan values on any band and eventually add those pixels to cloud mask
        im_nodata = np.zeros(cloud_mask.shape).astype(bool)
        for k in range(im_ms.shape[2]):
            im_inf = np.isin(im_ms[:,:,k], -np.inf)
            im_nan = np.isnan(im_ms[:,:,k])
            im_nodata = np.logical_or(np.logical_or(im_nodata, im_inf), im_nan)
        # check if there are pixels with 0 intensity in the Green, NIR and SWIR bands and add those
        # to the cloud mask as otherwise they will cause errors when calculating the NDWI and MNDWI
        im_zeros = np.ones(cloud_mask.shape).astype(bool)
        for k in [1,3,4]: # loop through the Green, NIR and SWIR bands
            im_zeros = np.logical_and(np.isin(im_ms[:,:,k],0), im_zeros)
        # add zeros to im nodata
        im_nodata = np.logical_or(im_zeros, im_nodata)
        # update cloud mask with all the nodata pixels
        cloud_mask = np.logical_or(cloud_mask, im_nodata) 
        
        # if panchromatic sharpening is turned off
        if pan_off:            
            # ms bands are untouched and the extra image is empty
            im_extra = []
    
        # otherwise perform panchromatic sharpening
        else:
            # read panchromatic band
            data = gdal.Open(fn_pan, gdal.GA_ReadOnly)
            georef = np.array(data.GetGeoTransform())
            bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
            im_pan = bands[0]
           
            # pansharpen Green, Red, NIR for Landsat 7
            if satname == 'L7':
                try:
                    im_ms_ps = SDS_preprocess.pansharpen(im_ms[:,:,[1,2,3]], im_pan, cloud_mask)
                except: # if pansharpening fails, keep downsampled bands (for long runs)
                    print('\npansharpening of image %s failed.'%fn[0])
                    im_ms_ps = im_ms[:,:,[1,2,3]]
                # add downsampled Blue and SWIR1 bands
                im_ms_ps = np.append(im_ms[:,:,[0]], im_ms_ps, axis=2)
                im_ms_ps = np.append(im_ms_ps, im_ms[:,:,[4,5]], axis=2)
                im_ms = im_ms_ps.copy()
                # the extra image is the 15m panchromatic band
                im_extra = im_pan
                
            # pansharpen Blue, Green, Red for Landsat 8 and 9           
            elif satname in ['L8','L9']:
                try:
                    im_ms_ps = SDS_preprocess.pansharpen(im_ms[:,:,[0,1,2]], im_pan, cloud_mask)
                except: # if pansharpening fails, keep downsampled bands (for long runs)
                    print('\npansharpening of image %s failed.'%fn[0])
                    im_ms_ps = im_ms[:,:,[0,1,2]]
                # add downsampled NIR and SWIR1 bands
                im_ms_ps = np.append(im_ms_ps, im_ms[:,:,[3,4,5]], axis=2)
                # plot_pansharpening(im_ms[:,:,[0,1,2]], im_ms_ps[:,:,[0,1,2]], fn[0].split("\\")[-1][:19], cloud_mask)
                im_ms = im_ms_ps.copy()
                # the extra image is the 15m panchromatic band
                im_extra = im_pan
                
                
    #=============================================================================================#
    # S2 images
    #=============================================================================================#
    if satname == 'S2':
        print(fn)
        # read 10m bands (R,G,B,NIR)
        fn_ms = fn[0]
        data = gdal.Open(fn_ms, gdal.GA_ReadOnly)
        georef = np.array(data.GetGeoTransform())
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount-1)]
        im_ms = np.stack(bands, 2)
        im_ms = im_ms/10000 # TOA scaled to 10000
        # read s2cloudless cloud probability (last band in ms image)
        cloud_prob = data.GetRasterBand(data.RasterCount).ReadAsArray()

        # image size
        nrows = im_ms.shape[0]
        ncols = im_ms.shape[1]
        # if image contains only zeros (can happen with S2), skip the image
        if sum(sum(sum(im_ms))) < 1:
            im_ms = []
            georef = []
            # skip the image by giving it a full cloud_mask
            cloud_mask = np.ones((nrows,ncols)).astype('bool')
            return im_ms, georef, cloud_mask, [], [], []

        # read 20m band (SWIR1)
        fn_swir1 = fn[1]
        data = gdal.Open(fn_swir1, gdal.GA_ReadOnly)
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
        im_swir1 = bands[0]
        im_swir1 = im_swir1/10000 # TOA scaled to 10000
        im_swir1 = np.expand_dims(im_swir1, axis=2)

        # append down-sampled SWIR1 band to the other 10m bands
        im_ms = np.append(im_ms, im_swir1, axis=2)

        # read 20m band (SWIR2)
        fn_swir2 = fn[2]
        data = gdal.Open(fn_swir2, gdal.GA_ReadOnly)
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
        im_swir2 = bands[0]
        im_swir2 = im_swir2/10000 # TOA scaled to 10000
        im_swir2 = np.expand_dims(im_swir2, axis=2)

        # append down-sampled SWIR2 band to the other 10m bands
        im_ms = np.append(im_ms, im_swir2, axis=2)

        # create cloud mask using 60m QA band (not as good as Landsat cloud cover)
        fn_mask = fn[3]
        data = gdal.Open(fn_mask, gdal.GA_ReadOnly)
        bands = [data.GetRasterBand(k + 1).ReadAsArray() for k in range(data.RasterCount)]
        im_QA = bands[0]
        # compute cloud mask using QA60 band
        cloud_mask_QA60 = SDS_preprocess.create_cloud_mask(im_QA, satname, cloud_mask_issue)
        # compute cloud mask using s2cloudless probability band
        cloud_mask_s2cloudless = SDS_preprocess.create_s2cloudless_mask(cloud_prob, s2cloudless_prob)
        # combine both cloud masks
        cloud_mask = np.logical_or(cloud_mask_QA60,cloud_mask_s2cloudless)
        
        # check if -inf or nan values on any band and create nodata image
        im_nodata = np.zeros(cloud_mask.shape).astype(bool)
        for k in range(im_ms.shape[2]):
            im_inf = np.isin(im_ms[:,:,k], -np.inf)
            im_nan = np.isnan(im_ms[:,:,k])
            im_nodata = np.logical_or(np.logical_or(im_nodata, im_inf), im_nan)
        # add the edges of the SWIR1 band that contains only 0's to the nodata image
        # these are created when reprojecting the SWIR1 20 m band onto the 10m pixel grid
        im_nodata = SDS_preprocess.pad_edges(im_swir1, im_nodata)        
        im_nodata = SDS_preprocess.pad_edges(im_swir2, im_nodata)        
        # check if there are pixels with 0 intensity in the Green, NIR and SWIR bands and add those
        # to the cloud mask as otherwise they will cause errors when calculating the NDWI and MNDWI
        im_zeros = np.ones(im_nodata.shape).astype(bool)
        im_zeros = np.logical_and(np.isin(im_ms[:,:,1],0), im_zeros) # Green
        im_zeros = np.logical_and(np.isin(im_ms[:,:,3],0), im_zeros) # NIR
        im_zeros = np.logical_and(np.isin(im_ms[:,:,4],0), im_zeros) # SWIR
        # add to im_nodata
        im_nodata = np.logical_or(im_zeros, im_nodata)
        # dilate if image was merged as there could be issues at the edges
        if 'merged' in fn_ms:
            im_nodata = morphology.dilation(im_nodata,morphology.square(5))

        # update cloud mask with all the nodata pixels
        cloud_mask = np.logical_or(cloud_mask, im_nodata)

        # no extra image
        im_extra = []

    return im_ms, georef, cloud_mask, im_extra, im_QA, im_nodata

def create_folder_structure(im_folder, satname):
    """
    Create the structure of subfolders for each satellite mission

    KV WRL 2018

    Arguments:
    -----------
    im_folder: str
        folder where the images are to be downloaded
    satname:
        name of the satellite mission

    Returns:
    -----------
    filepaths: list of str
        filepaths of the folders that were created
    """

    # one folder for the metadata (common to all satellites)
    filepaths = [os.path.join(im_folder, satname, 'meta')]
    # subfolders depending on satellite mission
    if satname == 'L5':
        filepaths.append(os.path.join(im_folder, satname, 'ms'))
        filepaths.append(os.path.join(im_folder, satname, 'mask'))
    elif satname in ['L7','L8','L9']:
        filepaths.append(os.path.join(im_folder, satname, 'ms'))
        filepaths.append(os.path.join(im_folder, satname, 'pan'))
        filepaths.append(os.path.join(im_folder, satname, 'mask'))
    elif satname in ['S2']:
        filepaths.append(os.path.join(im_folder, satname, 'ms'))
        filepaths.append(os.path.join(im_folder, satname, 'swir1'))
        filepaths.append(os.path.join(im_folder, satname, 'swir2'))
        filepaths.append(os.path.join(im_folder, satname, 'mask'))
    # create the subfolders if they don't exist already
    for fp in filepaths:
        if not os.path.exists(fp): os.makedirs(fp)

    return filepaths

def get_filenames(filename, filepath, satname):
    if satname == 'L5':
        fn_mask = filename.replace('ms.tif','mask.tif')
        fn = [os.path.join(filepath[0], filename),
              os.path.join(filepath[1], fn_mask)]
    if satname in ['L7','L8','L9']:
        fn_pan = filename.replace('ms.tif','pan.tif')
        fn_mask = filename.replace('ms.tif','mask.tif')
        fn = [os.path.join(filepath[0], filename),
              os.path.join(filepath[1], fn_pan),
              os.path.join(filepath[2], fn_mask)]
    if satname == 'S2':
        fn_swir1 = filename.replace('_ms','_swir1')
        fn_swir2 = filename.replace('_ms','_swir2')
        fn_mask = filename.replace('_ms','_mask')
        fn = [os.path.join(filepath[0], filename),
              os.path.join(filepath[1], fn_swir1),
              os.path.join(filepath[2], fn_swir2),
              os.path.join(filepath[3], fn_mask)]
        
    return fn


def get_filepath(inputs,satname):
    sitename = inputs['sitename']
    filepath_data = inputs['filepath']
    # access the images
    if satname == 'L5':
        # access downloaded Landsat 5 images
        fp_ms = os.path.join(filepath_data, satname, 'ms')
        fp_mask = os.path.join(filepath_data, satname, 'mask')
        filepath = [fp_ms, fp_mask]
    elif satname in ['L7','L8','L9']:
        # access downloaded Landsat 7 images
        fp_ms = os.path.join(filepath_data, satname, 'ms')
        fp_pan = os.path.join(filepath_data, satname, 'pan')
        fp_mask = os.path.join(filepath_data, satname, 'mask')
        filepath = [fp_ms, fp_pan, fp_mask]
    elif satname == 'S2':
        # access downloaded Sentinel 2 images
        fp_ms = os.path.join(filepath_data, satname, 'ms')
        fp_swir1 = os.path.join(filepath_data, satname, 'swir1')
        fp_swir2 = os.path.join(filepath_data, satname, 'swir2')
        fp_mask = os.path.join(filepath_data, satname, 'mask')
        filepath = [fp_ms, fp_swir1, fp_swir2, fp_mask]
            
    return filepath

def find_wl_contours1(im, cloud_mask, im_ref_buffer, threshold):
    nrows = cloud_mask.shape[0]
    ncols = cloud_mask.shape[1]
    # use im_ref_buffer and dilate it by 5 pixels
    se = morphology.disk(5)
    im_ref_buffer_extra = morphology.binary_dilation(im_ref_buffer,se)
    vec_buffer = im_ref_buffer_extra.reshape(nrows*ncols)
    # reshape spectral index image to vector
    vec_ndwi = im.reshape(nrows*ncols)
    # keep pixels that are in the buffer and not in the cloud mask
    vec_mask = cloud_mask.reshape(nrows*ncols)
    vec = vec_ndwi[np.logical_and(vec_buffer,~vec_mask)]
    vec = vec[~np.isnan(vec)]
    
    # use Marching Squares algorithm to detect contours on ndwi image
    im_buffer = np.copy(im)
    im_buffer[~im_ref_buffer] = np.nan
    contours = measure.find_contours(im_buffer, threshold)
    # remove contours that contain NaNs (due to cloud pixels in the contour)
    contours = SDS_shoreline.process_contours(contours)

    return contours

def pansharpen(im_ms, im_pan, cloud_mask):
    """
    Pansharpens a multispectral image, using the panchromatic band and a cloud mask.
    A PCA is applied to the image, then the 1st PC is replaced, after histogram
    matching with the panchromatic band. Note that it is essential to match the
    histrograms of the 1st PC and the panchromatic band before replacing and
    inverting the PCA.

    KV WRL 2018

    Arguments:
    -----------
    im_ms: np.array
        Multispectral image to pansharpen (3D)
    im_pan: np.array
        Panchromatic band (2D)
    cloud_mask: np.array
        2D cloud mask with True where cloud pixels are

    Returns:
    -----------
    im_ms_ps: np.ndarray
        Pansharpened multispectral image (3D)

    """
    # check that cloud cover is not too high otherwise pansharpening fails
    if sum(sum(cloud_mask)) > 0.95*cloud_mask.shape[0]*cloud_mask.shape[1]:
        return im_ms
    
    # reshape image into vector and apply cloud mask
    vec = im_ms.reshape(im_ms.shape[0] * im_ms.shape[1], im_ms.shape[2])
    vec_mask = cloud_mask.reshape(im_ms.shape[0] * im_ms.shape[1])
    vec = vec[~vec_mask, :]
    # apply PCA to multispectral bands
    pca = decomposition.PCA()
    vec_pcs = pca.fit_transform(vec)
    del vec

    # replace 1st PC with pan band (after matching histograms)
    vec_pan = im_pan.reshape(im_pan.shape[0] * im_pan.shape[1])
    vec_pan = vec_pan[~vec_mask]
    vec_pcs[:,0] = SDS_preprocess.hist_match(vec_pan, vec_pcs[:,0])
    vec_ms_ps = pca.inverse_transform(vec_pcs)
    del vec_pcs
    del vec_pan

    # reshape vector into image
    vec_ms_ps_full = np.ones((len(vec_mask), im_ms.shape[2])) * np.nan
    vec_ms_ps_full[~vec_mask,:] = vec_ms_ps
    im_ms_ps = vec_ms_ps_full.reshape(im_ms.shape[0], im_ms.shape[1], im_ms.shape[2])

    return im_ms_ps

# returns all intersections between given transect and shoreline
def get_intersections(transect, sl, settings):

    # compute rotation matrix
    temp = np.array(transect[-1,:]) - np.array(transect[0,:])
    phi = np.arctan2(temp[1], temp[0])
    Mrot = np.array([[np.cos(phi), np.sin(phi)],[-np.sin(phi), np.cos(phi)]])

    # calculate point to line distance between shoreline points and the transect
    p0 = transect[0,:]
    p1 = transect[-1,:]
    d_line = np.abs(np.cross(p1-p0,sl-p0)/np.linalg.norm(p1-p0))

    # calculate the distance between shoreline points and the origin of the transect
    d_origin = np.linalg.norm(sl - p0, axis=1)

    # find the shoreline points that are close to the transects and to the origin
    # the distance to the origin is hard-coded here to 1 km 
    search_limit = np.linalg.norm(p1 - p0) + settings['past_dist']
    idx_dist = np.logical_and(d_line <= settings['along_dist'], d_origin <= search_limit) # note: this technically gives the collider a rounded end
    idx_close = np.where(idx_dist)[0]
    
    # if no shoreline points close to the transect 
    if len(idx_close) == 0:
        return None

    # change of base to shore-normal coordinate system
    X0 = p0[0] # x and y of transect origin
    Y0 = p0[1]
    xy_close = np.array([sl[idx_close,0],sl[idx_close,1]]) - np.tile(np.array([[X0],
                        [Y0]]), (1,len(sl[idx_close])))
    
    xy_rot = np.matmul(Mrot, xy_close)

    # remove points that are too far landwards relative to the transect origin (i.e., negative chainage)
    # xy_rot[0, xy_rot[0,:] < settings['min_chainage']] = np.nan
    xy_rot = xy_rot[:, xy_rot[0,:] >= settings['min_chainage']]

    # if all intersections are too far landwards
    if np.all(np.isnan(xy_rot[0,:])):
        return None
    
    return xy_rot