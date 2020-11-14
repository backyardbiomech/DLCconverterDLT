"""
Uses cropped videos and DLC analyzed coordinates, plus original bounding box (ul, br) coordinates to produce full
resolution coordinates (can then be converted with dlc2dlt.py to load into Argus or DLTdv)


Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 6 Feb 2020
"""

import argparse
from pathlib import Path
import cv2
import numpy as np
import pandas as pd

def main(xypath, bbpath):
    # load both files
    coords = pd.read_hdf(xypath, 'df_with_missing')
    bbdata = pd.read_hdf(bbpath, 'df_with_missing')
    scorer = bbdata.columns.get_values()[0][0]
    # make a copy of coords to be modified
    fullcoords = coords.copy()
    # for each point, add upper left x and y
    for i in range(0, coords.shape[1], 2):
        fullcoords[scorer].iloc[:, i:i+2] = coords[scorer].iloc[:, i:i+2].values + bbdata[scorer].iloc[:, 0:2].values
    # get name of path
    hdfpath = Path(xypath.parent) / (xypath.stem + '_corrected.h5')
    csvpath = Path(xypath.parent) / (xypath.stem + '_corrected.csv')

    fullcoords.to_hdf(hdfpath, key='df_with_missing', mode='w')
    fullcoords.to_csv(csvpath + scorer + '.csv')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='uncrop videos and coordinates')

    parser.add_argument('coords', help='full path to h5 file containing digitized data from cropped videos')
    parser.add_argument('bbxy', help='full path to h5 file containing original bounding box coordinates')

    args = parser.parse_args()

    xypath = Path(args.coords)
    bbpath = Path(args.bbxy)

    main(xypath, bbpath)
