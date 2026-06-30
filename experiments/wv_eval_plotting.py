import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import metrics as m

def plot_transect_metric(metric, outlier_thresholds, transects_pix, ref_sl_points_pxl, im_rgb, contours_pxl=None, s=None):
    s = s or 1
    
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
    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c="white", s=s)

    # sds sl
    if contours_pxl is not None:
        ax.scatter(contours_pxl[:,0], contours_pxl[:,1], c="black", s=s)

    # handle transects with no intersections and outliers
    idx_none = np.where(np.isnan(metric))[0]
    for idx in np.concat([idx_none, outlier_idx]):
        ax.plot(transects_pix[idx,:,0], transects_pix[idx,:,1], c="red")

    ax.imshow(im_rgb)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='metric')
    
    return fig
    

def plot_shoreline_metric(metric, outlier_thresholds, ref_sl_points_pxl, im_rgb, title=None, contours_pxl=None, s=None):
    s = s or 1
    outlier_idx = m.get_outlier_idx(metric, outlier_thresholds)
    dists_no_outliers = np.delete(metric, outlier_idx)
    ref_sl_no_outliers = np.delete(ref_sl_points_pxl, outlier_idx, axis=0)

    min_dist, max_dist = np.min(dists_no_outliers), np.max(dists_no_outliers)
    cmap = mpl.cm.cool
    col = cmap((dists_no_outliers - min_dist) / (max_dist - min_dist))

    fig, ax = plt.subplots(figsize=(20, 10))
    ax.axis(False)
    ax.set_title(title)

    # reference sl
    ax.scatter(ref_sl_no_outliers[:,0], ref_sl_no_outliers[:,1], c=col, s=s)
    ax.scatter(ref_sl_points_pxl[outlier_idx,0], ref_sl_points_pxl[outlier_idx,1], c="red", s=s) # outliers

    # sds sl
    if contours_pxl is not None:
        ax.scatter(contours_pxl[:,0], contours_pxl[:,1], c="white", s=s)

    ax.imshow(im_rgb, interpolation=None)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='metric')
    
    return fig

def plot_comparison(entries1, entries2, opt1, opt2, metric_names, sl_lim=50):
    n_rows = np.ceil(len(metric_names) / 3).astype(int)
    fig, axs = plt.subplots(n_rows, 3, figsize=(16, 4 * n_rows), tight_layout=True)
    axs = axs.ravel()
    fig.suptitle(f"{opt1} vs {opt2}")

    for i, metric_name in enumerate(metric_names):
        metric1 = np.array([e[metric_name] for e in entries1])
        metric2 = np.array([e[metric_name] for e in entries2])

        if "sl" in metric_name and "outlier" not in metric_name:
            good = (metric1 < sl_lim) & (metric2 < sl_lim)
            metric1 = metric1[good]
            metric2 = metric2[good]

        axs[i].set_title(f"{metric_name}")
        axs[i].set_xlabel(opt1)
        axs[i].set_ylabel(opt2)
        axs[i].scatter(metric1, metric2, alpha=0.5)

        minimum = np.min([axs[i].get_xlim()[0], axs[i].get_ylim()[0]])
        maximum = np.max([axs[i].get_xlim()[1], axs[i].get_ylim()[1]])
        l = [minimum, maximum]
        axs[i].plot(l, l)
        axs[i].set_aspect("equal")
    
    for j in range(i+1, len(axs)):
        axs[j].axis(False)

    return fig

def plot_comparison_barplot(entries_arr, titles):
    methods = [e["method"] for e in entries_arr[0]]
    metrics = list(entries_arr[0][0].keys())[1:]
    # metrics = list(entries_arr[0][0].keys())[:]
    print(metrics)

    fig, ax = plt.subplots(len(metrics), 1, figsize=(20, 16), tight_layout=True)

    for i, metric in enumerate(metrics):
    
        x = np.arange(len(methods))  # the label locations
        width = 0.15  # the width of the bars
        multiplier = 0

        metric_matrix = np.array([[e[metric] for e in entries_arr[i]] for i in range(len(titles))])

        if i == 0:
            # sort in increasing order (of actual metric value)
            min_metric = np.min(metric_matrix, axis=0)
            min_idx = np.argsort(min_metric)
            methods = [methods[i] for i in min_idx]
        metric_matrix = metric_matrix[:,min_idx]

        # assume first in entries_arr is the reference
        relative_change = np.array([(metric_matrix[i,:] - metric_matrix[0,:]) / metric_matrix[0,:] for i in range(1, len(metric_matrix))])
        metric_dict = {titles[i+1] : relative_change[i,:] for i in range(len(relative_change))}

        for attribute, measurement in metric_dict.items():
            offset = width * multiplier
            rects = ax[i].bar(x + offset, measurement, width, label=attribute)
            # ax[i].bar_label(rects, padding=3)
            multiplier += 1


        ax[i].set_title(metric)
        ax[i].legend(loc='upper right', ncols=3)
        ax[i].set_ylim(-1, 1)
        ax[i].tick_params(
            axis='x',          # changes apply to the x-axis
            labelbottom=False)
        ax[-1].set_xticks(x + .5 * (len(titles) - 1) * width)
    
    ax[-1].tick_params(
            axis='x',          # changes apply to the x-axis
            labelbottom=True)
    ax[-1].set_xticks(x + .5 * (len(titles) - 1) * width, methods, rotation='vertical')
    return fig

###############################
# Best Method Functions
###############################
def plot_best_score_per_point(metric, ref_sl_points_pxl, im_rgb, sitename, sim_sat):

    min_dist, max_dist = np.min(metric), np.max(metric)
    cmap = mpl.cm.cool
    col = cmap((metric - min_dist) / (max_dist - min_dist))

    fig, ax = plt.subplots(figsize=(20, 10))
    ax.axis(False)
    ax.set_title(f"{sitename}_{sim_sat}: Best Score Per Point")

    # reference sl
    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c=col, s=1)

    ax.imshow(im_rgb, interpolation=None)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='Distance to nearest extracted point',
                fraction=0.04, pad=0.04)
    
    return fig

def plot_best_method_per_point(idx, methods, ref_sl_points_pxl, im_rgb, sitename, sim_sat):
    cmap = get_all_of_em_cmap()

    fig, ax = plt.subplots(figsize=(20, 10))
    ax.axis(False)
    ax.set_title(f"{sitename}_{sim_sat}: Best Method Per Point")

    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c=cmap(idx/(len(methods) - 1)), cmap=cmap, s=1)
    ax.imshow(im_rgb, interpolation=None)
    
    legend_elements = [Patch(facecolor=cmap(i/(len(methods) - 1)), label=methods[i]) for i in range(len(methods))]
    ax.legend(handles=legend_elements, loc="upper right")
    
    return fig

def plot_best_score_per_transect(metric, transects_pix, ref_sl_points_pxl, im_rgb, sitename, sim_sat):

    min_dist, max_dist = np.min(metric), np.max(metric)
    cmap = mpl.cm.cool
    col = cmap((metric - min_dist) / (max_dist - min_dist))

    fig, ax = plt.subplots(figsize=(20, 10))
    ax.axis(False)
    ax.set_title(f"{sitename}_{sim_sat}: Best Score Per Transect")

    # reference sl
    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c="white", s=1)

    # transects
    for i in range(len(transects_pix)):
        ax.plot(transects_pix[i,:,0], transects_pix[i,:,1], c=col[i])

    ax.imshow(im_rgb, interpolation=None)

    norm = mpl.colors.Normalize(min_dist, max_dist)
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                ax=ax, orientation='vertical', label='Transect Cross Distance MAE')
    
    return fig

def plot_best_method_per_transect(idx, methods, transects_pix, ref_sl_points_pxl, im_rgb, sitename, sim_sat):
    cmap = get_all_of_em_cmap()

    fig, ax = plt.subplots(figsize=(20, 10))
    ax.axis(False)
    ax.set_title(f"{sitename}_{sim_sat}: Best Score Per Transect")

    ax.scatter(ref_sl_points_pxl[:,0], ref_sl_points_pxl[:,1], c="white", s=1)
    ax.imshow(im_rgb, interpolation=None)

    for i in range(len(transects_pix)):
        ax.plot(transects_pix[i,:,0], transects_pix[i,:,1], c=cmap(idx[i]/(len(methods) - 1)))
    
    legend_elements = [Patch(facecolor=cmap(i/(len(methods) - 1)), label=methods[i]) for i in range(len(methods))]
    ax.legend(handles=legend_elements, loc="upper right")
    
    return fig

def violin_plots(metric, methods, title, ylim=None, outlier_idx=None, box_instead=False, sort_methods=False):
    no_outlier_performances = []
    valid_methods = []
    means = []
    for i in range(len(methods)):
        no_outlier = metric[i]
        if outlier_idx is not None:  no_outlier = no_outlier[~outlier_idx]
        no_outlier = no_outlier[~np.isnan(no_outlier)]
        
        no_outlier_performances.append(no_outlier)
        valid_methods.append(methods[i])
        means.append(np.median(no_outlier))

    if sort_methods:
        sorted_idx = np.argsort(means)
        no_outlier_performances = [no_outlier_performances[idx] for idx in sorted_idx]
        valid_methods = [valid_methods[idx] for idx in sorted_idx]

    fig, ax = plt.subplots(figsize=(16, 8), tight_layout=True)
    ax.set_title(title)
    if ylim is not None: ax.set_ylim(ylim)
    if box_instead:
        ax.boxplot(no_outlier_performances)
    else:
        ax.violinplot(no_outlier_performances, showmedians=True)
    ax.set_xticks([y + 1 for y in range(len(valid_methods))], labels=valid_methods, rotation=90)
    return fig, ax

def plot_best_method_counts(best_per_unit_idx, methods, title, pie_instead=False):
    idx, counts = np.unique(best_per_unit_idx, return_counts=True)
    fig, ax = plt.subplots()
    if not pie_instead:
        ax.bar(methods[idx], counts)
        ax.tick_params(axis='x', labelrotation=90)
        ax.set_ylabel("Count")
        ax.set_title(title)
    else:
        cmap = get_all_of_em_cmap()
        wedges, _ = ax.pie(counts, colors=cmap(np.arange(len(methods)) / len(methods)))
        ax.set_title(title)
    return fig

#######################
# Helpers
#######################
def get_all_of_em_cmap():
    return mpl.colors.LinearSegmentedColormap.from_list(
        name="all of em",
        colors=["#A13737", "#BE508D", "#B23AB6", "#9036c4", "#543aca", "#3a78ca", "#3aa1ca", "#3acab2", "#3aca41", "#c8ca3a", "#ca903a", "#ca3a3a"]
    )