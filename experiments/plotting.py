import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns
import numpy as np
import sys, os
import skimage.measure as measure

sys.path.insert(0, os.pardir)
from coastsat import SDS_download, SDS_preprocess, SDS_shoreline, SDS_tools, SDS_classify

import modified_coastsat # modifications for SWIR1 imagery
from indices import mndwi, ndwi, awei_ns, awei_sh, scowi, wi2015
from thresholding import otsu
from image_plotting_parameters import get_idx_for_site, fn_to_title, get_image_plotting_params

# Plot bands intensities, and corresponding index values across given transects
def plot_samples(im, fn, cloud_mask, transects, samples, boundary_points, boundary_labels, transect_labels, ind_fns, output_dir=None):
    n_samples = len(samples)

    fig = plt.figure(figsize=(20,8))
    gs = fig.add_gridspec(n_samples, 4)

    ax_im = fig.add_subplot(gs[:,:2])
    ax_im.set_title(f"{fn}")
    im_RGB = SDS_preprocess.rescale_image_intensity(im[:,:,[2,1,0]], cloud_mask, 99.9)
    plot_im(ax_im, im_RGB, transects, boundary_points, transect_labels, c='black')

    for i in range(len(samples)):
        ax_bands = fig.add_subplot(gs[i,2])
        ax_indices = fig.add_subplot(gs[i,3])
        
        plot_sample_bands(ax_bands, samples[i], boundary_points[i], boundary_labels[i], transect_labels[i])
        plot_sample_indices(ax_indices, ind_fns, samples[i], boundary_points[i], boundary_labels[i], normalize=True)

    legend_pos = (0.5,-.25)
    ax_bands.legend(ncol=3, bbox_to_anchor=legend_pos, loc='upper center')
    ax_indices.legend(ncol=3, bbox_to_anchor=legend_pos, loc='upper center')
    
    fig.tight_layout()
    
    if output_dir:
        output_fn = os.path.join(output_dir, "samples")
        fig.savefig(output_fn)
        plt.close(fig)
    else:
        plt.show()
        plt.close(fig)

# For each given index, plot the index image, histogram, and transect, with each of the given thresholds
def plot_indices(
        im,
        title,
        samples,
        transects,
        boundary_points,
        boundary_labels,
        transect_labels,
        shoreline_points,
        cloud_mask,
        im_buffer,
        ind_fns,
        thresh_fns,
        output_dir=None):
    n_bands = im.shape[-1]
    pal = sns.color_palette()
    buffer_contours = mask_contour(im_buffer)
    im_flat = im.reshape(-1,n_bands)
    threshold_labels = [thresh_fn.__name__ for thresh_fn in thresh_fns]

    for ind_fn in ind_fns:
        im_ind = ind_fn(im_flat).reshape(im.shape[:-1])

        fig, axs = plt.subplots(2, 2, figsize=(12, 8), tight_layout=True)

        # plot index image
        plot_im(axs[0,0], im_ind, transects, boundary_points, transect_labels, cbar=True)
        for contour in buffer_contours:
            axs[0,0].plot(contour[:,1], contour[:,0], c="black")

        # plot histogram
        hist_labels = ["inside buffer", "outside buffer"]
        hist_pal = sns.color_palette(palette='Paired')
        hist_colors = [hist_pal[-3], hist_pal[-4]] # light purple, dark purple
        n, _, _ = axs[1,0].hist([im_ind[im_buffer], im_ind[~im_buffer]], bins=256, stacked=True, label=hist_labels, color=hist_colors, edgecolor=hist_colors)
        axs[1,0].set_ylim(ymax=np.max(n[0])) # focus on values inside buffer
        axs[1,0].legend()

        # calculate thresholds
        thresholds = [thresh_fn(im_ind, cloud_mask, im_buffer) for thresh_fn in thresh_fns]

        # plot samples with thresholds
        optimal_thresholds = []
        for i in range(len(samples)):
            axs[i,1].set_title(transect_labels[i])
            indices = plot_sample_indices(axs[i,1], [ind_fn], samples[i], boundary_points[i], boundary_labels[i], plot_points=True)

            xmin, xmax = axs[i,1].get_xlim()
            optimal_thresholds.append(indices[0][shoreline_points[i]])
            axs[i,1].hlines(thresholds, xmin, xmax, label=threshold_labels, color=pal)
            axs[i,1].hlines(optimal_thresholds[-1], xmin, xmax, label="optimal", color=pal[len(thresholds)])
        
        # add thresholds to histogram
        ymin, ymax = axs[1,0].get_ylim()
        axs[1,0].vlines(thresholds, ymin, ymax, label=threshold_labels, color=pal)
        axs[1,0].vlines(optimal_thresholds, ymin, ymax, label="optimal", color=pal[len(thresholds)])

        # add thresholding methods to legend
        legend_elements = [
            Patch(facecolor=pal[i], label=threshold_labels[i]) for i in range(len(threshold_labels))
        ]
        legend_elements.append(Patch(facecolor=pal[len(thresholds)], label="optimal"))
        
        fig.legend(handles=legend_elements, bbox_to_anchor=(0.5,0.0), loc='lower center', ncol=3)
        fig.suptitle(f"{title}: {ind_fn.__name__}")

        if output_dir:
            output_fn = os.path.join(output_dir, f"index_{ind_fn.__name__}")
            fig.savefig(output_fn)
            plt.close(fig)
        else:
            plt.show()
            plt.close(fig)

def plot_extractions(
            im,
            title,
            index_funcs,
            threshold_funcs,
            cloud_mask,
            ref_buffer,
            im_nodata,
            georef,
            image_epsg,
            settings,
            output_dir=None,
            n_col=int(3)):
    im_RGB = SDS_preprocess.rescale_image_intensity(im[:,:,[2,1,0]], cloud_mask, 99.9)
    n_bands = im.shape[-1]
    im_flat = im.reshape(-1,n_bands)
    pal = sns.color_palette(palette='Dark2')

    n_row = int(np.ceil(len(index_funcs) / n_col))
    fig, axs = plt.subplots(n_row, n_col, figsize=(12, 12), tight_layout=True)
    axs = axs.flatten()


    for i, idx_func in enumerate(index_funcs):
        index = idx_func(im_flat)
        ax = axs[i]

        for j, t_func in enumerate(threshold_funcs):
            
            # prepare shoreline contours
            threshold = t_func(index, cloud_mask, ref_buffer)
            contours = modified_coastsat.find_wl_contours1(index.reshape(im.shape[:-1]), cloud_mask, ref_buffer, threshold)
            contours = SDS_shoreline.process_shoreline(contours, cloud_mask, im_nodata,
                                          georef, image_epsg, settings)
            contours = SDS_tools.convert_epsg(contours, settings['output_epsg'], image_epsg)
            contours = SDS_tools.convert_world2pix(contours, georef)

            # plot
            ax.imshow(im_RGB, interpolation='none')
            ax.scatter(contours[:,0], contours[:,1], label=t_func.__name__, c=pal[j], s=1)
            
            ax.grid(False)
            ax.set_axis_off()
            ax.set_title(f"{idx_func.__name__}")

    # remove empty plots
    while i < n_row * n_col - 1:
        i += 1
        axs[i].set_axis_off()

    legend_elements = [
        Patch(facecolor=pal[i], label=func.__name__) for i, func in enumerate(threshold_funcs)
    ]    
    fig.legend(handles=legend_elements, bbox_to_anchor=(0.5,0.0), loc='lower center', ncol=3)
    fig.suptitle(title)

    if output_dir:
        output_fn = os.path.join(output_dir, "extractions")
        fig.savefig(output_fn)
        plt.close(fig)
    else:
        plt.show()
        plt.close(fig)

def save_all_plots(
            sitename,

            filenames,
            ims,
            cloud_masks,
            im_buffers,
            im_nodatas,
            georefs,
            im_epsgs,

            index_funcs,
            thresh_funcs,

            settings,
            root_output_dir):
    im_idxs = get_idx_for_site(sitename)
    root_output_dir = os.path.join(root_output_dir, "plots")

    for im_idx in im_idxs:
        t, b_points, b_labs, sl_points, t_labs = get_image_plotting_params(sitename, im_idx)
        title=fn_to_title(filenames[im_idx][0], sitename)
        output_dir = os.path.join(root_output_dir, f"{sitename}_plots", title)
        os.makedirs(output_dir, exist_ok=True)
        samples = sample_ms(ims[im_idx], t)

        plot_samples(ims[im_idx], title, cloud_masks[im_idx], t, samples,
                    b_points, b_labs, t_labs, index_funcs, output_dir)
        plot_extractions(ims[im_idx], title, index_funcs, thresh_funcs,
                    cloud_masks[im_idx], im_buffers[im_idx],im_nodatas[im_idx],
                    georefs[im_idx], im_epsgs[im_idx], settings, output_dir)
        plot_indices(ims[im_idx], title, samples, t, b_points, b_labs, t_labs, sl_points,
                    cloud_masks[im_idx], im_buffers[im_idx], index_funcs, thresh_funcs, output_dir)

def sample_ms(im, transects):
    samples = []

    for transect in transects:
        p1 = transect[0]
        p2 = transect[1]

        sample_y = np.arange(p1[0], p2[0]+1, step=1, dtype=int)
        sample_x = np.arange(p1[1], p2[1]+1, step=1, dtype=int)

        samples.append(im[sample_x,sample_y])

    return samples

##################
# Helpers
##################

# boundary points is list of np arrays (so can have inhomogenous)
def plot_im(ax, im, transects=[], boundary_points=[], transect_labels=[], cbar=False, c='black'):
    if cbar:
        cmap = sns.diverging_palette(20, 220, as_cmap=True)
        index_plot = ax.imshow(im, interpolation='none', cmap=cmap)
    else:
        index_plot = ax.imshow(im, interpolation='none')

    for i in range(len(transects)):
        ax.plot(transects[i,:,0],transects[i,:,1], label=f"transect {i}", c=c)

        bp_x = boundary_points[i] + transects[i,0,0]
        bp_y = np.full(boundary_points[i].shape, transects[i,0,1])
        ax.scatter(bp_x, bp_y, marker='|', c=c, s=15)

        ax.text(transects[i,0,0], transects[i,0,1]-3, transect_labels[i], color=c)

    ax.grid(False)
    
    if cbar:
        cb = plt.colorbar(index_plot)
        cb.ax.tick_params(labelsize=10)


def plot_sample_bands(ax, sample, boundary_points, boundary_labels, transect_label):
    labels = ["blue", "green", "red", "NIR", "SWIR1", "SWIR2"]
    colours = ["blue", "green", "red", "orange", "grey", "purple"]
    
    # plot bands
    for i in range(len(labels)):
        ax.plot(sample[:,i], label=labels[i], c=colours[i])
    
    plot_bounds(ax, boundary_points, boundary_labels)

    ax.set_xlabel("Pixels")
    ax.set_ylabel("Intensity")
    ax.set_title(transect_label)


def plot_sample_indices(ax, ind_fns, sample, boundary_points, boundary_labels, normalize=False, plot_points=False):
    indices = []
    for ind_fn in ind_fns:
        index = ind_fn(sample)
        indices.append(index)

        # standardize indices with larger ranges to [-1, 1]
        if ind_fn.__name__ in ["wi2015", "wri"] and normalize:
            index = standardize(index)
            name = f"{ind_fn.__name__}*"
        else:
            name = ind_fn.__name__

        if plot_points:
            x_pos = np.arange(len(index))
            ax.scatter(x_pos, index, s=7)
        
        ax.plot(index, label=name)
    
    plot_bounds(ax, boundary_points, boundary_labels)
    
    ax.set_xlabel("Pixels")
    ax.set_ylabel("Index Value")

    return indices

def standardize(x, new_min=-1, new_max=1):
    x_max = np.max(x)
    x_min = np.min(x)
    min_max_scaled = (x - x_min) / (x_max - x_min) # scaled to [0,1]
    return (new_max - new_min) * min_max_scaled + new_min # scaled to [new_min, new_max]

def plot_bounds(ax, boundary_points, boundary_labels):
    # add vertical lines for each boundary
    ymin, ymax = ax.get_ylim()
    ax.vlines(boundary_points, ymin=ymin, ymax=ymax, colors="black", linestyle="--")

    # add text for each boundary
    for i in range(len(boundary_points)):
        x = boundary_points[i]
        ax.text(x, ymax, boundary_labels[i], rotation=90, va='top', ha='right')

def mask_contour(mask):
    return measure.find_contours(mask, 0.5)