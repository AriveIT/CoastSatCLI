# load modules
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import TwoSlopeNorm
from scipy.spatial import cKDTree
from shapely.geometry import LineString
from itertools import compress

# CoastSat modules
from coastsat import SDS_tools

# Rejection reasons
NO_VALID_SHORELINE = 1
AMBIGUOUS_SHORELINE = 2
DISPERSION = 3
NO_INTERSECTIONS = 4

# returns the filtered intersections, the dotproduct values, and info
def shoreline_selection(intersections, normals, transect, clustering_threshold):
    transect_direction = transect[1] - transect[0]
    transect_direction /= np.linalg.norm(transect_direction)

    dotprods = np.dot(normals, transect_direction)

    # only look at points with seaward normal pointing the same direction as the transect
    intersections = intersections[dotprods > 0]

    # no shorelines facing the right way
    if len(intersections) == 0:
        return None, None, NO_VALID_SHORELINE

    # check if there's multiple valid shorelines
    clusters = cluster1d(intersections, threshold=clustering_threshold)

    # more than one valid shoreline
    if len(clusters) > 1:
        return None, None, AMBIGUOUS_SHORELINE

    return intersections, dotprods, 0

def cluster1d(intersections, threshold):
    sorted = np.sort(intersections)
    gaps = np.diff(sorted)
    idx = np.where(gaps > threshold)[0]
    clusters = np.split(sorted, idx + 1)
    return clusters

"""
Author: Kilian Vos, Water Research Laboratory, University of New South Wales
Modified to also filter associated normals
Note that normals are not transformed
"""
# returns all intersections between given transect and shoreline
def get_intersections(transect, sl, sl_norm, settings):

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
        return None, None, None

    # change of base to shore-normal coordinate system
    X0 = p0[0] # x and y of transect origin
    Y0 = p0[1]
    xy_close = np.array([sl[idx_close,0],sl[idx_close,1]]) - np.tile(np.array([[X0],
                        [Y0]]), (1,len(sl[idx_close])))
    xy_rot = np.matmul(Mrot, xy_close)

    sl_points = sl[idx_close]
    sl_norm_close = sl_norm[idx_close]

    # remove points that are too far landwards relative to the transect origin (i.e., negative chainage)
    mask = xy_rot[0,:] >= settings['min_chainage']
    intersections = xy_rot[0, mask]
    sl_norm_close = sl_norm_close[mask]
    sl_points = sl_points[mask]

    # if all intersections are too far landwards
    if np.all(np.isnan(xy_rot[0,:])):
        return None, None, None

    return intersections, sl_norm_close, sl_points
###################################################################################################
# Shoreline Extraction
###################################################################################################
def calc_shoreline_normals(contours):
    rot_mat = np.array([[0, -1], [1, 0]])
    norms = []

    for contour in contours:
        d = np.diff(contour, axis=0).T

        line_norms = np.matmul(rot_mat, d).T
        line_norms /= np.linalg.norm(line_norms, axis=1).reshape(-1, 1)

        point_norms = line_norms[:-1] + line_norms[1:]
        point_norms /= np.linalg.norm(point_norms, axis=1).reshape(-1, 1)
        point_norms = np.concatenate([[line_norms[0]], point_norms, [line_norms[-1]]])

        norms.append(point_norms)

    return norms


def plot_normals(contours, normals, date, norm_mult=5):
    fig, ax = plt.subplots(figsize=(20,20))

    for c, n in zip(contours, normals):
        ax.scatter(c[:,1], c[:,0], s=1, c="black")

        # plot normals
        for i in range(len(c)):
            ax.plot([c[i,1], c[i,1] + norm_mult*n[i,1]], [c[i,0], c[i,0] + norm_mult*n[i,0]], c='blue')

    ax.set_aspect('equal', adjustable='box')
    dir = r"C:\Users\avanever\Documents\CoastSatProject\Sites\rose-spit-tip\outputs\misc\\"
    plt.savefig(dir + date)
    plt.close(fig)

"""
Author: Kilian Vos, Water Research Laboratory, University of New South Wales
Modified to also filter the associated normals
"""
def process_shoreline(contours, normals, cloud_mask, im_nodata, georef, image_epsg, settings, date):

    # Step 1: Convert contours to world coordinates and reproject
    contours_world = SDS_tools.convert_pix2world(contours, georef)
    contours_epsg = SDS_tools.convert_epsg(contours_world, image_epsg, settings['output_epsg'])

    # Step 2: Remove short contours
    mask = [LineString([(x, y) for x, y in wl]).length >= settings['min_length_sl'] for wl in contours_epsg]
    contours_long = list(compress(contours_epsg, mask))
    normals_long = list(compress(normals, mask))    

    # Combine long contours into single array
    if not contours_long:
        return np.empty((0, 2)), np.empty((0, 2))
    shoreline = np.vstack(contours_long)
    normals = np.vstack(normals_long)
   

    # Step 3: Remove shoreline points close to cloud pixels
    if cloud_mask.any():
        cloud_idx = np.column_stack(np.where(cloud_mask))
        cloud_coords = SDS_tools.convert_pix2world(cloud_idx, georef)
        cloud_coords = SDS_tools.convert_epsg(cloud_coords, image_epsg, settings['output_epsg'])
        cloud_tree = cKDTree(cloud_coords)
        keep = cloud_tree.query(shoreline, distance_upper_bound=settings['dist_clouds'])[0] == np.inf
        shoreline = shoreline[keep]
        normals = normals[keep]

    # Step 4: Remove shoreline points close to nodata pixels
    if im_nodata.any():
        nodata_idx = np.column_stack(np.where(im_nodata))
        nodata_coords = SDS_tools.convert_pix2world(nodata_idx, georef)
        nodata_coords = SDS_tools.convert_epsg(nodata_coords, image_epsg, settings['output_epsg'])
        nodata_tree = cKDTree(nodata_coords)
        keep = nodata_tree.query(shoreline, distance_upper_bound=30)[0] == np.inf
        shoreline = shoreline[keep]
        normals = normals[keep]

    return shoreline, normals

#############################################################################
# Plotting
#############################################################################

def plot_intersections(key, sl, intersecting_sl, sl_norms, dotprods, transect, date, settings, im_datum, im_rgb, median):
    col = {
        "sl": "black",
        "transect": "black",
        "centroid": "darkorchid",
        "cloud": 'cyan',
        "contrast": 'white' # to make features POP
    }

    transect_p0 = transect[0,:]
    transect_p1 = transect[-1,:]
    collider = get_transect_collider(transect_p0, transect_p1, settings["min_chainage"], settings["past_dist"], settings["along_dist"])

    # init plots
    fig, ax = plt.subplots(figsize=(12, 8))

    sc = plot_basic_intersections(ax, sl, intersecting_sl, sl_norms, dotprods, settings["output_epsg"],
                                  transect_p0, transect_p1, collider, im_datum, im_rgb, col, median)

    # finalize plot
    leg_ax = ax
    handles, _ = leg_ax.get_legend_handles_labels()
    collider_handle = mpatches.Rectangle((0, 0), 1, 1, facecolor='none', edgecolor=col["transect"], linewidth=1.5, label='collider')
    fig.legend(handles=[*handles, collider_handle], bbox_to_anchor=(0.5,0.15), loc='upper center', ncol=3)
    fig.tight_layout(rect=[0, 0.15, 1, 1]) # second value reserves some place for the legend to sit
    fig.colorbar(sc, label='dot product')
    
    # save plot
    filepath = f"{settings['output_dir']}\\{key}_intersection_plots"
    if not os.path.exists(filepath):
                os.mkdir(filepath)
    fig.savefig(f"{filepath}\\{key}_{date}.png")
    plt.close(fig)

def plot_basic_intersections(ax, sl, int_sl, sl_norms, dotprods, output_epsg, transect_p0, transect_p1, collider, im_datum, im_rgb, col, median):
    georef, image_epsg = im_datum

    # convert to image space to be consistent with norms
    def conv(points):
        return SDS_tools.convert_world2pix(SDS_tools.convert_epsg(points, output_epsg, image_epsg), georef)
    transect_p0, transect_p1 = conv(np.stack([transect_p0, transect_p1]))
    collider = conv(np.stack(collider, axis=1)).T
    int_sl = conv(int_sl)
    sl = conv(sl)
    if im_rgb is not None:
        ax.imshow(im_rgb)

    cmap = plt.get_cmap('coolwarm')

    # plot shoreline and transect
    norm = TwoSlopeNorm(vcenter=0)
    ax.scatter(sl[:,1], sl[:,0], c="black", s=5)
    sc = ax.scatter(int_sl[:, 1], int_sl[:, 0], c=dotprods, s=7, cmap=cmap, norm=norm, label="shoreline")
    ax.plot([transect_p0[1], transect_p1[1]], [transect_p0[0], transect_p1[0]], label="transect", c=col["transect"])

    # plot normals
    for i in range(len(int_sl)):
        ax.plot([int_sl[i,1], int_sl[i,1] + 5*sl_norms[i,1]], [int_sl[i,0], int_sl[i,0] + 5*sl_norms[i,0]], c=cmap(norm(dotprods[i])))

    # plot collider
    ax.plot(collider[1], collider[0], c=col["transect"], linewidth=1.5)

    # plot median
    median = get_point_along_transect(transect_p0, transect_p1, median / georef[1])
    ax.scatter(median[1], median[0], s=30, c="white", zorder=100)

    # for better visibility
    x_lim, y_lim = get_plot_range(collider)

    ax.set_xlim(x_lim[0], x_lim[1])
    ax.set_ylim(y_lim[0], y_lim[1])
    ax.set_aspect('equal', adjustable='box')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    if im_datum is not None: ax.invert_yaxis()

    return sc

def get_point_along_transect(p0, p1, point):
    d = p1 - p0
    norm = d / np.linalg.norm(d)
    return p0 + point * norm

def get_transect_collider(p0, p1, min_chainage, past_dist, along_dist):
    d = p1 - p0
    norm = d / np.linalg.norm(d)
    orth = np.array([norm[1], -norm[0]])

    v1 = p1 + past_dist * norm - along_dist * orth
    v2 = p1 + past_dist * norm + along_dist * orth
    v3 = p0 + min_chainage * norm + along_dist * orth # min_chainage is relative to origin (don't need to subtract)
    v4 = p0 + min_chainage * norm - along_dist * orth

    return ([v1[0], v2[0], v3[0], v4[0], v1[0]], [v1[1], v2[1], v3[1], v4[1], v1[1]])
    # return ([v1[1], v2[1], v3[1], v4[1], v1[1]], [v1[0], v2[0], v3[0], v4[0], v1[0]])

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

    # return x_lim, y_lim
    return y_lim, x_lim

def plot_rejection_counts(rejection_counts, dir):
    reasons = [
        "no valid shoreline",
        "ambiguous shoreline",
        "dispersion",
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