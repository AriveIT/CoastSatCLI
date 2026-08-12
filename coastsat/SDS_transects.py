"""
This module contains functions to analyze the 2D shorelines along shore-normal
transects
    
Author: Kilian Vos, Water Research Laboratory, University of New South Wales
"""

# load modules
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import pytz
import pdb
import pickle
from pathlib import Path
import timeit

# other modules
import skimage.transform as transform
from pylab import ginput
from scipy import stats
from scipy.spatial import cKDTree

# CoastSat modules
from coastsat import SDS_tools, CASS, CASS_V2

# Global variables
DAYS_IN_YEAR = 365.2425
SECONDS_IN_DAY = 24*3600


###################################################################################################
# DRAW/LOAD TRANSECTS
###################################################################################################

def create_transect(origin, orientation, length):
    """
    Create a transect given an origin, orientation and length.
    Points are spaced at 1m intervals.
    
    KV WRL 2018
    
    Arguments:
    -----------
    origin: np.array
        contains the X and Y coordinates of the origin of the transect
    orientation: int
        angle of the transect (anti-clockwise from North) in degrees
    length: int
        length of the transect in metres
        
    Returns:    
    -----------
    transect: np.array
        contains the X and Y coordinates of the transect
        
    """   
    
    # origin of the transect
    x0 = origin[0]
    y0 = origin[1]
    # orientation of the transect
    phi = (90 - orientation)*np.pi/180 
    # create a vector with points at 1 m intervals
    x = np.linspace(0,length,length+1)
    y = np.zeros(len(x))
    coords = np.zeros((len(x),2))
    coords[:,0] = x
    coords[:,1] = y 
    # translate and rotate the vector using the origin and orientation
    tf = transform.EuclideanTransform(rotation=phi, translation=(x0,y0))
    transect = tf(coords)
                
    return transect

def draw_transects(output, settings):
    """
    Draw shore-normal transects interactively on top of the mapped shorelines

    KV WRL 2018       

    Arguments:
    -----------
    output: dict
        contains the extracted shorelines and corresponding metadata
    settings: dict with the following keys
        'inputs': dict
            input parameters (sitename, filepath, polygon, dates, sat_list)
            
    Returns:    
    -----------
    transects: dict
        contains the X and Y coordinates of all the transects drawn.
        Also saves the coordinates as a .geojson as well as a .jpg figure 
        showing the location of the transects.       
    """   
    
    sitename = settings['inputs']['sitename']
    filepath = settings['inputs']['filepath']

    # plot the mapped shorelines
    fig1 = plt.figure()
    ax1 = fig1.add_subplot(111)
    ax1.axis('equal')
    ax1.set_xlabel('Eastings [m]')
    ax1.set_ylabel('Northings [m]')
    ax1.grid(linestyle=':', color='0.5')
    for i in range(len(output['shorelines'])):
        sl = output['shorelines'][i]
        date = output['dates'][i]
        ax1.plot(sl[:, 0], sl[:, 1], '.', markersize=3, label=date.strftime('%d-%m-%Y'))
#    ax1.legend()
    fig1.set_tight_layout(True)
    mng = plt.get_current_fig_manager()                                         
    mng.window.showMaximized()
    ax1.set_title('Click two points to define each transect (first point is the ' +
                  'origin of the transect and is landwards, second point seawards).\n'+
                  'When all transects have been defined, click on <ENTER>', fontsize=16)
    
    # initialise transects dict
    transects = dict([])
    counter = 0
    # loop until user breaks it by click <enter>
    while 1:
        # let user click two points
        pts = ginput(n=2, timeout=-1)
        if len(pts) > 0:
            origin = pts[0]
        # if user presses <enter>, no points are selected
        else:
            # save figure as .jpg
            fig1.gca().set_title('Transect locations', fontsize=16)
            fig1.savefig(os.path.join(filepath, 'jpg_files', sitename + '_transect_locations.jpg'), dpi=200)
            plt.title('Transect coordinates saved as ' + sitename + '_transects.geojson')
            plt.draw()
            # wait 2 seconds for user to visualise the transects that are saved
            ginput(n=1, timeout=2, show_clicks=True)
            plt.close(fig1)
            # break the loop
            break
        
        # add selectect points to the transect dict
        counter = counter + 1
        transect = np.array([pts[0], pts[1]])
        
        # alternative of making the transect the origin, orientation and length
#        temp = np.array(pts[1]) - np.array(origin)
#        phi = np.arctan2(temp[1], temp[0])
#        orientation = -(phi*180/np.pi - 90)
#        length = np.linalg.norm(temp)
#        transect = create_transect(origin, orientation, length)
        
        transects[str(counter)] = transect
        
        # plot the transects on the figure
        ax1.plot(transect[:,0], transect[:,1], 'b-', lw=2.5)
        ax1.plot(transect[0,0], transect[0,1], 'rx', markersize=10)
        ax1.text(transect[-1,0], transect[-1,1], str(counter), size=16,
                 bbox=dict(boxstyle="square", ec='k',fc='w'))
        plt.draw()
        
    # save transects.geojson
    gdf = SDS_tools.transects_to_gdf(transects)
    # set projection
    gdf.crs = {'init':'epsg:'+str(settings['output_epsg'])}
    # save as geojson    
    gdf.to_file(os.path.join(filepath, sitename + '_transects.geojson'), driver='GeoJSON', encoding='utf-8')
    # print the location of the files
    print('Transect locations saved in ' + filepath)
        
    return transects

###################################################################################################
# COMPUTE INTERSECTIONS
###################################################################################################

def compute_intersection_QC(output, transects, settings):
    """
    More advanced function to omputes the intersection between the 2D mapped shorelines 
    and the transects. Produces more quality-controlled time-series of shoreline change.
    
    Arguments:
    -----------
        output: dict
            contains the extracted shorelines and corresponding dates.
        transects: dict
            contains the X and Y coordinates of the transects (first and last point needed for each
            transect).
        settings: dict
                'along_dist': int (in metres)
                    alongshore distance to caluclate the intersection (median of points 
                    within this distance). 
                'min_points': int 
                    minimum number of shoreline points to calculate an intersections
                'max_std': int (in metres)
                    maximum std for the shoreline points when calculating the median, 
                    if above this value then NaN is returned for the intersection
                'max_range': int (in metres)
                    maximum range  for the shoreline points when calculating the median, 
                    if above this value then NaN is returned for the intersection
                'min_chainage': int (in metres)
                    furthest landward of the transect origin that an intersection is 
                    accepted, beyond this point a NaN is returned
                        
    Returns:    
    -----------
        cross_dist: dict
            time-series of cross-shore distance along each of the transects. These are not tidally 
            corrected.
        
    """
    ts = np.array(list(transects.values()))
    transect_cache = {} # stores transects converted to pixel spaces
    shorelines = output['shorelines']
    sl_norms = output['shoreline_norms']
    objects_per_file = 50 

    # initialise variables
    def init_var():
        return np.full((len(shorelines), len(transects.keys())), np.nan)
    std_intersect = init_var()
    med_intersect = init_var()
    max_intersect = init_var()
    min_intersect = init_var()
    n_intersect = init_var()

    rejection_counts = init_var()

    # loop through each shoreline
    n = len(shorelines)
    last_obj_idx = 0
    if settings["plot_sat"]: im_data = load_objects(settings, last_obj_idx, objects_per_file, n, "im_data", "im_data")
    for sl_idx in range(len(shorelines)):
        print(f'\rProcessing shoreline {sl_idx + 1} out of {str(n)}...', end='')
        sl = shorelines[sl_idx]
        sl_norm = sl_norms[sl_idx]

        # load next cloud kd tree file
        cur = sl_idx // objects_per_file
        if cur != last_obj_idx:
            if settings["plot_sat"]: im_data = load_objects(settings, cur, objects_per_file, n, "im_data", "im_data")
            last_obj_idx = cur

        if settings.get('CASS', False):
            obj_idx = sl_idx - objects_per_file * last_obj_idx
            if settings.get('plot_sat', False):
                im_datum = im_data[obj_idx]
            else:
                im_datum = None

            cache_key = (tuple(np.round(im_datum[1], 6)), tuple(im_datum[2]))
            if cache_key in transect_cache.keys():
                pix_transects = transect_cache[cache_key]
            else:
                transects_0_pxl = SDS_tools.convert_world2pix(SDS_tools.convert_epsg(ts[:,0,:], settings["output_epsg"], im_datum[2]), im_datum[1])
                transects_1_pxl = SDS_tools.convert_world2pix(SDS_tools.convert_epsg(ts[:,1,:], settings["output_epsg"], im_datum[2]), im_datum[1])
                pix_transects = np.swapaxes(np.stack([transects_0_pxl, transects_1_pxl]), 0, 1)
                transect_cache[cache_key] = pix_transects

        # loop through each transect
        for transect_idx, key in enumerate(transects.keys()):

            intersections, normals, intersecting_sl = CASS_V2.get_intersections(transects[key], sl, sl_norm, settings)

            if intersections is None:
                rejection_counts[sl_idx, transect_idx] = CASS_V2.NO_INTERSECTIONS
                continue

            if settings.get('CASS', False):

                intersections, dotprods, info = CASS_V2.shoreline_selection(
                    intersections,
                    normals,
                    pix_transects[transect_idx],
                    settings['clustering_threshold']
                )

                if intersections is None:
                    rejection_counts[sl_idx, transect_idx] = info
                    continue

                # plot intersections and other clustering alg related info
                if key in settings.get('transects_to_plot', []): # and c_info > 0:
                    CASS_V2.plot_intersections(key, sl, intersecting_sl, normals, dotprods, transects[key], str(output['dates'][sl_idx])[:10], settings, im_datum)

            # compute std, median, max, min of the intersections (for current transect-shoreline pair)
            std_intersect[sl_idx, transect_idx] = np.nanstd(intersections)
            med_intersect[sl_idx, transect_idx] = np.nanmedian(intersections)
            max_intersect[sl_idx, transect_idx] = np.nanmax(intersections)
            min_intersect[sl_idx, transect_idx] = np.nanmin(intersections)
            n_intersect[sl_idx, transect_idx] = np.sum(~np.isnan(intersections))  # count only non-nan values
           
    # quality control the intersections using dispersion metrics (std and range) and # points
    nan_before = np.isnan(med_intersect)
    condition1 = std_intersect <= settings['max_std']
    condition2 = (max_intersect - min_intersect) <= settings['max_range']
    condition3 = n_intersect >= settings['min_points']
    idx_good = np.logical_and(np.logical_and(condition1, condition2), condition3)
    
    med_intersect[~idx_good] = np.nan
    # med_intersect[~idx_good] = min_intersect[~idx_good]
    # med_intersect[~condition3] = np.nan


    # save intersections for each transect in dictionary
    cross_dist = {key: med_intersect[:,transect_idx] for transect_idx, key in enumerate(transects.keys())}
    
    # plot why intersections were rejected for each transect and shoreline
    if settings.get("plot_rejection_counts", False) and settings.get('CASS', False):
        nan_after = np.isnan(med_intersect)
        dispersion_rejections = np.logical_and(nan_after, ~nan_before)
        rejection_counts[dispersion_rejections] = CASS_V2.DISPERSION
        CASS_V2.plot_rejection_counts(rejection_counts, settings['output_dir'])

    print()
    return cross_dist


def load_objects(settings, idx, objects_per_file, n_shorelines, dir_name, object_name):
    start = idx * objects_per_file
    end = min((idx + 1) * objects_per_file, n_shorelines)
    fn = f"{settings['sitename']}_{object_name}_{start}_{end}.pkl"

    cache_path = Path(settings["output_dir"]) / dir_name / fn

    try:
        with cache_path.open("rb") as f:
            objects = pickle.load(f)
    except FileNotFoundError:
        raise Exception(f"Pickle file {fn} in {cache_path} unable to load")
    return objects


###################################################################################################
# DESPIKING/OUTLIER REMOVAL
###################################################################################################

def reject_outliers(cross_distance, output, settings):
    """
    
    Arguments:
    -----------
        cross_distance: dict
            time-series of shoreline change
        output: dict
            mapped shorelines with metadata
        settings: dict
                'max_cross_change': int (in metres)
                    maximum cross-shore change observable between consecutive timesteps
                'otsu_threshold': tuple (min_t, max_t)
                    min and max intensity threshold use for contouring the shoreline
                        
    Returns:    
    ----------- 
        chain_dict: dict
            contains the updated time-series of cross-shore distance with the corresponding dates
        
    """
    
    chain_dict = dict([])
    outlier_stats = np.zeros((3, len(cross_distance.keys()))) # track good, spike, otsu counts

    print("Cleaning time series data (removing outliers)...")

    if settings['plot_fig']:
        os.makedirs(f"{settings['plot_dir']}\\outlier_rejection", exist_ok=True)

    for i,key in enumerate(list(cross_distance.keys())):
        chainage = cross_distance[key].copy()
        if sum(np.isnan(chainage)) == len(chainage):
            print(f'--> {key}: has no intersections')
            chain_dict[key] = chainage
            continue

        # 1. Remove nans and negative chainages
        idx_nonan = np.where(~np.isnan(chainage))[0]
        chainage1 = [chainage[k] for k in idx_nonan]
        dates1 = [output['dates'][k] for k in idx_nonan]

        # satnames1 = [output['satname'][k] for k in idx_nonan]

        # 2. Remove points where the MNDWI threshold is above a certain value (max_threshold)
        if np.isnan(settings['otsu_threshold'][0]):
            chainage2 = chainage1
            dates2 = dates1
        else:
            threshold1 = [output['MNDWI_threshold'][k] for k in idx_nonan]
            idx_thres = np.where(np.logical_and(np.array(threshold1) <= settings['otsu_threshold'][1],
                                                np.array(threshold1) >= settings['otsu_threshold'][0]))[0]
            chainage2 = [chainage1[k] for k in idx_thres]
            dates2 = [dates1[k] for k in idx_thres]

        # 3. Remove outliers based on despiking [iterative method]
        if len(chainage2) <= 1: # identify_outliers crashes if only 1 observation (also can't have outlier if only 1 obs)
            print(f"Warning: {key} has only {len(chainage2)} valid intersections, results may be untrustworthy")
            chainage3 = chainage2
            dates3 = dates2
        else:
            chainage3, dates3 = identify_outliers(chainage2, dates2, settings['max_cross_change'])
            if len(chainage3) < 30:
                print(f"Warning: {key} has only {len(chainage3)} valid intersections, results may be untrustworthy")

        # fill with nans the indices to be removed from cross_distance
        idx_kept = []
        if len(output['dates']) != len(chainage):
            output_dates_trimmed = output['dates'][:len(chainage)]
        else:
            output_dates_trimmed = output['dates']
        idx_kept = [date in dates3 for date in output_dates_trimmed]
        chainage[~np.array(idx_kept)] = np.nan

        # store in chain_dict
        chain_dict[key] = chainage
        
        outlier_stats[0, i] = len(chainage3) # points in post-processed time-series
        outlier_stats[1, i] = len(chainage2) - len(chainage3) # spike
        outlier_stats[2, i] = len(chainage1) - len(chainage2) # otsu
        
        print('--> %s: Removed %d outliers'%(key, len(dates1) - len(dates3)))
        if settings['plot_fig']:
            plot_outlier_rejection(key, chainage1, chainage2, chainage3, dates1, dates2, dates3, settings['plot_dir'])

    if settings['plot_fig']:
        plot_outlier_counts(outlier_stats, len(output['dates']), settings['plot_dir'])

    return chain_dict

def identify_outliers(chainage, dates, cross_change, debug=False):
    """
    Remove outliers based on despiking [iterative method]
    
    Arguments:
    -----------
    chainage: list
        time-series of shoreline change
    dates: list of datetimes
        correspondings dates
    cross_change: float
        threshold distance to identify a point as an outlier
        
    Returns:    
    ----------- 
    chainage_temp: list
        time-series of shoreline change without outliers
    dates_temp: list of datetimes
        dates without outliers
        
    """
    # make a copy of the inputs
    chainage_temp = chainage.copy()
    dates_temp = dates.copy()
    
    # loop through the time-series always starting from the start
    # when an outlier is found, remove it and restart
    # repeat until no more outliers are found in the time-series
    done = False
    while not done:

        # if all but last point has been removed, throw that one away too
        if len(chainage_temp) <= 1:
            chainage_temp.pop(k)
            dates_temp.pop(k)
            break

        for k in range(len(chainage_temp)):
            
            # check if the first point is an outlier
            if k == 0:
                # difference between 1st and 2nd point in the time-series
                diff = chainage_temp[k] - chainage_temp[k+1]
                if np.abs(diff) > cross_change:
                    chainage_temp.pop(k)  
                    dates_temp.pop(k)
                    break
                
            # check if the last point is an outlier
            elif k == len(chainage_temp)-1:
                done = True # now have looked through entire time-series
                # difference between last and before last point in the time-series
                diff = chainage_temp[k] - chainage_temp[k-1]
                if np.abs(diff) > cross_change:
                    chainage_temp.pop(k)  
                    dates_temp.pop(k) 
                    break
                
            # check if a point is an isolated outlier or in a group of 2 consecutive outliers
            else:  
                # calculate the difference with the data point before and after
                diff_m1 = chainage_temp[k] - chainage_temp[k-1]
                diff_p1 = chainage_temp[k] - chainage_temp[k+1]
                # remove point if isolated outlier, distant from both neighbours
                condition1 = np.abs(diff_m1) > cross_change
                condition2 = np.abs(diff_p1) > cross_change
                # check that distance from neighbours has the same sign 
                condition3 = np.sign(diff_p1) == np.sign(diff_m1)
                if np.logical_and(np.logical_and(condition1,condition2),condition3):
                    chainage_temp.pop(k)  
                    dates_temp.pop(k) 
                    break
                
                # check for 2 consecutive outliers in the time-series
                if k >= 2 and k < len(chainage_temp)-2:
                    
                    # calculate difference with the data around the neighbours of the point
                    diff_m2 = chainage_temp[k-1] - chainage_temp[k-2]
                    diff_p2 = chainage_temp[k+1] - chainage_temp[k+2]
                    # remove if there are 2 consecutive outliers (see conditions below)
                    condition4 = np.abs(diff_m2) > cross_change
                    condition5 = np.abs(diff_p2) > cross_change
                    condition6 = np.sign(diff_m1) == np.sign(diff_p2)
                    condition7 = np.sign(diff_p1) == np.sign(diff_m2)
                    # check for both combinations (1,5,6 and ,2,4,7)
                    if np.logical_and(np.logical_and(condition1,condition5),condition6):
                        chainage_temp.pop(k)  
                        dates_temp.pop(k) 
                        break
                    elif np.logical_and(np.logical_and(condition2,condition4),condition7):
                        chainage_temp.pop(k)  
                        dates_temp.pop(k) 
                        break
                    
                    # also look for clusters of 3 outliers
                    else:
                        # increase the distance to make sure these are really outliers
                        condition4b = np.abs(diff_m2) > 1.5*cross_change
                        condition5b = np.abs(diff_p2) > 1.5*cross_change
                        condition8 = np.sign(diff_m2) == np.sign(diff_p2)
                        # if point is close to immediate neighbours but 
                        # the neighbours are far from their neighbours, point is an outlier
                        if np.logical_and(np.logical_and(np.logical_and(condition4b,condition5b),
                                                         np.logical_and(~condition1,~condition2)),
                                                         condition8):
                            if debug: print('*', end='')
                            chainage_temp.pop(k)  
                            dates_temp.pop(k) 
                            break                                        
     
    # return the time-series where the outliers have been removed
    return chainage_temp, dates_temp

def plot_outlier_rejection(key, chainage1, chainage2, chainage3, dates1, dates2, dates3, plot_dir):
    # # only plot before
    # fig, ax = plt.subplots(1, 1, figsize=(12, 3), tight_layout=True)
    # ax.grid(linestyle=':', color='0.5')
    # ax.set(ylabel='distance [m]',
    #             title= 'Transect %s - %d points' % (key, len(chainage1)))
    # ax.plot(dates1, chainage1, 'C0-')
    # ax.plot(dates1, chainage1, 'C0o', ms=4, mfc='w', mec='C0')
    
    fig,ax=plt.subplots(2,1,figsize=[12,6], sharex=True)
    fig.set_tight_layout(True)
    ax[0].grid(linestyle=':', color='0.5')
    ax[0].set(ylabel='distance [m]',
                title= 'Transect %s original time-series - %d points' % (key, len(chainage1)))
    ax[1].grid(linestyle=':', color='0.5') 
    ax[1].set(ylabel='distance [m]',
                title= 'Post-processed time-series - %d points' % (len(chainage3)))
    
    # plot the data line
    ax[0].plot(dates1, chainage1, 'C0-')

    # plot points (and if they were rejected)
    ax[0].plot(dates1, chainage1, 'C2o', ms=4, mec='k', mew=0.7,label='otsu')
    ax[0].plot(dates2, chainage2, 'C3o', ms=4, mec='k', mew=0.7,label='spike')
    ax[0].plot(dates3, chainage3, 'C0o', ms=4, mfc='w', mec='C0')

    # plot the final time-series
    ax[1].plot(dates3, chainage3, 'C0-o', ms=4, mfc='w', mec='C0')

    ax[0].legend(ncol=2,loc='upper right')
    fig.savefig(f"{plot_dir}\\outlier_rejection\\{key}_outlier_rejection.png")
    plt.close(fig)

def plot_outlier_counts(outlier_stats, n_sl, dir):
    labels = ["good", "spike", "otsu"]
    colours = ["C0", "C3", "C2"] # consistency with other outlier plots
    n_transects = outlier_stats.shape[1]

    mean_outliers = np.sum(outlier_stats[[1, 2],:]) / n_transects
    mean_points = np.sum(outlier_stats) / n_transects

    total_points = np.sum(outlier_stats)
    outlier_percentage = np.sum(outlier_stats[[1, 2],:]) / total_points if total_points != 0 else 0



    fig, ax = plt.subplots(figsize=(12,8))
    fig.suptitle(f"Outlier rejection counts for each transect", fontsize=18)
    ax.set_title(f"Mean # points: {mean_points:.3f}, Mean # outliers: {mean_outliers:.3f}, Percentage of outliers: {outlier_percentage:.3f}", fontsize=10)
    ax.set_xlabel(f"transect index")
    ax.set_ylabel("counts")
    bottom = np.zeros(n_transects)
    x_pos = np.arange(1, n_transects + 1) # generated transect labels start at 1
    width=1

    for label, colour, counts in zip(labels, colours, outlier_stats):
        _ = ax.bar(x_pos, height=counts, width=width, label=label, bottom=bottom, color=colour)
        bottom += counts
    ax.axhline(n_sl, linestyle="--", color="k", label=f"total # shorelines")

    fig.legend(bbox_to_anchor=(0.5,0.0), loc='lower center', ncol=2)
    fig.tight_layout(rect=[0, 0.15, 1, 1]) # second value reserves some place for the legend to sit

    fig.savefig(f"{dir}\\outlier_rejection_counts.png")
    plt.close(fig)

###################################################################################################
# SEASONAL/MONTHLY AVERAGING
###################################################################################################

def seasonal_average(dates, chainages): 
    # define the 4 seasons
    months = ['-%02d'%_ for _ in np.arange(1,13)]
    seasons = np.array([1,4,7,10])
    season_labels = ['DJF', 'MAM', 'JJA', 'SON']
    # put time-series into a pd.dataframe (easier to process)
    df = pd.DataFrame({'dates': dates, 'chainage':chainages})
    df.set_index('dates', inplace=True) 
    # initialise variables for seasonal averages
    dict_seasonal = dict([])
    for k,j in enumerate(seasons):
        dict_seasonal[season_labels[k]] = {'dates':[], 'chainages':[]}
    dates_seasonal = []
    chainage_seasonal = []
    season_ts = []
    for year in np.unique(df.index.year):
        # 4 seasons: DJF, MMA, JJA, SON
        for k,j in enumerate(seasons):
            # middle date
            date_seas = pytz.utc.localize(datetime(year,j,1))
            # if j == 1: date_seas = pytz.utc.localize(datetime(year-1,12,31))
            # for the first season, take the December data from the year before
            if j == 1:
                chain_seas = np.array(df[str(year-1) + months[(j-1)-1]:str(year) + months[(j-1)+1]]['chainage'])
            else:
                chain_seas = np.array(df[str(year) + months[(j-1)-1]:str(year) + months[(j-1)+1]]['chainage'])
            if len(chain_seas) == 0:
                continue
            else:
                dict_seasonal[season_labels[k]]['dates'].append(date_seas)
                dict_seasonal[season_labels[k]]['chainages'].append(np.mean(chain_seas))
                dates_seasonal.append(date_seas)
                chainage_seasonal.append(np.mean(chain_seas))
                season_ts.append(j)
    # convert chainages to np.array (easier to manipulate than a list)
    for seas in dict_seasonal.keys():
         dict_seasonal[seas]['chainages'] = np.array(dict_seasonal[seas]['chainages'])
                
    return dict_seasonal, dates_seasonal, np.array(chainage_seasonal), np.array(season_ts)

def monthly_average(dates, chainages):
    # define the 12 months
    months = ['-%02d'%_ for _ in np.arange(1,13)]
    seasons = np.arange(1,13)
    season_labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    # put time-series into a pd.dataframe (easier to process)
    df = pd.DataFrame({'dates': dates, 'chainage':chainages})
    df.set_index('dates', inplace=True) 
    # initialise variables for seasonal averages
    dict_seasonal = dict([])
    for k,j in enumerate(seasons):
        dict_seasonal[season_labels[k]] = {'dates':[], 'chainages':[]}
    dates_seasonal = []
    chainage_seasonal = []
    season_ts = []
    for year in np.unique(df.index.year):
        # 4 seasons: DJF, MMA, JJA, SON
        for k,j in enumerate(seasons):
            # middle date
            date_seas = pytz.utc.localize(datetime(year,j,15))
            if date_seas > dates[-1] - timedelta(days=30):
                break
            try:
                chain_seas = np.array(df[str(year)+months[k]:str(year)+months[k]]['chainage'])
            except:
                continue
            if len(chain_seas) == 0:
                continue
            else:
                dict_seasonal[season_labels[k]]['dates'].append(date_seas)
                dict_seasonal[season_labels[k]]['chainages'].append(np.mean(chain_seas))
                dates_seasonal.append(date_seas)
                chainage_seasonal.append(np.mean(chain_seas))
                season_ts.append(j)
    # convert chainages to np.array (easier to manipulate than a list)
    for seas in dict_seasonal.keys():
         dict_seasonal[seas]['chainages'] = np.array(dict_seasonal[seas]['chainages'])
                
    return dict_seasonal, dates_seasonal, np.array(chainage_seasonal), np.array(season_ts)

def calculate_trend(dates,chainage):
    "calculate long-term trend"
    dates_ord = np.array([_.toordinal() for _ in dates])
    dates_ord = (dates_ord - np.min(dates_ord))/DAYS_IN_YEAR   
    trend, intercept, rvalue, pvalue, std_err = stats.linregress(dates_ord, chainage)
    y = dates_ord*trend+intercept
    return trend, y, 1 - rvalue ** 2, std_err