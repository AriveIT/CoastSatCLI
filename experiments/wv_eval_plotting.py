import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import metrics as m

def plot_transect_metric(metric, outlier_thresholds, transects_pix, ref_sl_points_pxl, contours_pxl, im_rgb):
    outlier_idx = m.get_outlier_idx(metric, outlier_thresholds)
    metric_no_outliers = np.delete(metric, outlier_idx)
    transects_pix_no_outliers = np.delete(transects_pix, outlier_idx, axis=0)

    min_dist, max_dist = min(metric_no_outliers), max(metric_no_outliers)
    cmap = mpl.cm.cool
    col = cmap((metric_no_outliers - min_dist) / (max_dist - min_dist))

    fig, ax = plt.subplots(figsize=(40,20))

    # transects
    for i in range(len(transects_pix_no_outliers)):
        ax.plot(transects_pix_no_outliers[i,:,0], transects_pix_no_outliers[i,:,1], c=col[i])

    # reference sl
    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c="white", s=1)

    # sds sl
    ax.scatter(contours_pxl[:,0], contours_pxl[:,1], c="black", s=1)

    # handle transects with no intersections and outliers
    idx_none = np.where(np.isnan(metric))[0]
    for idx in np.concat([idx_none, outlier_idx]):
        ax.plot(transects_pix[idx,:,0], transects_pix[idx,:,1], c="red")

    ax.imshow(im_rgb)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='metric')
    
    return fig
    

def plot_shoreline_metric(metric, outlier_thresholds, ref_sl_points_pxl, contours_pxl, im_rgb):
    outlier_idx = m.get_outlier_idx(metric, outlier_thresholds)
    dists_no_outliers = np.delete(metric, outlier_idx)
    ref_sl_no_outliers = np.delete(ref_sl_points_pxl, outlier_idx, axis=0)

    min_dist, max_dist = np.min(dists_no_outliers), np.max(dists_no_outliers)
    cmap = mpl.cm.cool
    col = cmap((dists_no_outliers - min_dist) / (max_dist - min_dist))

    fig, ax = plt.subplots(figsize=(40, 20))
    ax.axis(False)

    # reference sl
    ax.scatter(ref_sl_no_outliers[:,0], ref_sl_no_outliers[:,1], c=col, s=1)
    ax.scatter(ref_sl_points_pxl[outlier_idx,0], ref_sl_points_pxl[outlier_idx,1], c="red", s=1) # outliers

    # sds sl
    ax.scatter(contours_pxl[:,0], contours_pxl[:,1], c="white", s=1)

    ax.imshow(im_rgb, interpolation=None)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='metric')
    
    return fig


###############################
# Best Method Functions
###############################
def plot_best_score_per_point(metric, ref_sl_points_pxl, im_rgb):

    min_dist, max_dist = np.min(metric), np.max(metric)
    cmap = mpl.cm.cool
    col = cmap((metric - min_dist) / (max_dist - min_dist))

    fig, ax = plt.subplots(figsize=(40, 20))
    ax.axis(False)

    # reference sl
    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c=col, s=1)

    ax.imshow(im_rgb, interpolation=None)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='metric')
    
    return fig

def plot_best_method_per_point(idx, methods, ref_sl_points_pxl, im_rgb):
    cmap = get_all_of_em_cmap()

    fig, ax = plt.subplots(figsize=(40, 20))
    ax.axis(False)

    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c=cmap(idx/(len(methods) - 1)), cmap=cmap, s=1)
    ax.imshow(im_rgb, interpolation=None)
    
    legend_elements = [Patch(facecolor=cmap(i/(len(methods) - 1)), label=methods[i]) for i in range(len(methods))]
    ax.legend(handles=legend_elements, loc="upper right")
    
    return fig

def plot_best_score_per_transect(metric, transects_pix, ref_sl_points_pxl, im_rgb):

    min_dist, max_dist = np.min(metric), np.max(metric)
    cmap = mpl.cm.cool
    col = cmap((metric - min_dist) / (max_dist - min_dist))

    fig, ax = plt.subplots(figsize=(40, 20))
    ax.axis(False)

    # reference sl
    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c="white", s=1)

    # transects
    for i in range(len(transects_pix)):
        ax.plot(transects_pix[i,:,0], transects_pix[i,:,1], c=col[i])

    ax.imshow(im_rgb, interpolation=None)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='metric')
    
    return fig

def plot_best_method_per_transect(idx, methods, transects_pix, ref_sl_points_pxl, im_rgb):
    cmap = get_all_of_em_cmap()

    fig, ax = plt.subplots(figsize=(40, 20))
    ax.axis(False)

    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c="white", s=1)
    ax.imshow(im_rgb, interpolation=None)

    for i in range(len(transects_pix)):
        ax.plot(transects_pix[i,:,0], transects_pix[i,:,1], c=cmap(idx[i]/(len(methods) - 1)))
    
    legend_elements = [Patch(facecolor=cmap(i/(len(methods) - 1)), label=methods[i]) for i in range(len(methods))]
    ax.legend(handles=legend_elements, loc="upper right")
    
    return fig

def violin_plots(metric, methods, outlier_t=None, box_instead=False):
    no_outlier_performances = []
    valid_methods = []
    for i in range(len(methods)):
        no_outlier = metric[i, ~np.isnan(metric[i])]
        
        if outlier_t:
            no_outlier = metric[i, (metric[i] >= outlier_t[0]) & (metric[i] <= outlier_t[1])]
        if len(no_outlier) == 0:
            continue
        no_outlier_performances.append(no_outlier)
        valid_methods.append(methods[i])

    fig, ax = plt.subplots(figsize=(16, 8))
    if box_instead:
        ax.boxplot(no_outlier_performances)
    else:
        ax.violinplot(no_outlier_performances, showmedians=True)
    ax.set_xticks([y + 1 for y in range(len(valid_methods))], labels=valid_methods, rotation=90)
    return fig

#######################
# Helpers
#######################
def get_all_of_em_cmap():
    return mpl.colors.LinearSegmentedColormap.from_list(
        name="all of em",
        colors=["#A13737", "#BE508D", "#B23AB6", "#9036c4", "#543aca", "#3a78ca", "#3aa1ca", "#3acab2", "#3aca41", "#c8ca3a", "#ca903a", "#ca3a3a"]
    )