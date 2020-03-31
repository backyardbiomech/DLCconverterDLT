"""
Takes dlt-style coordinates, and cropped coordinates from DLC format, and saves
DLC style corrected coordinates
"""

import numpy as np
import pandas as pd
from pathlib import Path
import argparse

def main(fname, cropname, cnum, numcams, opath, flipy, offset):
    # load xypts file to dataframe
    xypts = pd.read_csv(fname)

    if offset < 0:
        # the DLT digitized value on the n-th row was actually digitized at n+offset frame
        # e.g. if offset = -5, a point digitized in the first frame of the video will be placed
        # on the 5th row of the xypts csv file, so negative offsets mean that many blank rows
        # need to be removed from the front of the df
        xypts.drop(range(-1 * offset), inplace=True)
        xypts.reset_index(drop=True)
    if offset > 0:
        # remove than many rows from the end of the df
        xypts.drop(range(len(xypts) - offset, len(xypts)), inplace=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = 'convert argus to cropped DLC coordinates for training')
    parser.add_argument('-xy', help = 'input path to xypts file')
    parser.add_arugment('-crop', help = 'input path to DLC crop file')
    parser.add_argument('-numcams', default=3, help='enter number of cameras')
    parser.add_argument('-cnum', default=2, help='enter 1-indexed camera number for extraction')
    parser.add_argument('-newpath', default=None, help='enter a path for saving, existing target folder will be overwritten, should end with "labeled-data/<videoname>"')
    parser.add_argument('-flipy', default=True,
                        help='flip y coordinates - necessary for DLTdv versions 1-7 and Argus, set to False for DLTdv8')
    parser.add_argument('-offset', default=0, type=int, help='enter offset of chosen camera as integer')

    args = parser.parse_args()

    fname = Path(args.xy)
    cropname = Path(args.crop)
    cnum = int(args.cnum) - 1
    numcams = int(args.numcams)

    # make a new dir for output
    if not args.newpath:
        opath = cropname.parent / 'labeled-data' / cropname.stem
    else:
        opath = Path(args.newpath) / 'labeled-data' / cropname.stem
    if not opath.exists():
        opath.mkdir(parents=True, exist_ok=True)

    main(fname, cropname, cnum, numcams, opath, args.flipy, args.offset)