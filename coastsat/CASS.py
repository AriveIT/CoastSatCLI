# load modules
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.spatial import cKDTree

# CoastSat modules
from coastsat import SDS_tools

# Rejection reasons
INVALID_LABELS = 1
CENTROID_IN_CLOUD = 2
CLOUD_PREFERRED = 3
CLUSTERS_CLOUD = 4 # 2 clusters + cloud ambiguous case
GE3_CLUSTERS = 5 # at least 3 clusters
DISPERSION = 6
NO_INTERSECTIONS = 7

###################################################################################################
# Cloud-Aware Shoreline Selection (CASS)
###################################################################################################

# given a set of intersections, apply 1d clustering, and select the cluster that corresponds to the correct
# shoreline given the sign (+/-) of the clusters and the class of the transect (if origin is on land/water)
# factors in if clouds could be covering the correct shoreline
# assumes intersections is not empty

# returns clusters, centroids, index of selected centroid (-1 if no selection), info
# info gives the reason why the intersection was rejected, or the utilised label otherwise
def shoreline_selection(intersections, clustering_threshold, transect_classes, transect_length, cloud_min_max):

    # get clusters
    clusters = cluster1d(intersections, threshold=clustering_threshold)
    centroids = np.array([np.mean(c) for c in clusters])

    # select label
    label_idx, offset = select_label(centroids, transect_classes, transect_length)
    if label_idx == -1:
        return None, None, -1, -INVALID_LABELS
    transect_class = transect_classes[label_idx]

    if cloud_min_max:
        
        # check if any centroids are inside cloud
        centroids_in_cloud = np.any(np.logical_and(centroids > cloud_min_max[0], centroids < cloud_min_max[1]))
        if centroids_in_cloud:
            return clusters, centroids, -1, -CENTROID_IN_CLOUD

        # sort cloud centroid into shoreline centroids
        cloud_centroid = (cloud_min_max[0] + cloud_min_max[1]) / 2
        cloud_idx = np.searchsorted(centroids, cloud_centroid)
        temp_centroids = np.insert(centroids, cloud_idx, cloud_centroid)

        if len(clusters) == 1:
            centroid_idx = select_centroid_2(temp_centroids - offset, transect_class)
            
            if centroid_idx == cloud_idx: return clusters, centroids, -1, -CLOUD_PREFERRED
            else: return clusters, centroids, 0, label_idx + 1 # shoreline is preferred, return 0 as idx (there's only one shoreline)
        
        # 2 clusters + cloud = potentially 3 shorelines --> can be an ambiguous case
        if len(clusters) == 2:
            centroid_idx = select_centroid_3(temp_centroids - offset, transect_class)
            
            # ambiguous case
            if centroid_idx != 1:
                return clusters, centroids, -1, -CLUSTERS_CLOUD
            
            # cloud covers middle shoreline (and cloud is preferred)
            if cloud_idx == 1:
                return clusters, centroids, -1, -CLOUD_PREFERRED
            
            # it is not an ambiguous case and shoreline is preferred, return middle shoreline
            if cloud_idx == 0: return clusters, centroids, 0, label_idx + 1
            else: return clusters, centroids, 1, label_idx + 1

    else:

        if len(clusters) == 1:
            if select_centroid_1(centroids[0] - offset, transect_class):
                return clusters, centroids, 0, label_idx + 1
            else:
                return clusters, centroids, -1, -CLOUD_PREFERRED
        
        if len(clusters) == 2:
            centroid_idx = select_centroid_2(centroids - offset, transect_class)
            return clusters, centroids, centroid_idx, label_idx + 1
    
    # if >2 clusters, assume it's erroneous extraction
    return clusters, centroids, -1, -GE3_CLUSTERS
    

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
            return i, clf_points[i]

    return -1, 0

# returns true if the one shoreline is facing the right direction
def select_centroid_1(centroid, transect_class):
    return (transect_class and centroid < 0) or (not transect_class and centroid > 0)

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
# if returns 0 or 2, selection is ambiguous
def select_centroid_3(centroids, transect_class):
    if centroids[1] > 0:
        selection = select_centroid_2(centroids[:2], transect_class)
        offset = 0
    else:
        selection = select_centroid_2(centroids[1:], transect_class)
        offset = 1
    
    return selection + offset


# returns the minimum and maximum intersections of given cloud and transect
def get_cloud_min_max(transect, cloud_tree, query_radius, half_collider_length, settings):

    collider_center = get_collider_center(transect, settings["min_chainage"], half_collider_length)
    cloud_indices = cloud_tree.query_ball_point(collider_center, query_radius)
    if cloud_indices == []:
        return None, None

    cloud_coords = cloud_tree.data[cloud_indices]
    intersections = get_intersections(transect, cloud_coords, settings)
    if intersections is None:
        return None, cloud_coords

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

"""
Author: Kilian Vos, Water Research Laboratory, University of New South Wales
This function was moved to this file to avoid circular dependencies with SDS_transects
since it's also used to determine cloud intersections
"""
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

###################################################################################################
# Shoreline Extraction
###################################################################################################
def get_transect_classes(transects, im_mndwi, t_mndwi, cloud_mask, settings, georef, filename, image_epsg):
    origins = transects[:,0,:]
    endpoints = transects[:,-1,:]
    midpoints = (origins + endpoints) / 2
    points_world = np.concatenate([origins, midpoints, endpoints])

    points_pxl = np.round(SDS_tools.convert_world2pix(SDS_tools.convert_epsg(points_world,
                                                                    settings['output_epsg'],
                                                                    image_epsg), georef)).astype(int)

    # filter out indices outside of image
    inside_x = (points_pxl[:, 1] < im_mndwi.shape[0]) & (points_pxl[:, 1] >= 0)
    inside_y = (points_pxl[:, 0] < im_mndwi.shape[1]) & (points_pxl[:, 0] >= 0)
    inside = inside_x & inside_y

    # if transect is inside image, check if on cloud pixel. Otherwise set to False
    # cloud_mask is True where a cloud is. Therefore valid should be True if cloud_mask is False
    valid = np.full(inside.shape, False)
    valid[inside] = ~cloud_mask[points_pxl[inside, 1], points_pxl[inside, 0]]
  
    # value < t_mndwi means water
    on_water = np.full(inside.shape, -1)
    on_water[valid] = (im_mndwi[points_pxl[valid,1], points_pxl[valid,0]] < t_mndwi).astype(int)

    # plot_classified_transect_origins(points_pxl, on_water, im_mndwi, filename)
    return on_water.reshape((-1,3), order='F') # want each row to correspond to a single transect
 

def plot_classified_transect_origins(points_pxl, on_water, im, filename): 
    colors = ["blue" if w==1 else "green" if w==0 else "gray" for w in on_water]

    fig, ax = plt.subplots()
    ax.imshow(im)
    
    ax.scatter(points_pxl[:,0], points_pxl[:,1], c=colors, s=0.1)

    dir = "C:\\Users\\avanever\\Documents\\CoastSatProject\\Plots"
    fig.savefig(f"{dir}\\{filename}_mndwi.png", dpi=400)
    plt.close(fig)

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
def plot_clustering_intersections(intersections, key, sl, transect, transect_classes, centroids, centroid_idx, cluster_info, cloud_min_max, cloud_points, date, settings, im_datum):
    origin_colormap = {
        -1 : 'gray',
        0 : 'green',
        1 : 'blue'
    }
    col = {
        "sl": "black",
        "transect": "tab:red",
        "centroid": "darkorchid",
        "cloud": 'cyan',
        "contrast": 'white' # to make features POP
    }

    # if rejected, get reason
    reason = ""
    if cluster_info < 0:
        reason += "rejected: "
        if cluster_info == -INVALID_LABELS: reason += "invalid labels"
        elif cluster_info == -CENTROID_IN_CLOUD: reason += "sl in cloud"
        elif cluster_info == -CLOUD_PREFERRED: reason += "cloud preferred"
        elif cluster_info == -CLUSTERS_CLOUD: reason += "ambiguous 2 sl + cloud"
        elif cluster_info == -GE3_CLUSTERS: reason += ">2 sl"
    else:
        reason += "passed"

    transect_p0 = transect[0,:]
    transect_p1 = transect[-1,:]
    origin_class = transect_classes[0]
    
    collider = get_transect_collider(transect_p0, transect_p1, settings["min_chainage"], settings["past_dist"], settings["along_dist"])

    # init plots
    n_plots = 1 + settings['plot_entire_shoreline'] + settings['plot_1d']
    fig, axs = plt.subplots(1, n_plots, figsize=(12, 8))
    fig.suptitle(f'{key} on {date}: {reason}')

    # organize plotting functions and parameters
    to_plot = [
        True, # basic intersections
        settings['plot_1d'],
        settings['plot_entire_shoreline']
    ]
    plot_fn = [
        plot_basic_intersections, plot_1d_intersections, plot_entire_shoreline,
    ]
    plot_args = [
        (sl, settings["output_epsg"], transect_p0, transect_p1, origin_colormap, origin_class, centroids,
                centroid_idx, cluster_info, transect_classes, cloud_points, collider, im_datum, col),
        (intersections, centroids, centroid_idx, cluster_info, cloud_min_max, col),
        (sl, transect_p0, transect_p1, cloud_points, collider, col),
    ]

    # make plots
    if n_plots == 1:
        plot_fn[0](axs, *plot_args[0])
    else:
        ax_idx = 0
        for i in range(len(to_plot)):
            if to_plot[i]:
                plot_fn[i](axs[ax_idx], *plot_args[i])
                ax_idx += 1

    # finalize plot
    leg_ax = axs if n_plots == 1 else axs[0]
    handles, _ = leg_ax.get_legend_handles_labels()
    collider_handle = mpatches.Rectangle((0, 0), 1, 1, facecolor='none', edgecolor=col["transect"], linewidth=1.5, label='collider')
    fig.legend(handles=[*handles, collider_handle], bbox_to_anchor=(0.5,0.15), loc='upper center', ncol=3)
    fig.tight_layout(rect=[0, 0.15, 1, 1]) # second value reserves some place for the legend to sit
    
    # save plot
    filepath = f"{settings['output_dir']}\\{key}_intersection_plots"
    if not os.path.exists(filepath):
                os.mkdir(filepath)
    fig.savefig(f"{filepath}\\{key}_{date}.png")
    plt.close(fig)

def plot_basic_intersections(ax, sl, output_epsg, transect_p0, transect_p1, colormap, origin_class,
                            centroids, centroid_idx, cluster_info, transect_classes, cloud_points, collider, im_datum, col):
    if im_datum is not None:
        im_rgb, georef, image_epsg = im_datum
        def conv(points):
            return SDS_tools.convert_world2pix(SDS_tools.convert_epsg(points, output_epsg, image_epsg), georef)
        transect_p0, transect_p1 = conv(np.stack([transect_p0, transect_p1]))
        collider = conv(np.stack(collider, axis=1)).T
        sl = conv(sl)
        if centroids is not None: centroids = np.copy(centroids) / georef[1]
        if cloud_points is not None: cloud_points = conv(cloud_points)

        ax.imshow(im_rgb)

    # plot shoreline and transect
    ax.plot(sl[:, 0], sl[:, 1], ".", markersize=2, label="shoreline", c=col["sl"])
    ax.plot([transect_p0[0], transect_p1[0]], [transect_p0[1], transect_p1[1]], label="transect", c=col["transect"])
    ax.plot([transect_p0[0]], [transect_p0[1]], 'o', c=colormap[origin_class], markersize=5) # transect origin

    # plot centroids
    if centroids is not None:
        centroid_trans = get_points_along_transect(transect_p0, transect_p1, centroids)

        # mark selected centroid
        if cluster_info > 0:
            ax.scatter(centroid_trans[centroid_idx, 0], centroid_trans[centroid_idx, 1], facecolors=col["contrast"], edgecolors=col["centroid"], s=150, label="selected", zorder=10)

        # marker size optimal - do not touch
        ax.plot(centroid_trans[:, 0], centroid_trans[:, 1], "s", markerfacecolor=col["centroid"], markeredgecolor=col["contrast"], markersize=6.4582, label="centroids", zorder=20)

    # mark used label
    if cluster_info > 1:
        label_pos = np.linalg.norm(transect_p1 - transect_p0) * (cluster_info - 1) / 2
        label_trans = get_points_along_transect(transect_p0, transect_p1, [label_pos])[0]
        label_colour = colormap[transect_classes[cluster_info - 1]]
        ax.plot(label_trans[0], label_trans[1], 'o', mfc='w', mec=label_colour, markersize=5, label="used label")

    # plot clouds (if showing satellite image, cloud mask shows where cloud is, don't need to overlay points as well)
    if cloud_points is not None and im_datum is None:    
        ax.plot(cloud_points[:, 0], cloud_points[:, 1], ".", c=col["cloud"], markersize=2, label="clouds")

    # plot collider
    ax.plot(*collider, c=col["transect"], linewidth=1.5)

    # for better visibility
    x_lim, y_lim = get_plot_range(collider)

    ax.set_xlim(x_lim[0], x_lim[1])
    ax.set_ylim(y_lim[0], y_lim[1])
    ax.set_aspect('equal', adjustable='box')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    if im_datum is not None: ax.invert_yaxis()

def plot_1d_intersections(ax, intersections, centroids, centroid_idx, cluster_info, cloud_min_max, col):
    # plot intersections in 1d scatterplot
    ax.plot(intersections, np.zeros_like(intersections), 'o', alpha=0.5, c=col["sl"])

    # mark selected centroid
    if cluster_info > 0:
        ax.scatter(centroids[centroid_idx], np.zeros_like(centroids[centroid_idx]), facecolors=col["contrast"], edgecolors=col["centroid"], s=250, label="selected", zorder=10)

    # plot centroids
    if centroids is not None:
        ax.plot(centroids, np.zeros_like(centroids), 's', markerfacecolor=col["centroid"], markeredgecolor=col["contrast"], markersize=8, zorder=20)

    if cloud_min_max is not None:
        ax.plot(cloud_min_max, np.zeros_like(cloud_min_max), 'o', c=col["cloud"], alpha=0.5)

    ax.get_yaxis().set_visible(False)

def plot_entire_shoreline(ax, sl, transect_p0, transect_p1, cloud_points, collider, col):
    ax.plot(sl[:, 0], sl[:, 1], ".", markersize=2, c=col["sl"])
    ax.plot([transect_p0[0], transect_p1[0]], [transect_p0[1], transect_p1[1]], alpha=0.5, c=col["transect"])

    # plot clouds
    if cloud_points is not None:
        ax.plot(cloud_points[:, 0], cloud_points[:, 1], ".", c=col["cloud"], markersize=2)    

    # plot collider
    ax.plot(*collider, c=col["transect"])

    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.axis('equal')

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