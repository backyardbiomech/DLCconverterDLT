"""
This function takes DLT digitized data and creates full DLC tracks, allowing Argus or DLT to be used to manually correct DLC tracks.
It works on a single camera at a time, and is currently only functioning with single animal projects

If the DLC tracks file exists, it will compare the data in the two files. Any points in the DLT data that are different (assumed to be corrected) will be assigned a likelihood of 1.0
This is written to only work with deeplabcut multianimal projects (even if only one individual animal)

Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 8 Jan 2022
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import os
import re
import warnings
import cv2
from deeplabcut.utils.auxiliaryfunctions import read_config

warnings.filterwarnings('ignore', category=pd.io.pytables.PerformanceWarning)


def dlt2dlctracks(config, xyfname, dlcxy, vid, flipy=True, ind=0):
    # make paths into Paths
    config=Path(config)
    xyfname=Path(xyfname)
    dlcxyfname = Path(dlcxy)
    vid=Path(vid)
    camname=vid.stem

    #load dlc config
    cfg = read_config(config)
    ma = cfg['multianimalproject']
    if ma:
        individuals = cfg['individuals']
        indiv = individuals[ind]
        bodyparts = cfg['multianimalbodyparts']
    else:
        bodyparts=cfg['bodyparts']
    coords = ['x', 'y']

 # load xypts file to dataframe
    xypts = pd.read_csv(xyfname)
    xypts = xypts.astype('float64')
    newcols = {}
    # store track name and column index - start of tracks - in dict
    for i in range(0, len(xypts.columns), 2):
        newcol = xypts.columns[i].split('_')[0]
        newcols[newcol]=i
    print(str(vid))
    cap = cv2.VideoCapture(str(vid))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    print(f"height: {height}, width: {width}")
    if not height > 0:
        print("no video file found, so video dimensions cannot be determined")
        return
    if flipy is True:
        # flip the y-coordinates (origin is lower left in Argus and DLTdv 1-7, upper left in openCV, DLC, DLTdv8)
        ycols = [x for x in xypts.columns if '_y' in x]
        xypts.loc[:, ycols] = height - xypts.loc[:, ycols]

    # load dlc tracks
    dlcpts = pd.read_hdf(dlcxyfname, 'df_with_missing')
    dlcpts = dlcpts.astype('float64')
    scorer = dlcpts.columns.get_level_values('scorer')[0]
    # convert the DLT data into a dataframe matching index and header as the DLC data (actually copy the data to keep the likelihood values, coordinates will be overwritten)
    dltpts = dlcpts.copy()
    for bp in bodyparts:
        xy = xypts.loc[:,[f'{bp}_cam_1_x', f'{bp}_cam_1_y']].values
        # reality check
        #dltpts.loc[~np.isfinite(xy[(scorer, bp, 'x')]) | ~np.isfinite(xy[(scorer, bp, 'y')]),
        #if a point as been deleted in DLT
        dltpts.loc[~np.isfinite(xy[:,0]), (scorer, bp, ['x', 'y', 'likelihood'])] = np.nan, np.nan, 0.0
        # if a point's x coordiantes are unreasonable
        dltpts.loc[(0 > dltpts[(scorer, bp, 'x')]) | (dltpts[(scorer, bp, 'x')] > width),
                   (scorer, bp, ['x', 'y', 'likelihood'])] = np.nan, np.nan, 0.0
        # if a point's y coordinates are unreasonable
        dltpts.loc[(0 > dltpts[(scorer, bp, 'y')]) | (dltpts[(scorer, bp, 'y')] > height),
                (scorer, bp, ['x', 'y', 'likelihood'])] = np.nan, np.nan, 0.0
        #dltpts.loc[:, (scorer, bp, ['x', 'y'])] = xypts.loc[:,[f'{bp}_cam_1_x', f'{bp}_cam_1_y']].values
        #  argus seems to round to nearest quarter pixel, so all values are different, so find diff of > 0.5
        # compare dlt and dlc values, and set any different value likelihoods to 1.0
        diff = np.where((abs(dlcpts.loc[:, (scorer, bp, 'x')] - xypts.loc[:, f'{bp}_cam_1_x']) > 0.5))[0]
        if len(diff) > 0:
            print(bp, diff)
            dltpts.loc[diff, (scorer, bp, 'likelihood')] = 1.0
            dltpts.loc[diff, (scorer, bp, ['x', 'y'])] = xypts.loc[diff,[f'{bp}_cam_1_x', f'{bp}_cam_1_y']].values


    # # save out new hdf file, overwriting the DLC file
    dltpts.to_hdf(dlcxyfname, 'df_with_missing', format='table', mode='w')
    # keep an archive version of the original
    dlcorig = dlcxyfname.parent / f'{dlcxyfname.stem}_orig.h5'
    dlcpts.to_hdf(dlcorig, 'df_with_missing', format='table', mode='w')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='convert DLT to DLC tracks frames after manual correction')
    parser.add_argument('-config', help='input path to DLC config file')
    parser.add_argument('-xy',
                        help='input path to DLT xypts file')
    parser.add_argument('-dlcxy', help='path to dlc h5 tracks, acts as output')
    parser.add_argument('-vid', help='input path to video file, needed to flip y coords')
    parser.add_argument('-flipy', default=True,
                        help='flip y coordinates - necessary for DLTdv versions 1-7 and Argus, set to False for DLTdv8')
    parser.add_argument('-ind', default=0, type=int, help='enter 0-indexed individual number from config file. \n xypts.csv must have only one indiv digitized.')


    args = parser.parse_args()

    dlt2dlctracks(args.config, args.xy, args.dlcxy, args.vid, flipy=args.flipy, ind=args.ind)

