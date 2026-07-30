import numpy as np
import re
import os
from datetime import datetime


def get_image_plotting_params(sitename, idx):
    func_name = clean_sitename(sitename) + "_data" + str(idx)
    return globals()[func_name]()


def get_download_dict(sitename):
    func_name = clean_sitename(sitename) + "_download"
    return globals()[func_name]()

def get_paths(sitename, output_dir):
    ref_sl_path = os.path.join(output_dir, "data", "ref_sl", f"{sitename}_ref.geojson")
    aoi_path = os.path.join(output_dir, "data", "aoi", f"{sitename}_aoi.kml")
    return aoi_path, ref_sl_path

def get_idx_for_site(sitename):
    keys = globals().keys()
    cleaned_sitename = clean_sitename(sitename)

    idx = []
    for key in keys:
        if is_data_function(cleaned_sitename, key):
            idx.append(get_num_in_string(key))
    
    return idx


def fn_to_title(fn, sitename):
    is_S2 = "S2" in fn
    sitename_length = len(sitename)
    start = -(sitename_length + 37) + is_S2
    end = -7
    fn = fn[start:end]
    return fn


#######################
# Helpers
######################
def clean_sitename(sitename):
    return re.sub(r'[^A-Za-z0-9]', '', sitename)


def get_num_in_string(input):
    return int(re.sub(r'[^0-9]', '', input))


def is_data_function(sitename, key):
    return sitename in key and "data" in key


# need Canadian urban area too

#############################
# colombia
#############################
def colombia_download():
    return {
        "L8": [datetime(2020, 1, 9)],
        "L9": [datetime(2021, 12, 28)],
        "S2": [datetime(2020, 1, 2)],
    }


#############################
# tofino-mudflat
#############################
def tofinomudflat_download():
    return {
        "L5": [],
        "L7": [],
        "L8": [],
        "L9": [],
        "S2": [],
    }

#############################
# ten-mile-point
#############################
def tenmilepoint_download():
    return {
        "L5": [],
        "L7": [],
        "L8": [],
        "L9": [],
        "S2": [],
    }

#############################
# gas-cliff
#############################
def gascliff_download():
    return {
        "L5": [datetime(1989, 8, 20)],
        "L7": [datetime(2010, 8, 24)],
        "L8": [datetime(2015, 7, 13), datetime(2024, 9, 30)],
        "L9": [datetime(2022, 9, 17), datetime(2024, 7, 13)],
        "S2": [datetime(2016, 8, 10)],
    }

def gascliff_data0():
    title="1989-08-20-18-01-54_L5_044007_gas-cliff"
    t = np.array([
        [[25, 80], [100, 80]], # (x1, y1), (x2, y2)
        [[25, 160], [100, 160]],
    ])
    b_points = [
        np.array([30, 48, 75]),
        np.array([55, 75]),
    ]
    b_labs = [
        ["other", "shadow", "water"],
        ["other", "water"],
    ]
    sl_points = [
        48,
        55
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def gascliff_data1():
    title="2010-08-24-18-15-13_L7_042007_gas-cliff"
    t = np.array([
        [[25, 80], [100, 80]], # (x1, y1), (x2, y2)
        [[25, 160], [100, 160]],
    ])
    b_points = [
        np.array([20, 47, 75]),
        np.array([54, 75]),
    ]
    b_labs = [
        ["other", "shadow", "water"],
        ["other", "water"],
    ]
    sl_points = [
        47,
        54
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def gascliff_data2():
    title="2015-07-13-18-22-30_L8_042007_gas-cliff"
    t = np.array([
        [[25, 100], [100, 100]], # (x1, y1), (x2, y2)
        [[25, 160], [100, 160]],
    ])
    b_points = [
        np.array([38, 51, 75]),
        np.array([54, 75]),
    ]
    b_labs = [
        ["other", "shadow", "water"],
        ["other", "water"],
    ]
    sl_points = [
        51,
        54
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def gascliff_data3():
    title="2024-09-30-18-28-58_L8_043007_gas-cliff"
    t = np.array([
        [[25, 100], [100, 100]], # (x1, y1), (x2, y2)
        [[25, 155], [100, 155]],
    ])
    b_points = [
        np.array([36, 51, 58, 75]),
        np.array([54, 75]),
    ]
    b_labs = [
        ["other", "shadow", "sh_water", "water"],
        ["other", "water"],
    ]
    sl_points = [
        51,
        54
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def gascliff_data4():
    title="2022-09-17-18-29-27_L9_043007_gas-cliff"
    t = np.array([
        [[25, 30], [100, 30]], # (x1, y1), (x2, y2)
        [[25, 50], [100, 50]],
    ])
    b_points = [
        np.array([20, 75]),
        np.array([28, 45, 75]),
    ]
    b_labs = [
        ["other", "shadow", "sh_water", "water"],
        ["shadow", "water_sh", "water"],
    ]
    sl_points = [
        51,
        54
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def gascliff_data5():
    title="2024-07-13-18-22-23_L9_042007_gas-cliff"
    t = np.array([
        [[25, 100], [100, 100]], # (x1, y1), (x2, y2)
        [[25, 155], [100, 155]],
    ])
    b_points = [
        np.array([36, 52, 75]),
        np.array([54, 75]),
    ]
    b_labs = [
        ["other", "shadow", "water"],
        ["other", "water"],
    ]
    sl_points = [
        52,
        54
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def gascliff_data6():
    title="2016-08-10-18-42-50_S2_15XWC_gas-cliff"
    t = np.array([
        [[50, 150], [150, 150]], # (x1, y1), (x2, y2)
        [[50, 250], [150, 250]],
    ])
    b_points = [
        np.array([38, 65, 71, 100]),
        np.array([71, 100]),
    ]
    b_labs = [
        ["other", "shadow", "sh_water", "water"],
        ["other", "water"],
    ]
    sl_points = [
        65,
        71
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs


#############################
# mini-island-view
#############################
def miniislandview_download():
    return {
        "L5": [datetime(1986, 8, 24), datetime(1999, 5, 8)],
        "L7": [datetime(1999, 10, 16), datetime(2003, 4, 9), datetime(2016, 9, 19)],
        "L8": [datetime(2015, 10, 4), datetime(2019, 7, 27)],
        "L9": [datetime(2022, 9, 20), datetime(2023, 5, 18)],
        "S2": [datetime(2015, 10, 4), datetime(2016, 9, 18)],
    }


def miniislandview_data0():
    title="1986-08-24-18-28-54_L5_048026_mini-island-view"
    t = np.array([
        [[20, 20], [60, 20]], # (x1, y1), (x2, y2)
        [[30, 85], [60, 85]],
    ])
    b_points = [
        np.array([10, 14, 40]),
        np.array([13, 17, 30]),
    ]
    b_labs = [
        ["other", "sand", "water"],
        ["other", "sand", "water"],
    ]
    sl_points = [
        14,
        17
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def miniislandview_data1():
    title="1999-05-08-18-46-13_L5_048026_mini-island-view"
    t = np.array([
        [[20, 20], [50, 20]], # (x1, y1), (x2, y2)
        [[20, 85], [60, 85]],
    ])
    b_points = [
        np.array([10, 14, 30]),
        np.array([23, 27, 40]),
    ]
    b_labs = [
        ["other", "sand", "water"],
        ["other", "sand", "water"],
    ]
    sl_points = [
        14,
        27
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def miniislandview_data3():
    title="2003-04-09-18-56-22_L7_048026_mini-island-view"
    t = np.array([
        [[20, 20], [50, 20]], # (x1, y1), (x2, y2)
        [[20, 85], [60, 85]],
    ])
    b_points = [
        np.array([9, 14, 30]),
        np.array([23, 25, 40]),
    ]
    b_labs = [
        ["shadow", "sand", "water"],
        ["other", "sand", "water"],
    ]
    sl_points = [
        14,
        25
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def miniislandview_data5():
    title="2015-10-04-19-01-27_L8_047026_mini-island-view"
    t = np.array([
        [[20, 20], [50, 20]], # (x1, y1), (x2, y2)
        [[20, 85], [60, 85]],
    ])
    b_points = [
        np.array([9, 14, 30]),
        np.array([23, 25, 40]),
    ]
    b_labs = [
        ["other", "sand", "water"],
        ["other", "sand", "water"],
    ]
    sl_points = [
        14,
        25
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def miniislandview_data6():
    title="2019-07-27-19-01-27_L8_047026_mini-island-view"
    t = np.array([
        [[20, 20], [50, 20]], # (x1, y1), (x2, y2)
        [[20, 85], [60, 85]],
    ])
    b_points = [
        np.array([9, 14, 30]),
        np.array([23, 25, 40]),
    ]
    b_labs = [
        ["other", "sand", "water"],
        ["other", "sand", "water"],
    ]
    sl_points = [
        14,
        25
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def miniislandview_data7():
    title="2022-09-20-19-07-56_L9_048026_mini-island-view"
    t = np.array([
        [[20, 20], [50, 20]], # (x1, y1), (x2, y2)
        [[20, 85], [60, 85]],
    ])
    b_points = [
        np.array([9, 14, 30]),
        np.array([23, 25, 40]),
    ]
    b_labs = [
        ["other", "sand", "water"],
        ["other", "sand", "water"],
    ]
    sl_points = [
        14,
        25
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def miniislandview_data11():
    title="2022-09-20-19-07-56_L9_048026_mini-island-view"
    t = np.array([
        [[30, 40], [80, 40]], # (x1, y1), (x2, y2)
        [[40, 85], [100, 85]],
    ])
    b_points = [
        np.array([18, 27, 30, 50]),
        np.array([15, 32, 35, 60]),
    ]
    b_labs = [
        ["other", "shadow", "sand", "water"],
        ["other", "shadow", "sand", "water"],
    ]
    sl_points = [
        30,
        35
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs


#############################
# mini-rose-spit
#############################
def minirosespit_download():
    return  {
    "L5": [datetime(1986, 8, 18), datetime(1992, 4, 12)],
    "L7": [datetime(1999, 9, 15), datetime(2002, 8, 29)],
    "L8": [datetime(2013, 3, 29), datetime(2013, 4, 29)],
    "L9": [datetime(2024, 8, 2), datetime(2024, 12, 8)],
    "S2": [datetime(2016, 5, 13), datetime(2017, 1, 31), datetime(2017, 3, 2)],
}


def minirosespit_data1():
    title="1992-04-12-19-07-05_L5_054022_mini-rose-spit"
    t = np.array([
        [[140, 50], [200, 50]], # (x1, y1), (x2, y2)
        [[120, 80], [200, 80]],
    ])
    b_points = [
        np.array([25, 32, 36, 42, 60]),
        np.array([20, 28, 32, 38, 61, 80]),
    ]
    b_labs = [
        ["water", "white water", "wet sand", "sand", "veg"],
        ["water", "white water", "wet sand", "sand", "veg", "shadow"],
    ]
    sl_points = [
        32,
        28
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs


def minirosespit_data3():
    title="2002-08-29-19-37-16_L7_055022_mini-rose-spit"
    t = np.array([
        [[130, 50], [180, 50]], # (x1, y1), (x2, y2)
        [[55, 164], [95, 164]],
    ])
    b_points = [
        np.array([20, 23, 30, 40, 50]),
        np.array([7, 20, 29, 34, 40]),
    ]
    b_labs = [
        ["water", "white water", "wet sand", "sand", "veg"],
        ["water", "shadow", "wet sand", "sand", "veg"],
    ]
    sl_points = [
        23,
        7
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs


def minirosespit_data5():
    title="2013-04-29-19-51-03_L8_055022_mini-rose-spit"
    t = np.array([
        [[120, 60], [180, 60]], # (x1, y1), (x2, y2)
        [[0, 200], [70, 200]],
    ])
    b_points = [
        np.array([10, 25, 40, 44, 60]),
        np.array([10, 28, 46, 54, 58, 70]),
    ]
    b_labs = [
        ["water", "white water", "wet sand", "sand", "shadow"],
        ["water", "white water", "shadow", "wet sand", "sand", "veg"],
    ]
    sl_points = [
        25,
        28
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def minirosespit_data6():
    title="2024-08-02-19-42-36_L9_054022_mini-rose-spit"
    t = np.array([
        [[120, 60], [180, 60]], # (x1, y1), (x2, y2)
        [[0, 200], [70, 200]],
    ])
    b_points = [
        np.array([11, 38, 42, 46, 51, 60]),
        np.array([24, 31, 40, 43]),
    ]
    b_labs = [
        ["water1", "water2", "white water", "wet sand", "sand", "veg"],
        ["water", "white water", "wet sand", "sand", "veg"],
    ]
    sl_points = [
        42,
        28
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def minirosespit_data8():
    title="2016-05-13-19-59-48_S2_09UUA_mini-rose-spit"
    t = np.array([
        [[220, 60], [300, 60]], # (x1, y1), (x2, y2)
        [[60, 250], [140, 250]],
    ])
    b_points = [
        np.array([28, 32, 49, 64, 80]),
        np.array([12, 15, 62, 80]),
    ]
    b_labs = [
        ["water", "white water", "wet sand", "sand", "veg"],
        ["water", "white water", "wet sand", "veg"],
    ]
    sl_points = [
        32,
        15
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs

def minirosespit_data13():
    title="2017-03-02-20-05-12_S2_09UUV_mini-rose-spit"
    t = np.array([
        [[150, 25], [250, 25]], # (x1, y1), (x2, y2)
        [[30, 180], [100, 180]],
    ])
    b_points = [
        np.array([28, 45, 55, 66, 78, 100]),
        np.array([10, 16, 22, 55, 70]),
    ]
    b_labs = [
        ["water", "white water", "runup", "wet sand", "sand", "veg"],
        ["water", "white water", "wet sand", "shadow", "veg"],
    ]
    sl_points = [
        45,
        16
    ]
    t_labs = [
        "001",
        "002",
    ]
    return t, b_points, b_labs, sl_points, t_labs