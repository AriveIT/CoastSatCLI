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
from datetime import datetime, timedelta
import pytz
import pdb

# other modules
import skimage.transform as transform
from pylab import ginput
from scipy import stats

# CoastSat modules
from coastsat import SDS_tools

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

def compute_intersection(output, transects, settings):
    """
    Computes the intersection between the 2D shorelines and the shore-normal.
    transects. It returns time-series of cross-shore distance along each transect.
    
    KV WRL 2018       
    Arguments:
    -----------
    output: dict
        contains the extracted shorelines and corresponding metadata
    transects: dict
        contains the X and Y coordinates of each transect
    settings: dict with the following keys
        'along_dist': int
            alongshore distance considered caluclate the intersection
              
    Returns:    
    -----------
    cross_dist: dict
        time-series of cross-shore distance along each of the transects. 
        Not tidally corrected.        
    """    
    
    # loop through shorelines and compute the median intersection    
    intersections = np.zeros((len(output['shorelines']),len(transects)))
    for i in range(len(output['shorelines'])):

        sl = output['shorelines'][i]
        
        for j,key in enumerate(list(transects.keys())): 
            
            # compute rotation matrix
            X0 = transects[key][0,0]
            Y0 = transects[key][0,1]
            temp = np.array(transects[key][-1,:]) - np.array(transects[key][0,:])
            phi = np.arctan2(temp[1], temp[0])
            Mrot = np.array([[np.cos(phi), np.sin(phi)],[-np.sin(phi), np.cos(phi)]])
    
            # calculate point to line distance between shoreline points and the transect
            p1 = np.array([X0,Y0])
            p2 = transects[key][-1,:]
            d_line = np.abs(np.cross(p2-p1,sl-p1)/np.linalg.norm(p2-p1))
            # calculate the distance between shoreline points and the origin of the transect
            d_origin = np.array([np.linalg.norm(sl[k,:] - p1) for k in range(len(sl))])
            # find the shoreline points that are close to the transects and to the origin
            # the distance to the origin is hard-coded here to 1 km 
            idx_dist = np.logical_and(d_line <= settings['along_dist'], d_origin <= 200)
            # find the shoreline points that are in the direction of the transect (within 90 degrees)
            temp_sl = sl - np.array(transects[key][0,:])
            phi_sl = np.array([np.arctan2(temp_sl[k,1], temp_sl[k,0]) for k in range(len(temp_sl))])
            diff_angle = (phi - phi_sl)
            idx_angle = np.abs(diff_angle) < np.pi/2
            # combine the transects that are close in distance and close in orientation
            idx_close = np.where(np.logical_and(idx_dist,idx_angle))[0]     
            
            # in case there are no shoreline points close to the transect 
            if len(idx_close) == 0:
                intersections[i,j] = np.nan
            else:
                # change of base to shore-normal coordinate system
                xy_close = np.array([sl[idx_close,0],sl[idx_close,1]]) - np.tile(np.array([[X0],
                                   [Y0]]), (1,len(sl[idx_close])))
                xy_rot = np.matmul(Mrot, xy_close)
                # compute the median of the intersections along the transect
                intersections[i,j] = np.nanmedian(xy_rot[0,:])
    
    # fill the a dictionnary
    cross_dist = dict([])
    for j,key in enumerate(list(transects.keys())): 
        cross_dist[key] = intersections[:,j]   
    
    return cross_dist

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
                'multiple_inter': mode for removing outliers ('auto', 'nan', 'max')
                'auto_prc': percentage to use in 'auto' mode to switch from 'nan' to 'max'
                'd_origin_threshold': distance a shoreline points can be from transect origin and be counted as an intersection
                        
    Returns:    
    -----------
        cross_dist: dict
            time-series of cross-shore distance along each of the transects. These are not tidally 
            corrected.
        
    """      
    
    # initialise dictionary with intersections for each transect
    cross_dist = dict([])
    
    shorelines = output['shorelines']
    along_dist = settings['along_dist']

    # loop through each transect
    n = len(transects.keys())
    for key in transects.keys():
        print(f'\rProcessing {key} out of {str(n)}...', end='')
        
        # initialise variables
        std_intersect = np.zeros(len(shorelines))
        med_intersect = np.zeros(len(shorelines))
        max_intersect = np.zeros(len(shorelines))
        min_intersect = np.zeros(len(shorelines))
        prc_intersect = np.zeros(len(shorelines))
        n_intersect = np.zeros(len(shorelines))

        ema = np.nan # exponential moving average
        alpha = 0.1 # how much to weight most recent centroid
        bad_intersection_count = 0

        # loop through each shoreline
        for i in range(len(shorelines)):

            sl = shorelines[i]
            
            # compute rotation matrix
            X0 = transects[key][0,0]
            Y0 = transects[key][0,1]
            temp = np.array(transects[key][-1,:]) - np.array(transects[key][0,:])
            phi = np.arctan2(temp[1], temp[0])
            Mrot = np.array([[np.cos(phi), np.sin(phi)],[-np.sin(phi), np.cos(phi)]])
    
            # calculate point to line distance between shoreline points and the transect
            p1 = np.array([X0,Y0])
            p2 = transects[key][-1,:]
            d_line = np.abs(np.cross(p2-p1,sl-p1)/np.linalg.norm(p2-p1))
            # calculate the distance between shoreline points and the origin of the transect
            d_origin = np.linalg.norm(sl - p1, axis=1)
            # find the shoreline points that are close to the transects and to the origin
            # the distance to the origin is hard-coded here to 1 km 
            search_limit = np.linalg.norm(transects[key][-1,:] - transects[key][0,:]) + settings['past_dist']
            idx_dist = np.logical_and(d_line <= along_dist, d_origin <= search_limit)
            idx_close = np.where(idx_dist)[0]
            
            # in case there are no shoreline points close to the transect 
            if len(idx_close) == 0:
                std_intersect[i] = np.nan
                med_intersect[i] = np.nan
                max_intersect[i] = np.nan
                min_intersect[i] = np.nan
                prc_intersect[i] = np.nan
                n_intersect[i] = np.nan
            else:
                # change of base to shore-normal coordinate system
                xy_close = np.array([sl[idx_close,0],sl[idx_close,1]]) - np.tile(np.array([[X0],
                                   [Y0]]), (1,len(sl[idx_close])))
                xy_rot = np.matmul(Mrot, xy_close)
                # remove points that are too far landwards relative to the transect origin (i.e., negative chainage)
                xy_rot[0, xy_rot[0,:] < settings['min_chainage']] = np.nan
                
                if settings.get('cluster_intersection_selection', False):
                    transect_class = output['transect_origin_classes'][i][key_to_idx(key)]
                    clusters, centroids, c_idx = cluster_intersection_selection(
                        intersections = xy_rot[0,~np.isnan(xy_rot[0,:])],
                        clustering_threshold = settings['clustering_threshold'],
                        transect_class = transect_class
                    )
                    
                    # if no clusters found (or bad case)
                    if clusters[c_idx].size == 0:
                        std_intersect[i] = np.nan
                        med_intersect[i] = np.nan
                        max_intersect[i] = np.nan
                        min_intersect[i] = np.nan
                        prc_intersect[i] = np.nan
                        n_intersect[i] = np.nan
                        bad_intersection_count += 1
                        continue
                    
                    ema = update_ema(ema, alpha, centroids[c_idx]) # not sure if this is useful yet

                    # plot intersections and other clustering alg related info
                    if key in settings.get('transects_to_plot', []):
                        plot_intersections(
                            xy_rot[0,:],
                            key,
                            sl,
                            i,
                            transects[key][0,:],
                            transects[key][-1,:],
                            settings['min_chainage'],
                            settings['past_dist'],
                            along_dist,
                            centroids,
                            output['dates'][i],
                            c_idx,
                            transect_class,
                            ema,
                            settings['transect_plot_dir'])
                        pass

                    intersections = clusters[c_idx]
                else:
                    intersections = xy_rot[0,:]

                # compute std, median, max, min of the intersections
                std_intersect[i] = np.nanstd(intersections)
                med_intersect[i] = np.nanmedian(intersections)
                max_intersect[i] = np.nanmax(intersections)
                min_intersect[i] = np.nanmin(intersections)
                prc_intersect[i] = np.nanpercentile(intersections, settings['min_prc'])
                n_intersect[i] = np.sum(~np.isnan(intersections))  # count only non-nan values

                
        # quality control the intersections using dispersion metrics (std and range)
        condition1 = std_intersect <= settings['max_std']
        condition2 = (max_intersect - min_intersect) <= settings['max_range']
        condition3 = n_intersect >= settings['min_points']
        idx_good = np.logical_and(np.logical_and(condition1, condition2), condition3)
        # print(sum(~idx_good), bad_intersection_count)

        # save copy for QA plot later
        # med_intersect_temp = med_intersect.copy()
        # max_intersect_temp = max_intersect.copy()
        
        # decide what to do with the intersections with high dispersion 
        if settings['multiple_inter'] == 'auto':
            # compute the percentage of data points where the std is larger than the user-defined max
            prc_over = np.sum(std_intersect > settings['max_std'])/len(std_intersect)
            # if more than a certain percentage is above, use the maximum intersection
            if prc_over > settings['auto_prc']:
                med_intersect[~idx_good] = max_intersect[~idx_good]
                med_intersect[~condition3] = np.nan
            # otherwise put a nan
            else:
                med_intersect[~idx_good] = np.nan
                
        elif settings['multiple_inter'] == 'max':
            med_intersect[~idx_good] = max_intersect[~idx_good]
            med_intersect[~condition3] = np.nan
            prc_over = 0
            
        elif settings['multiple_inter'] == 'nan':
            med_intersect[~idx_good] = np.nan
            prc_over = 0

        elif settings['multiple_inter'] == 'min':
            med_intersect[~idx_good] = prc_intersect[~idx_good]
            med_intersect[~condition3] = np.nan
            prc_over = 0

        
        else:
            raise Exception('the multiple_inter parameter can only be: nan, max or auto')

        # store in dict
        cross_dist[key] = med_intersect

        # plot for troubleshooting
        # if settings['plot_fig']:
        #     fig,ax=plt.subplots(1,1,figsize=[12,4])
        #     fig.set_tight_layout(True)
        #     ax.grid(linestyle=':', color='0.5')
        #     ax.plot(output['dates'], med_intersect_temp, 'o-', c='0.6', ms=3, label='median')
        #     ax.plot(output['dates'], max_intersect_temp, 'o-', c='g', ms=3, label='max')        
        #     ax.plot(output['dates'], cross_dist[key], 'o', c='r', ms=3, label='final')
        #     ax.set_title('%s - %.2f'%(key, prc_over))
        #     ax.legend(loc=3)
        #     print('%s  - removed %d'%(key, sum(np.isnan(med_intersect))))

    print()
    return cross_dist


def update_ema(ema, alpha, new_value):
    if np.isnan(new_value): return ema
    if np.isnan(ema): return new_value
    return new_value * alpha + ema * (1-alpha)


# assuming key is "transect_xxx", return xxx - 1 as an int
def key_to_idx(key):
    return int(key.split("_")[1]) - 1


###################################################################################################
# Cluster Intersection Selection Algorithm
###################################################################################################

def cluster_intersection_selection(intersections, clustering_threshold, transect_class):
    clusters = cluster1d(intersections, threshold=clustering_threshold)
    centroids = np.array([np.mean(c) for c in clusters])
    
    if len(clusters) == 2 and transect_class != -1:
        centroid_idx = select_centroid(centroids, transect_class)
        return clusters, centroids, centroid_idx
    elif len(centroids) == 1:
        centroid_idx = 0
        return clusters, centroids, centroid_idx
    
    # if more than 2 or 0 clusters, or 2 clusters and transect_class is invalid
    # then this alg doesn't work so we return nothing
    # if 3 clusters is a common case (and consistently not noise), should consider adding handling
    return np.array([[]]), np.nan, -1 # make np array have same shape just in case
    

# simple gap based 1d clustering based on given threshold
def cluster1d(intersections, threshold):
    sorted = np.sort(intersections)
    gaps = np.diff(sorted)
    idx = np.where(gaps > threshold)[0]
    clusters = np.split(sorted, idx + 1)
    return clusters


# transect_class = 1 --> transect origin is on water
# assumes exactly 2 centroids, and transect classes are valid (0 or 1)
# determines which shoreline to pick (first or second centroid)
def select_centroid(centroids, transect_class):
    return int(np.logical_xor(transect_class, np.logical_xor(centroids[0] > 0, centroids[1] > 0)))


###################################################################################################
# Intersection Plotting
###################################################################################################

"""
Plots:
    - Transect and collider
    - Intersections, centroids, with selected centroid marked
    - Shoreline points
    - EMA for reference
    - Transect origin, coloured based on class
    - Plots 2D version, and also projected onto transect
"""
def plot_intersections(intersections, key, sl, sl_idx, transect_p0, transect_p1, min_chainage, past_dist, along_dist, centroids,
                       date, centroid_idx, transect_class, ema, dir):
    origin_colormap = {
        -1 : 'gray',
        0 : 'green',
        1 : 'blue'
    }

    fig, axs = plt.subplots(1, 2)
    fig.suptitle(f'{key} vs shoreline {sl_idx} - {date}')

    # plot intersections and centroids in 1d scatterplot
    axs[0].plot(intersections, np.zeros_like(intersections), 'o', alpha=0.5, label="shoreline")
    axs[0].plot(centroids, np.zeros_like(centroids), 'o', c='black', label="centroids")

    # plot shoreline and transect
    axs[1].plot(sl[:, 0], sl[:, 1], ".", markersize=2)
    axs[1].plot([transect_p0[0], transect_p1[0]], [transect_p0[1], transect_p1[1]], alpha=0.5, label="transect")
    axs[1].plot([transect_p0[0]], [transect_p0[1]], 'o', c=origin_colormap[transect_class], markersize=5) # transect origin

    # plot collider
    collider = get_transect_collider(transect_p0, transect_p1, min_chainage, past_dist, along_dist)
    axs[1].plot(*collider, c='red', label="collider")

    # plot centroids on transect
    centroid_trans = get_centroids_along_transect(transect_p0, transect_p1, centroids)
    axs[1].plot(centroid_trans[:, 0], centroid_trans[:, 1], ".", c='black', markersize=6)

    # mark selected centroid
    if centroid_idx != -1:
        axs[0].scatter(centroids[centroid_idx], np.zeros_like(centroids[centroid_idx]), facecolors='none', edgecolors='black', s=200, label="selected")
        axs[1].scatter(centroid_trans[centroid_idx, 0], centroid_trans[centroid_idx, 1], facecolors='none', edgecolors='black', s=200)

    # plot ema
    axs[0].scatter(ema, np.zeros_like(ema), facecolors='none', edgecolors='purple', s=200, label="ema")
    ema_trans = get_centroids_along_transect(transect_p0, transect_p1, [ema])
    axs[1].scatter(ema_trans[:, 0], ema_trans[:, 1], facecolors='none', edgecolors='purple', s=200)

    # for better visibility
    # axs[1].axis('equal') # note: some centroids look off because of skew, but uncommenting this zooms out a lot (kinda ignores lims)
    x_lim, y_lim = get_plot_range(transect_p0, transect_p1)
    axs[1].set_xlim(x_lim[0], x_lim[1])
    axs[1].set_ylim(y_lim[0], y_lim[1])
    axs[0].get_yaxis().set_visible(False)

    fig.legend(bbox_to_anchor=(0.5,0.0), loc='lower center', ncol=3)
    fig.tight_layout(rect=[0, 0.15, 1, 1]) # second value reserves some place for the legend to sit
    
    filepath = f"{dir}\\{key}_intersection_plots"
    if not os.path.exists(filepath):
                os.mkdir(filepath)
    fig.savefig(f"{filepath}\\{key}_sl_{sl_idx}.png")


def get_centroids_along_transect(p0, p1, centroids):
    d = p1 - p0
    norm = d / np.linalg.norm(d)
    centroid_trans = np.array([p0 + c * norm for c in centroids])
    return centroid_trans


def get_transect_collider(p0, p1, min_chainage, past_dist, along_dist):
    d = p1 - p0
    norm = d / np.linalg.norm(d)
    orth = np.array([norm[1], -norm[0]])

    v1 = p1 + past_dist * norm - along_dist * orth
    v2 = p1 + past_dist * norm + along_dist * orth
    v3 = p0 + min_chainage * norm + along_dist * orth # min_chainage is already relative to origin (don't need to subtract)
    v4 = p0 + min_chainage * norm - along_dist * orth

    return ([v1[0], v2[0], v3[0], v4[0], v1[0]], [v1[1], v2[1], v3[1], v4[1], v1[1]])

def get_plot_range(p0, p1, buffer_ratio=1.5):
    x_max = max(p0[0], p1[0])
    x_min = min(p0[0], p1[0])
    x_range = x_max - x_min
    y_max = max(p0[1], p1[1])
    y_min = min(p0[1], p1[1])
    y_range = y_max - y_min

    # add buffer to bounding box proportional to x and y ranges
    x_lim = (x_min - buffer_ratio * x_range, x_max + buffer_ratio * x_range)
    y_lim = (y_min - buffer_ratio * y_range, y_max + buffer_ratio * y_range)

    return x_lim, y_lim

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

    print("Cleaning time series data (removing outliers)...")

    if settings['plot_fig']:
        os.makedirs(f"{settings['plot_dir']}\\outlier_rejection", exist_ok=True)

    for i,key in enumerate(list(cross_distance.keys())):
        chainage = cross_distance[key].copy()
        if sum(np.isnan(chainage)) == len(chainage):
            print(f'→ {key}: has no intersections')
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
        
        print('→ %s: Removed %d outliers'%(key, len(dates1) - len(dates3)))
        # figure for QA
        if settings['plot_fig']:
            fig,ax=plt.subplots(2,1,figsize=[12,6], sharex=True)
            fig.set_tight_layout(True)
            ax[0].grid(linestyle=':', color='0.5')
            ax[0].set(ylabel='distance [m]',
                      title= 'Transect %s original time-series - %d points' % (key, len(chainage1)))
            
            # note: chainages used to be centered at 0 (by subtracting the mean), but this made comparison to other plots difficult
            # plot the data points
            ax[0].plot(dates1, chainage1, 'C0-')
            ax[0].plot(dates1, chainage1, 'C2o', ms=4, mec='k', mew=0.7,label='otsu')
            # plot the indices removed because of the threshold
            ax[0].plot(dates2, chainage2, 'C3o', ms=4, mec='k', mew=0.7,label='spike')
            ax[0].legend(ncol=2,loc='upper right')
            # plot the final time-series
            ax[0].plot(dates3, chainage3, 'C0o', ms=4, mfc='w', mec='C0')
            ax[1].grid(linestyle=':', color='0.5') 
            ax[1].plot(dates3, chainage3, 'C0-o', ms=4, mfc='w', mec='C0')
            ax[1].set(ylabel='distance [m]',
                      title= 'Post-processed time-series - %d points' % (len(chainage3)))
            fig.savefig(f"{settings['plot_dir']}\\outlier_rejection\\{key}_outlier_rejection.png")

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
    return trend, y