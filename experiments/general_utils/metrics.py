import numpy as np
from scipy.spatial import KDTree
import matplotlib as mpl
import matplotlib.pyplot as plt
from general_utils import modified_coastsat


#################################
# Shoreline wide nearest distance
#################################
# for each gt shoreline point, compute the distance to the nearest sds shoreline point
def get_nearest_distance(gt, sds):
    pointwise_dist = []
    sds_tree = KDTree(sds)

    for gt_point in gt:
        pointwise_dist.append(sds_tree.query(gt_point)[0])
    
    return np.array(pointwise_dist)


####################
# Median Distance
####################
# computes distance between medians
def median_distance(gt_inter, sds_inter):
    return np.median(sds_inter) - np.median(gt_inter)

def get_median_distances(transects, ref_sl_points, contours, collider_settings):
    skipped_ind = []
    med_dist = []
    for i in range(len(transects)):
        t = transects[i]
        gt_inter = modified_coastsat.get_intersections(t, ref_sl_points, collider_settings)
        sds_inter = modified_coastsat.get_intersections(t, contours, collider_settings)

        if gt_inter is None or sds_inter is None:
            skipped_ind.append(i)
            med_dist.append(np.nan)
            continue

        med_dist.append(median_distance(gt_inter, sds_inter))

    med_dist = np.array(med_dist)
    return med_dist, skipped_ind

####################
# My (flawed) Average Distance
# Assumes shorelines could be expressed as functions (vertical line test)
####################
# assumes p1, p2 are one line, q1, q2 are another line that do not cross
# assumes p1 and q1 have same x, and p2 and q2 have same x
# assumes p1[0] < p2[0] and q1[0] < q2[0] (points are sorted by x values)
# does not assume which line is on top
def trapezoid_area(p1, p2, q1, q2):

    # determine which line is on top
    if p1[1] >= q1[1] and p2[1] >= q2[1]:
        top1, top2, bot1, bot2 = p1, p2, q1, q2
    elif p1[1] <= q1[1] and p2[1] <= q2[1]:
        top1, top2, bot1, bot2 = q1, q2, p1, p2
    else:
        print("lines cross")
        print(p1[0], p2[0], q1[0], q2[0])
        print(p1[1], p2[1], q1[1], q2[1])
        assert 1 == 0

    # dimensions of rectangle and the 2 triangles
    width = top2[0] - top1[0]
    rect_height = min(top1[1], top2[1]) - max(bot1[1], bot2[1])
    tri1_height = abs(top1[1] - top2[1])
    tri2_height = abs(bot1[1] - bot2[1])

    # return area of rectangle + area of the 2 triangles
    return (width * rect_height) + (width * tri1_height) / 2 + (width * tri2_height) / 2


def get_average_distance(gt_inter, sds_inter):
    gt_inter = format_inter(gt_inter)
    sds_inter = format_inter(sds_inter)

    matching_sds = add_matching_points(gt_inter, sds_inter)
    matching_gt = add_matching_points(sds_inter, gt_inter)

    combined1_sds = sort_by_x(np.concat([sds_inter, matching_sds]))
    combined1_gt = sort_by_x(np.concat([gt_inter, matching_gt]))

    filtered_sds, filtered_gt = filter_inters(combined1_sds, combined1_gt)

    inter = add_points_at_intersections(filtered_sds, filtered_gt)

    combined2_sds = sort_by_x(np.concat([filtered_sds, inter]))
    combined2_gt = sort_by_x(np.concat([filtered_gt, inter]))
    assert filtered_sds.shape == filtered_gt.shape

    cum_area = 0
    for i in range(filtered_sds.shape[0]-1):
        cum_area += trapezoid_area(combined2_sds[i,:], combined2_sds[i+1,:], combined2_gt[i,:], combined2_gt[i+1,:])
    
    return cum_area / (combined2_sds[-1,0] - combined2_sds[0,0])
    # return cum_area


######################
# Helpers
######################
def filter_inters(sds, gt):
    eps = 1e-7
    lower_bound = max(gt[0,0], sds[0,0]) - eps
    upper_bound = min(gt[-1,0], sds[-1,0]) + eps
    filtered_sds = sds[(sds[:,0] < upper_bound) & (sds[:,0] > lower_bound)]
    filtered_gt = gt[(gt[:,0] < upper_bound) & (gt[:,0] > lower_bound)]
    return filtered_sds, filtered_gt


def lerp(p1, p2, x):
    assert p1[0] <= x and x <= p2[0]

    weight = (x - p1[0]) / (p2[0] - p1[0])
    return p1[1] * (1-weight) + p2[1] * weight

# for each x in a1, generates a new point by interpolating a2 at that x
def add_matching_points(a1, a2):
    new_points = []

    for p in a1:
        idx = np.searchsorted(a2[:,0], p[0])
        if idx == 0 or idx >= a2.shape[0]: continue

        new_y = lerp(a2[idx-1,:], a2[idx,:], p[0])
        new_points.append([p[0], new_y])

    return np.array(new_points)

def slope(p1, p2):
    return (p2[1] - p1[1]) / (p2[0] - p1[0])

def intercept(p1, slope):
    return p1[1] - p1[0] * slope

def sort_by_x(a):
    order = np.argsort(a[:,0])
    return a[order]

def format_inter(inter):
    inter = inter[[1, 0],:] # put x at 0th index
    inter = inter.T
    return sort_by_x(inter)

# returns intersection of two lines, each defined by two points
# assumes there is an intersection
def find_intersection(p1, p2, q1, q2):
    p_slope = slope(p1, p2)
    q_slope = slope(q1, q2)
    p_intercept = intercept(p1, p_slope)
    q_intercept = intercept(q1, q_slope)

    numer = q_intercept - p_intercept
    denom = p_slope - q_slope
    x = numer / denom
    y = p_slope * x + p_intercept

    return [x, y]

# add a point whenever a1 and a2 intersect
def add_points_at_intersections(a1, a2):
    inter_pts = []
    idx1, idx2 = 0, 0
    assert a1.shape == a2.shape
    last_top = a1[idx1,1] > a2[idx2,1]

    while True:
        top = a1[idx1,1] > a2[idx2,1]
        # print(f"{top != last_top}, {idx1} {idx2}, {a1[idx1, 1]}, {a2[idx2, 1]}, {a1[idx1, 0]}, {a2[idx2, 0]}")

        # if which line is on top changes there's an intersection
        if top != last_top:
            inter = find_intersection(a1[idx1-1], a1[idx1], a2[idx2-1], a2[idx2])
            inter_pts.append(inter)

        last_top = top

        # look at point with next largest x
        idx1 += 1
        idx2 += 1

        # if at end of one of the lines
        if idx1 >= a1.shape[0] - 2 or idx2 >= a2.shape[0] - 2:
            break
    
    inter_pts = np.array(inter_pts).reshape(-1, 2)

    return inter_pts

def get_outlier_idx(metric, outlier_thresholds):
    return np.where((metric < outlier_thresholds[0]) | (metric > outlier_thresholds[1]))[0]