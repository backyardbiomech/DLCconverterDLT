"""
Takes dlc tracked coordinates (from <DLC_project_folder>/videos/<name>.hd5) files from multiple DLT calibrated cameras, and exports a DLTdv or Argus based DLT -xypts.csv file. Will also make "dummy" -xyzpts.csv, -offsets.csv, and -xyzres.csv (all blank) for so that everything will load in DLTdv8.

When passing the '-newpath' flag, input a full path ending with a filename prefix. e.g. /path/to/desired/folder/trial01
will make trial01-xypts.csv, trial01-xyzpts.csv, trial01-xyzres.csv, trial01-offsets.csv

That file can then be loaded into DLTdv* or Argus, along with the camera profile and DLT coefficents files. Saving data there then produces an updated -xyzpts.csv file.

Argus and DLTdv* also contain 3d_reconstruct commands that can be called on the command line with the xypts file output here.

Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 23 Jan 2020
"""

import argparse
import pandas as pd
import numpy as np
import cv2
from pathlib import Path

def main(opath, camlist, flipy, offsets, like):
    numcams = len(camlist)
    alldata = {}
    numframes = []
    # load each data file get some basic info and store data in a dict
    for c in range(numcams):
        #load the hd5
        camdata = pd.read_hdf(camlist[c], 'df_with_missing')
        numframes.append(max(camdata.index.values) + 1)
        # if the first camera, get the track names
        if c == 0:
            tracks = camdata.columns.get_level_values('bodyparts')
            scorer = camdata.columns.get_level_values('scorer')[0]
        # set x,y values with likelihoods below like to nan
        # for each point
        for track in set(tracks):
            camdata.loc[camdata[scorer][track]['likelihood']<=like, (scorer, track, ['x', 'y'])] = np.nan
        alldata[c] = camdata
    # initialize the massive array full of nans (with more than enough rows)
    arr = np.empty((max(numframes) - min(offsets), len(tracks)//3 * 2 * numcams)) * np.nan
    # loop through each camera's data and assign to the proper row
    for c, camdata in alldata.items():
        if flipy:
            # load each video, check for "height", and flip the y-coordinates (origin is lower left in Argus and DLTdv 1-7, upper left in openCV, DLC, DLTdv8)
            # DLC video name is datafile stem, plus _labeled.mp4
            vidname = camlist[c].rsplit('.h')[0] + '_labeled.mp4'
            cap = cv2.VideoCapture(str(vidname))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # make lists of rows, of matching length, that account for offsets (out = in - offset)
        outrows = list(range(max([0, 0-offsets[c]]), min([numframes[c], numframes[c]-offsets[c]]), 1))
        inrows = list(range(max([0, 0+offsets[c]]), min([numframes[c], numframes[c]+offsets[c]]), 1))

        # fill the array
        for i in range(len(tracks)//3):
            incol = i*3
            outcol = (i * 2 * numcams) + (2 * c)
            if flipy:
                arr[outrows, outcol] = camdata.iloc[inrows, incol]
                arr[outrows, outcol+1] = height - camdata.iloc[inrows, incol+1]
            else:
                arr[outrows, outcol:outcol+2] = camdata.iloc[inrows, incol:incol+2]

            
    tracknames = tracks[0:-1:3]
    # make col names
    xycols = ['{}_cam_{}_{}'.format(x, c, d) for x in tracknames for c in range(1,numcams+1) for d in ['x', 'y']]
    # convert to dataframe
    xydf = pd.DataFrame(arr, columns = xycols, index = range(len(arr)))
    # write to CSV
    xydf.to_csv((str(opath) + '-xypts.csv'), na_rep = 'NaN', index=False)
    
    # make "dummy" xyzpts
    xyzcols = ['{}_{}'.format(x, d) for x in tracknames for d in ['x', 'y', 'z']]
    xyzdf = pd.DataFrame(np.nan, columns = xyzcols, index = range(len(arr)))
    xyzdf.to_csv((str(opath) + '-xyzpts.csv'), na_rep = 'NaN', index=False)
    # dummy resid
    residdf = pd.DataFrame(np.nan, columns = tracknames, index=range(len(arr)))
    residdf.to_csv((str(opath) + '-xyzres.csv'), na_rep = 'NaN', index=False)
    # dummy offsets
    offcols = ['camera_{}'.format(cnum) for cnum in range(1, numcams+1)]
    offdf = pd.DataFrame(0, columns = offcols, index=range(len(arr)))
    offdf.iloc[0]=offsets
    offdf.to_csv((str(opath) + '-offsets.csv'), na_rep = 'NaN', index=False)


if __name__== '__main__':
    parser = argparse.ArgumentParser(
    description='convert argus to DLC labeled frames for training')

    parser.add_argument('-dlctracks', nargs='+', help='input paths of DLC tracked coordinates (hd5) in order used in DLT calibration, each path separated by a space')
    parser.add_argument('-newpath', type=str, help = 'enter a path for saving, will overwrite if it already exists, should not be in DLC project folder, should end with filename prefix')
    parser.add_argument('-flipy', default=True, help = 'flip y coordinates - necessar for Argus and DLTdv versions 1-7, set to False for DLTdv8')
    parser.add_argument('-offsets', nargs='+', default = None, help='enter offsets as space separated list including first camera e.g.: -offsets 0 -12 2')
    parser.add_argument('-like', default=0.9, help='enter the likelihood threshold - defaults to 0.9')

    args = parser.parse_args()
    if not args.offsets:
        offsets = [0] * len(args.dlctracks)
    else:
        offsets = [int(x) for x in args.offsets]
        
    opath = Path(args.newpath)
    # opath.mkdir(parents=True, exist_ok=True)
    
    main(opath, args.dlctracks, args.flipy, offsets, args.like)
