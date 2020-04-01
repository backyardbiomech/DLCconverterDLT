"""
Takes dlt-style coordinates, cropped coordinates from DLC format, and saves
DLT style crop-corrected coordinates
"""

import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import re

def main(fname, croplist, numcams, opath, flipy, offsets):
    croppaths = [Path(x) for x in croplist]
    # load xypts file to dataframe
    xypts = pd.read_csv(fname)
    xynew = xypts.copy() * np.nan
    for c in range(numcams):
        # load the cropped data file
        cropped = pd.read_hdf(croppaths[c], 'df_with_missing')
        # get the scorer
        scorer = cropped.columns.get_level_values('scorer')[0]
        # get the 'ul' x and y columns from this camera
        # PROBLEM: coordinates for training bounding boxes are indexed by path to training image. Coordinates from DLC analysis is indexed by frame number, and has 'x', 'y', and 'likelihood' columns
        # test if the cropped coordinates are from a training set (rare, all done in DLT, or in testing), or from analyzed data'
        ul = cropped[scorer]['ul'][['x', 'y']]
        # if it's analyzed data, index is already set as 0-indexed frame integer, do nothing
        if cropped.index.dtype != 'int':
            # it's DLT created or training data during testing, indexed by a path to a training image, which is numbered
            new = [Path(x).stem for x in ul.index]
            ul.index = [int(re.findall(r'\d+', s)[0]) for s in new]
        # correct for offsets by reindexing, effectively inserting blank rows at the start or end of cropped
        ul.index = ul.index - offsets[c]
        #TODO need to flip the Y - may be different for each camera! so requires loading the videos, or add to dlt2dlc.py
        for i in range(int(len(xypts.columns)/(2*numcams))):
            icol = i * (2 * numcams) + (c * 2)
            # do the subtraction, indexes should take care of everything
            #xypts.iloc[:, icol : icol+2] = xypts.iloc[:, icol : icol+2] - ul
            xynew.iloc[ul.index, icol: icol+2] = xypts.iloc[ul.index, icol:icol+2].values - ul.values
    # resave the xypts - no need to xyz etc since this is just an intermediate for dlt2dlc.py
    xynew.to_csv(opath, na_rep='NaN', index=False)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = 'convert argus to cropped DLC coordinates for training')
    parser.add_argument('-xy', help = 'input path to xypts file')
    parser.add_argument('-crop', nargs='+', help='input paths to DLC crop files for each video separated by spaces')
    parser.add_argument('-numcams', default=3, help='enter number of cameras')
    parser.add_argument('-flipy', default=True,
                        help='flip y coordinates - necessary for DLTdv versions 1-7 and Argus, set to False for DLTdv8')
    parser.add_argument('-offsets', nargs='+', default=None, help='enter offsets as space separated list including first camera e.g.: -offsets 0 -12 2')
    args = parser.parse_args()

    fname = Path(args.xy)
    croplist = args.crop
    numcams = int(args.numcams)

    if not args.offsets:
        offsets = [0] * len(croplist)
    else:
        offsets = [int(x) for x in args.offsets]

    opath = fname.parent / (str(fname.stem) + 'cropped.csv')

    main(fname, croplist, numcams, opath, args.flipy, offsets)
