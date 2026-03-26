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
import pickle
from pathlib import Path

# other modules
import skimage.transform as transform
from pylab import ginput
from scipy import stats
from scipy.spatial import cKDTree

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
    shorelines = output['shorelines']
    trees_per_file = 50
    
    # pre-calculate values for cloud intersections
    ts = np.array(list(transects.values()))
    transect_lengths = np.linalg.norm(ts[:,-1,:] - ts[:,0,:], axis=1)
    half_collider_lengths = (transect_lengths + settings["past_dist"] - settings["min_chainage"]) / 2
    query_radii = np.sqrt(half_collider_lengths ** 2 + settings["along_dist"] ** 2) # distance from collider center to collider corner

    # initialise variables
    def init_var():
        return np.full((len(shorelines), len(transects.keys())), np.nan)
    std_intersect = init_var()
    med_intersect = init_var()
    max_intersect = init_var()
    min_intersect = init_var()
    n_intersect = init_var()

    n_cluster = init_var()
    rejection_counts = init_var()

    # loop through each shoreline
    n = len(shorelines)
    last_kd_tree_idx = 0
    cloud_kd_trees = load_cloud_kd_trees(settings, last_kd_tree_idx, trees_per_file, n)
    for sl_idx in range(len(shorelines)):
        print(f'\rProcessing shoreline {sl_idx + 1} out of {str(n)}...', end='')
        sl = shorelines[sl_idx]

        cur = sl_idx // trees_per_file
        if cur != last_kd_tree_idx:
            cloud_kd_trees = load_cloud_kd_trees(settings, cur, trees_per_file, n)
            last_kd_tree_idx = cur

        # loop through each transect
        for transect_idx, key in enumerate(transects.keys()):
            
            intersections = get_intersections(transects[key], sl, settings)

            if intersections is None:
                rejection_counts[sl_idx, transect_idx] = 7 # 7 means no intersections
                continue

            if settings.get('cluster_intersection_selection', False):
                if settings.get('cloud_filtering', True):
                    cloud_idx = sl_idx - trees_per_file * last_kd_tree_idx
                    cloud_min_max, cloud_points = get_cloud_min_max(transects[key], cloud_kd_trees[cloud_idx], query_radii[transect_idx], half_collider_lengths[transect_idx],
                                                                    settings['min_points'], settings)
                else:
                    cloud_min_max, cloud_points = None, None
                transect_classes = output['transect_origin_classes'][sl_idx][transect_idx]
                clusters, centroids, c_idx, c_info = cluster_intersection_selection(
                    intersections = intersections[~np.isnan(intersections)],
                    clustering_threshold = settings['clustering_threshold'],
                    transect_classes = transect_classes,
                    transect_length = transect_lengths[transect_idx],
                    cloud_min_max = cloud_min_max
                )

                # plot intersections and other clustering alg related info
                if key in settings.get('transects_to_plot', []) and c_info > 0:
                    plot_clustering_intersections(intersections, key, sl, transects[key], transect_classes,
                            centroids, c_idx, c_info, cloud_min_max, cloud_points, str(output['dates'][sl_idx])[:10], settings)

                # if no cluster selected
                if c_info < 0:
                    rejection_counts[sl_idx, transect_idx] = abs(c_info)
                    continue
                
                intersections = clusters[c_idx] # update intersections to just selected cluster
                n_cluster[sl_idx, transect_idx] = len(clusters)

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
    n_cluster[~idx_good] = np.nan
    nan_after = np.isnan(med_intersect)

    # save intersections for each transect in dictionary
    cross_dist = {key: med_intersect[:,transect_idx] for transect_idx, key in enumerate(transects.keys())}
    
    # plot time series with cluster information
    if settings.get("plot_n_clusters", False) and settings.get('cluster_intersection_selection', False):
        for transect_idx, key in enumerate(transects.keys()):
            transect_classes = np.array(output['transect_origin_classes'])[:,transect_idx,0]
            plot_n_clusters(cross_dist[key], output['dates'], n_cluster[:,transect_idx], transect_classes, key, settings['output_dir'])

    # plot why intersections were rejected for each transect and shoreline
    if settings.get("plot_rejection_counts", False) and settings.get('cluster_intersection_selection', False):
        dispersion_rejections = np.logical_and(nan_after, ~nan_before)
        rejection_counts[dispersion_rejections] = 6
        plot_rejection_counts(rejection_counts, settings['output_dir'])

    print()
    return cross_dist


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
    xy_rot[0, xy_rot[0,:] < settings['min_chainage']] = np.nan

    # if all intersections are too far landwards
    if np.all(np.isnan(xy_rot[0,:])):
        return None

    return xy_rot[0,:]


def load_cloud_kd_trees(settings, idx, trees_per_file, n_shorelines):
    start = idx * trees_per_file
    end = min((idx + 1) * trees_per_file, n_shorelines)
    fn = f"{settings['sitename']}_cloud_kdtrees_{start}_{end}.pkl"

    cache_path = Path(settings["output_dir"]) / "kdtrees" / fn

    try:
        with cache_path.open("rb") as f:
            cloud_kd_trees = pickle.load(f)
    except FileNotFoundError:
        raise Exception(f"Cloud kd tree pickle file {fn} in {cache_path} unable to load")
    return cloud_kd_trees

def update_ema(ema, alpha, new_value):
    if np.isnan(new_value): return ema
    if np.isnan(ema): return new_value
    return new_value * alpha + ema * (1-alpha)


###################################################################################################
# Cluster Intersection Selection Algorithm
###################################################################################################

# given a set of intersections, apply 1d clustering, and select the cluster that corresponds to the correct
# shoreline given the sign (+/-) of the clusters and the class of the transect (if origin is on land/water)
# factors in if clouds could be covering the correct shoreline
# assumes intersections is not empty

# returns clusters, centroids, index of selected centroid, info
# info:
# 1: returned correct centroid
# -1: invalid labels
# -2: centroid in cloud
# -3: cloud preferred over shoreline
# -4: 2 clusters + cloud
# -5: >2 clusters
def cluster_intersection_selection(intersections, clustering_threshold, transect_classes, transect_length, cloud_min_max):

    # get clusters
    clusters = cluster1d(intersections, threshold=clustering_threshold)
    centroids = np.array([np.mean(c) for c in clusters])

    # select label if we will have to select a centroid
    if (cloud_min_max is not None) + len(clusters) >= 2:
        label_idx, offset = select_label(centroids, transect_classes, transect_length)
        if label_idx == -1:
            return None, None, -1, -1
        transect_class = transect_classes[label_idx]

    if cloud_min_max:
        
        # check if any centroids are inside cloud
        centroids_in_cloud = np.any(np.logical_and(centroids > cloud_min_max[0], centroids < cloud_min_max[1]))
        if centroids_in_cloud:
            return clusters, centroids, -1, -2    

        cloud_centroid = (cloud_min_max[0] + cloud_min_max[1]) / 2 

        if len(clusters) == 1:

            # centroids have to be in increasing order
            if cloud_centroid < centroids[0]:
                temp_centroids = np.array([cloud_centroid, centroids[0]])
                cloud_idx = 0
            else:
                temp_centroids = np.array([centroids[0], cloud_centroid]) 
                cloud_idx = 1
            
            # see if imaginary cloud covered shoreline would be preferred
            centroid_idx = select_centroid_2(temp_centroids - offset, transect_class)
            
            if centroid_idx == cloud_idx: return clusters, centroids, -1, -3 # skip intersection if cloud preferred 
            else: return clusters, centroids, 0, label_idx + 1 # if shoreline is preferred, return 0 as idx (there's only one shoreline)
        
        # 2 clusters + cloud = potentially 3 shorelines --> can be an ambiguous case
        if len(clusters) == 2:

            cloud_idx = np.searchsorted(centroids, cloud_centroid)
            temp_centroids = np.insert(centroids, cloud_idx, cloud_centroid)
            centroid_idx = select_centroid_3(temp_centroids - offset, transect_class) # returns None or 1
            
            # if ambiguous case
            if centroid_idx == None:
                return clusters, centroids, -1, -4
            
            # if cloud covers middle shoreline (cloud is preferred)
            if cloud_idx == 1:
                return clusters, centroids, -1, -3
            
            # it is not an ambiguous case, and shoreline is preferred, return middle shoreline
            if cloud_idx == 0: return clusters, centroids, 0, label_idx + 1
            else: return clusters, centroids, 1, label_idx + 1


    else:

        if len(clusters) == 1:
            return clusters, centroids, 0, 1
        
        if len(clusters) == 2:
            centroid_idx = select_centroid_2(centroids - offset, transect_class)
            return clusters, centroids, centroid_idx, label_idx + 1
    
    # if more >2  clusters, picking shoreline becomes ambiguous in some cases
    # if 3 clusters is a common case (and consistently not noise), should consider adding handling
    return clusters, centroids, -1, -5
    

# simple gap based 1d clustering based on given threshold
def cluster1d(intersections, threshold):
    sorted = np.sort(intersections)
    gaps = np.diff(sorted)
    idx = np.where(gaps > threshold)[0]
    clusters = np.split(sorted, idx + 1)
    return clusters

# three points on the transect are classified (origin, midpoint and endpoint)
# select the first label that is valid and far enough from the shorelines (> resolution = 15m)
# returns index of label, and its offset from the origin
# returns -1, 0 if no valid points far enough from all shorelines
def select_label(centroids, transect_classes, transect_length):

    clf_points = np.array([0, transect_length / 2, transect_length])
    for i in range(3):
        if transect_classes[i] != -1 and np.all(np.abs(clf_points[i] - centroids) > 15):
            return i, transect_length * i / 2

    return -1, 0




# transect_class = 1 --> transect origin is on water
# assumes exactly 2 centroids, and transect classes are valid (0 or 1)
# determines which shoreline to pick (first or second centroid)
# i.e. the shoreline facing the same direction as the transect
# assumes centroids are in increasing order
# basically just a behaviour tree
def select_centroid_2(centroids, transect_class):
    return int(np.logical_xor(transect_class, np.logical_xor(centroids[0] > 0, centroids[1] > 0)))

# select centroid from list of 3 centroids/shorelines
# only applied to 2 SL + cloud case, since we're pretending the cloud is covering a real shoreline
# otherwise, 3 SL case is too often noise
def select_centroid_3(centroids, transect_class):
    if centroids[1] > 0:
        selection = select_centroid_2(centroids[:2], transect_class)
        offset = 0
    else:
        selection = select_centroid_2(centroids[1:], transect_class)
        offset = 1
    
    # if middle shoreline is preferred, return that
    # otherwise, 2 shorelines are facing the correct direction so selection is ambiguous
    if selection + offset == 1:
        return 1
    else:
        return None

# could move no label transect check before cloud intersection calculation (nice to have plots tho)

# returns the minimum and maximum intersections of given cloud and transect
def get_cloud_min_max(transect, cloud_tree, query_radius, half_collider_length, min_points, settings):

    collider_center = get_collider_center(transect, settings["min_chainage"], half_collider_length)
    cloud_indices = cloud_tree.query_ball_point(collider_center, query_radius)
    if cloud_indices == []:
        return None, None

    cloud_coords = cloud_tree.data[cloud_indices]
    intersections = get_intersections(transect, cloud_coords, settings)
    if intersections is None or len(intersections) < min_points:
        return None, None

    resolution = 15 # resolution in worst case (Landsat)
    buffer = resolution * 1.414 # ~root(2) --> distance to other corner

    return (np.nanmin(intersections) - buffer, np.nanmax(intersections) + buffer), cloud_coords

def get_collider_center(transect, min_chainage, half_collider_length):
    dir = normalize(transect[-1,:] - transect[0,:])
    center = transect[0,:] + (min_chainage + half_collider_length) * dir
    return center

def normalize(vector):
    magnitude = np.linalg.norm(vector)
    return vector / magnitude


###################################################################################################
# Intersection Plotting
###################################################################################################

"""
Plots:
    - Transect and collider
    - Intersections, centroids, with selected centroid marked
    - Shoreline points
    - Transect origin, coloured based on class
    - Nearby cloud points and min/max cloud intersections
    - Plots 2D version (zoomed in and zoomed out), and also projected onto transect
"""
def plot_clustering_intersections(intersections, key, sl, transect, transect_classes, centroids, centroid_idx, cluster_info, cloud_min_max, cloud_points, date, settings):
    origin_colormap = {
        -1 : 'gray',
        0 : 'green',
        1 : 'blue'
    }

    # if rejected, get reason
    reason = ""
    if cluster_info < 0:
        reason += "rejected: "
        if cluster_info == -1: reason += "invalid labesl"
        elif cluster_info == -2: reason += "sl in cloud"
        elif cluster_info == -3: reason += "cloud preferred"
        elif cluster_info == -4: reason += "ambiguous 2 sl + cloud"
        elif cluster_info == -5: reason += ">2 sl"
    else:
        reason += "passed"

    transect_p0 = transect[0,:]
    transect_p1 = transect[-1,:]
    origin_class = transect_classes[0]

    if settings['plot_entire_shoreline']:
        fig, axs = plt.subplots(1, 3, figsize=(12, 8))
    else:
        fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle(f'{key} on {date}: {reason}')

    # plot intersections in 1d scatterplot
    axs[0].plot(intersections, np.zeros_like(intersections), 'o', alpha=0.5, label="shoreline")

    # plot shoreline and transect
    axs[1].plot(sl[:, 0], sl[:, 1], ".", markersize=2)
    axs[1].plot([transect_p0[0], transect_p1[0]], [transect_p0[1], transect_p1[1]], alpha=0.5, label="transect")
    axs[1].plot([transect_p0[0]], [transect_p0[1]], 'o', c=origin_colormap[origin_class], markersize=5) # transect origin

    if settings['plot_entire_shoreline']:
        axs[2].plot(sl[:, 0], sl[:, 1], ".", markersize=2)
        axs[2].plot([transect_p0[0], transect_p1[0]], [transect_p0[1], transect_p1[1]], alpha=0.5)

    # plot centroids
    if centroids is not None:
        axs[0].plot(centroids, np.zeros_like(centroids), 'o', c='black', label="centroids")
        centroid_trans = get_points_along_transect(transect_p0, transect_p1, centroids)
        axs[1].plot(centroid_trans[:, 0], centroid_trans[:, 1], ".", c='black', markersize=6)

    # mark selected centroid
    if cluster_info > 0:
        axs[0].scatter(centroids[centroid_idx], np.zeros_like(centroids[centroid_idx]), facecolors='none', edgecolors='black', s=200, label="selected")
        axs[1].scatter(centroid_trans[centroid_idx, 0], centroid_trans[centroid_idx, 1], facecolors='none', edgecolors='black', s=200)

    # mark used label
    if cluster_info > 1:
        label_pos = np.linalg.norm(transect_p1 - transect_p0) * (cluster_info - 1) / 2
        label_trans = get_points_along_transect(transect_p0, transect_p1, [label_pos])[0]
        label_colour = origin_colormap[transect_classes[cluster_info - 1]]
        axs[1].plot(label_trans[0], label_trans[1], 'o', mfc='w', mec=label_colour, markersize=5, label="used label")
    # plot clouds
    if cloud_min_max is not None:
        axs[0].plot(cloud_min_max, np.zeros_like(cloud_min_max), 'o', c='cyan', alpha=0.5, label="clouds")
    if cloud_points is not None:    
        axs[1].plot(cloud_points[:, 0], cloud_points[:, 1], ".", c='cyan', markersize=2)
        if settings['plot_entire_shoreline']: axs[2].plot(cloud_points[:, 0], cloud_points[:, 1], ".", c='cyan', markersize=2)

    # plot collider
    collider = get_transect_collider(transect_p0, transect_p1, settings["min_chainage"], settings["past_dist"], settings["along_dist"])
    axs[1].plot(*collider, c='red', label="collider")
    if settings['plot_entire_shoreline']: axs[2].plot(*collider, c='red')

    # plot ema
    # axs[0].scatter(ema, np.zeros_like(ema), facecolors='none', edgecolors='purple', s=200, label="ema")
    # ema_trans = get_points_along_transect(transect_p0, transect_p1, [ema])
    # axs[1].scatter(ema_trans[:, 0], ema_trans[:, 1], facecolors='none', edgecolors='purple', s=200)

    # for better visibility
    x_lim, y_lim = get_plot_range(collider)

    axs[0].get_yaxis().set_visible(False)
    axs[1].set_xlim(x_lim[0], x_lim[1])
    axs[1].set_ylim(y_lim[0], y_lim[1])
    axs[1].set_aspect('equal', adjustable='box')
    axs[1].get_xaxis().set_visible(False)
    axs[1].get_yaxis().set_visible(False)
    
    if settings['plot_entire_shoreline']:
        axs[2].get_xaxis().set_visible(False)
        axs[2].get_yaxis().set_visible(False)
        axs[2].axis('equal')

    fig.legend(bbox_to_anchor=(0.5,0.0), loc='lower center', ncol=3)
    fig.tight_layout(rect=[0, 0.15, 1, 1]) # second value reserves some place for the legend to sit
    
    # save plot
    filepath = f"{settings['output_dir']}\\{key}_intersection_plots"
    if not os.path.exists(filepath):
                os.mkdir(filepath)
    fig.savefig(f"{filepath}\\{key}_{date}.png")
    plt.close(fig)


def get_points_along_transect(p0, p1, points):
    d = p1 - p0
    norm = d / np.linalg.norm(d)
    centroid_trans = np.array([p0 + q * norm for q in points])
    return centroid_trans


def get_transect_collider(p0, p1, min_chainage, past_dist, along_dist):
    d = p1 - p0
    norm = d / np.linalg.norm(d)
    orth = np.array([norm[1], -norm[0]])

    v1 = p1 + past_dist * norm - along_dist * orth
    v2 = p1 + past_dist * norm + along_dist * orth
    v3 = p0 + min_chainage * norm + along_dist * orth # min_chainage is relative to origin (don't need to subtract)
    v4 = p0 + min_chainage * norm - along_dist * orth

    return ([v1[0], v2[0], v3[0], v4[0], v1[0]], [v1[1], v2[1], v3[1], v4[1], v1[1]])

def get_plot_range(collider, buffer=10):
    x = collider[0][:4] # leave out repeated point
    y = collider[1][:4]
    x_max = np.max(x)
    x_min = np.min(x)
    y_max = np.max(y)
    y_min = np.min(y)
    
    r = max(x_max-x_min, y_max-y_min) / 2
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    r += buffer
    x_lim = (x_mean - r, x_mean + r)
    y_lim = (y_mean - r, y_mean + r)

    return x_lim, y_lim


def plot_n_clusters(chainage, dates, n_clusters, transect_classes, transect_key, dir):
    # note: intersections with unlabelled transects are thrown out - therefore not plotted

    # preprocessing
    idx_not_nan = np.where(~np.isnan(chainage))[0]
    idx1 = np.where(n_clusters == 1)[0]
    idx2 = np.where(n_clusters == 2)[0]
    idx_land = np.where(transect_classes == 0)[0]
    idx_water = np.where(transect_classes == 1)[0]
    
    idx_1_land = np.intersect1d(idx1, idx_land)
    idx_1_water = np.intersect1d(idx1, idx_water)
    idx_2_land = np.intersect1d(idx2, idx_land)
    idx_2_water = np.intersect1d(idx2, idx_water)

    pct_2_cluster = (len(idx2) / len(idx_not_nan)) * 100 if len(idx_not_nan) != 0 else 0

    # prep fig
    fig,ax=plt.subplots(1,1,figsize=[12,6], sharex=True)
    fig.set_tight_layout(True)
    fig.suptitle(f'{transect_key} time-series: {pct_2_cluster:.3f}% 2 cluster')
    ax.grid(linestyle=':', color='0.5')
    ax.set_ylabel('distance [m]')

    # plot the data points
    ax.plot([dates[i] for i in idx_not_nan], chainage[idx_not_nan], c=str(0.8), linestyle='-') # line
    ax.plot([dates[i] for i in idx_1_land], chainage[idx_1_land], 'C2o', ms=4, mfc='w', mec='C2', label="1 cluster + land")
    ax.plot([dates[i] for i in idx_1_water], chainage[idx_1_water], 'C0o', ms=4, mfc='w', mec='C0', label="1 cluster + water")
    ax.plot([dates[i] for i in idx_2_land], chainage[idx_2_land], 'C2o', ms=4, mec='C2', label="2 cluster + land")
    ax.plot([dates[i] for i in idx_2_water], chainage[idx_2_water], 'C0o', ms=4, mec='C0', label="2 cluster + water")

    fig.legend(bbox_to_anchor=(0.5,0.0), loc='lower center', ncol=2)
    fig.tight_layout(rect=[0, 0.15, 1, 1]) # second value reserves some place for the legend to sit
    
    # save
    os.makedirs(f"{dir}\\n_clusters", exist_ok=True)
    fig.savefig(f"{dir}\\n_clusters\\{transect_key}_n_clusters.png")
    plt.close(fig)
    

def plot_rejection_counts(rejection_counts, dir):
    reasons = [
        "invalid labels",
        "centroid in cloud",
        "cloud preferred",
        "ambiguous 2 sl + cloud",
        ">2 sl",
        "dispersion metrics",
        "no intersections",
    ]
    n_sl = rejection_counts.shape[0]
    n_t = rejection_counts.shape[1]

    sl_unique = count_unique_per_row(rejection_counts, len(reasons))
    t_unique = count_unique_per_row(np.transpose(rejection_counts), len(reasons))

    sl_dict = {reasons[i]: sl_unique[:,i] for i in range(len(reasons))}
    t_dict = {reasons[i]: t_unique[:,i] for i in range(len(reasons))}

    plot_rejection_counts_helper("transect", "shoreline", n_t, n_sl, t_dict, dir)
    plot_rejection_counts_helper("shoreline", "transect", n_sl, n_t, sl_dict, dir)

def plot_rejection_counts_helper(type, other, n_type, n_other, reasons_dict, dir):

    fig, ax = plt.subplots(figsize=(12,8))
    fig.suptitle(f"Rejection counts for each {type}")
    ax.set_xlabel(f"{type} index")
    ax.set_ylabel("counts")
    bottom = np.zeros(n_type)
    x_pos = np.arange(1, n_type + 1) # generated transect labels start at 1
    width=1

    for reason, count in reasons_dict.items():
        _ = ax.bar(x_pos, height=count, width=width, label=reason, bottom=bottom)
        bottom += count
    
    ax.axhline(n_other, linestyle="--", color="k", label=f"total # {other}")
    fig.legend(bbox_to_anchor=(0.5,0.0), loc='lower center', ncol=2)
    fig.tight_layout(rect=[0, 0.15, 1, 1]) # second value reserves some place for the legend to sit

    fig.savefig(f"{dir}\\{type}_rejection_counts.png")
    plt.close(fig)

def count_unique_per_row(mat, n_lab):
    output = np.zeros((mat.shape[0], n_lab))

    for row in range(mat.shape[0]):
        unique, counts = np.unique(mat[row,:], return_counts=True)

        # remove count for nans
        not_nan = ~np.isnan(unique)
        unique = unique[not_nan]
        counts = counts[not_nan]

        unique = np.array(unique, dtype=np.int64) - 1
        output[row,unique] = counts
    
    return output


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
        
        print('--> %s: Removed %d outliers'%(key, len(dates1) - len(dates3)))
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
            plt.close(fig)

        outlier_stats[0, i] = len(chainage3) # points in post-processed time-series
        outlier_stats[1, i] = len(chainage2) - len(chainage3) # spike
        outlier_stats[2, i] = len(chainage1) - len(chainage2) # otsu

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

def plot_outlier_counts(outlier_stats, n_sl, dir):
    labels = ["good", "spike", "otsu"]
    colours = ["C0", "C3", "C2"] # consistency with other outlier plots
    n_transects = outlier_stats.shape[1]

    mean_outliers = np.sum(outlier_stats[[1, 2],:]) / n_transects
    mean_points = np.sum(outlier_stats) / n_transects
    outlier_percentage = np.sum(outlier_stats[[1, 2],:]) / np.sum(outlier_stats)



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
    return trend, y