"""
Takes dlc tracked coordinates (from <DLC_project_folder>/videos/<name>.hd5) files from multiple DLT calibrated cameras, and exports a DLTdv or Argus based DLT -xypts.csv file. Will also make "dummy" -xyzpts.csv, -offsets.csv, and -xyzres.csv (all blank) for so that everything will load in DLTdv8.

When passing the '-newpath' flag, input a full path ending with a filename prefix. e.g. /path/to/desired/folder/trial01
will make trial01-xypts.csv, trial01-xyzpts.csv, trial01-xyzres.csv, trial01-offsets.csv

That file can then be loaded into DLTdv* or Argus, along with the camera profile and DLT coefficients files. Saving data there then produces an updated -xyzpts.csv file.

Argus and DLTdv* also contain 3d_reconstruct commands that can be called on the command line with the xypts file output here.

With multi-animal projects, this will create SEPARATE dlt files for each individual, which can be combined in post-hoc analysis, or when/if I write a functions specifically to that.

Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 23 Jan 2020
"""

import argparse
import pandas as pd
import numpy as np
import cv2
from pathlib import Path
import re
from deeplabcut.utils.auxiliaryfunctions import read_config

# TODO: read no. of individuals if multi, decide if 1 file per indiv., or multiple tracks in one file

def dlc2dlt(config, opath, camlist, flipy, offsets, like, vid):
    config=Path(config)
    opath = Path(opath)
    offsets = [int(x) for x in offsets]
    numcams = len(camlist)

    # load dlc config
    cfg = read_config(config)
    #scorer = cfg['scorer']
    ma = cfg['multianimalproject']

    if ma:
        individuals = cfg['individuals']
        # indiv = individuals[ind]
        bodyparts = cfg['multianimalbodyparts']
    else:
        bodyparts=cfg['bodyparts']
    coords = ['x', 'y']
    tracks=bodyparts
    # alldata is a nested dict to contain numpy arrays until writing to csv
    # first key is cam, second is indiv
    alldata = {}
    numframes = []
    digi = True
    # load each data file get some basic info and store data in a dict
    for c in range(numcams):
        #load the hd5
        camdata = pd.read_hdf(camlist[c], 'df_with_missing')
        scorer=camdata.columns.get_level_values('scorer')[0]
        #get track names from first camera
        #if c== 0:
            #tracks = camdata.columns.get_level_values('bodyparts')
            #TODO: check if multianimal project based on "individual" in multi-index
        # allow different "scorer"s if different DLC models were used on each camera
        #scorer = camdata.columns.get_level_values('scorer')[0]
        # re-index if h5 is training style - index is paths to images instead of all frame numbers
        # if camdata.index.dtype != np.int64:
        #     # it's DLT created or training data during testing, indexed by a path to a training image, which is numbered
        #     new = [Path(x).stem for x in camdata.index]
        #     camdata.index = [int(re.findall(r'\d+', s)[0]) for s in new]
        #     # add Nans for all missing indexes from 0 to numframes
        #     camdata = camdata.reindex(range(0, camdata.index.max() + 1))
        #     digi = False
        # else:
            # set x,y values with likelihoods below like to nan
            # for each point

        if ma:
            alldata[c]={}
            try:
                for ind in individuals:
                    for track in set(tracks):
                        camdata.loc[camdata[scorer][ind][track]['likelihood'] <= like, (scorer, ind, track, ['x', 'y'])] = np.nan
                    alldata[c][ind]=camdata[scorer][ind]
            except:
                #it's possible in some workflows for config to show multianimal but the tracked data file to not have individuals
                # so act as if single animal
                ma=False
                for track in set(tracks):
                    camdata.loc[camdata[scorer][track]['likelihood'] <= like, (scorer, track, ['x', 'y'])] = np.nan
                alldata[c] = camdata[scorer]
        else:
            for track in set(tracks):
                camdata.loc[camdata[scorer][track]['likelihood'] <= like, (scorer, track, ['x', 'y'])] = np.nan
            alldata[c] = camdata[scorer]

        # make a list to keep track of the number of frames in each camera's dataset
        numframes.append(max(camdata.index.values) + 1)

    # initialize the massive array full of nans (with more than enough rows)
    blankarr = np.empty((max(numframes) - min(offsets), len(tracks) * 2 * numcams)) * np.nan
    xcols = range(0, len(tracks) * 2 * numcams, 2)
    ycols = range(1, len(tracks) * 2 * numcams, 2)
    # outdata is a dict with first key = indiv (0 if not multianimal)
    outdata={}
    if ma:
        for ind in individuals:
            outdata[ind]=blankarr.copy()
    else:
        outdata[0] = blankarr.copy()

    # loop through each camera's data and assign to the proper row
    for c, camdata in alldata.items():

        # load each video, check for "height", and flip the y-coordinates (origin is lower left in Argus and DLTdv 1-7, upper left in openCV, DLC, DLTdv8)
        if vid:
            vidname = vid[c]
        else:
            # DLC video name is datafile stem, plus _labeled.mp4
            vidname = camlist[c].rsplit(scorer)[0] + '.mp4'
        cap = cv2.VideoCapture(str(vidname))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        if height==0 or width==0:
            print("no video file found, so video dimensions cannot be determined")
        # make lists of rows, of matching length, that account for offsets (out = in - offset)
        outrows = list(range(max([0, 0 - offsets[c]]), min([numframes[c], numframes[c] - offsets[c]]), 1))
        inrows = list(range(max([0, 0 + offsets[c]]), min([numframes[c], numframes[c] + offsets[c]]), 1))
        iter = 3
        if ma:
            for ind in individuals:
                for i in range(len(tracks)):
                    incol = i * iter
                    outcol = (i * 2 * numcams) + (2 * c)
                    if flipy:
                        outdata[ind][outrows, outcol] = camdata[ind].iloc[inrows, incol]
                        outdata[ind][outrows, outcol+1] = height - camdata[ind].iloc[inrows,incol+1]
                    else:
                        outdata[ind][outrows, outcol:outcol+2] = camdata[ind].iloc[inrows, incol:incol+2]
                    # set out of range values to nan
                    outdata[ind][outdata[ind] <= 0] = np.nan

                    for xc in xcols:
                        foo = outdata[ind][:, xc]
                        foo[foo >= width] = np.nan
                        outdata[ind][:, xc] = foo

                    for yc in ycols:
                        foo = outdata[ind][:, yc]
                        foo[foo >= height] = np.nan
                        outdata[ind][:, yc] = foo

        else:
            for i in range(len(tracks)):
                incol = i * iter
                outcol = (i * 2 * numcams) + (2 * c)
                if flipy:
                    outdata[0][outrows, outcol] = camdata.iloc[inrows, incol]
                    outdata[0][outrows, outcol+1] = height - camdata.iloc[inrows, incol+1]
                else:
                    outdata[0][outrows, outcol:outcol+2] = camdata.iloc[inrows, incol:incol+2]

    #TODO: set up for multi animal
    #tracknames = tracks[0:-1:3]
    # make col names (same for all files)
    xycols = ['{}_cam_{}_{}'.format(x, c, d) for x in tracks for c in range(1,numcams+1) for d in ['x', 'y']]
    if ma:
        # make separate files for each indiv
        for i, ind in enumerate(individuals):
            basename = str(opath) + '_' + str(ind) + '-'
            xydf = pd.DataFrame(outdata[ind], columns=xycols, index=range(len(outdata[ind])))
            # write to CSV
            xydf.to_csv((basename + 'xypts.csv'), na_rep="NaN", index=False)
            #make "dummy" files
            xyzcols = ['{}_{}'.format(x, d) for x in tracks for d in ['x', 'y', 'z']]
            xyzdf = pd.DataFrame(np.nan, columns=xyzcols, index=range(len(outdata[ind])))
            xyzdf.to_csv((basename + 'xyzpts.csv'), na_rep='NaN', index=False)

            residdf = pd.DataFrame(np.nan, columns=tracks, index=range(len(outdata[ind])))
            residdf.to_csv((basename + 'xyzres.csv'), na_rep='NaN', index=False)

            offcols = ['camera_{}'.format(cnum) for cnum in range(1, numcams + 1)]
            offdf = pd.DataFrame(0, columns=offcols, index=range(len(outdata[ind])))
            offdf.iloc[0] = offsets
            offdf.to_csv((basename + 'offsets.csv'), na_rep='NaN', index=False)

    else:
        ind=0
        basename = str(opath) + '-'
        xydf = pd.DataFrame(outdata[ind], columns=xycols, index=range(len(outdata[ind])))
        # write to CSV
        xydf.to_csv((basename + 'xypts.csv'), na_rep="NaN", index=False)
        # make "dummy" files
        xyzcols = ['{}_{}'.format(x, d) for x in tracks for d in ['x', 'y', 'z']]
        xyzdf = pd.DataFrame(np.nan, columns=xyzcols, index=range(len(outdata[ind])))
        xyzdf.to_csv((basename + 'xyzpts.csv'), na_rep='NaN', index=False)

        residdf = pd.DataFrame(np.nan, columns=tracks, index=range(len(outdata[ind])))
        residdf.to_csv((basename + 'xyzres.csv'), na_rep='NaN', index=False)

        offcols = ['camera_{}'.format(cnum) for cnum in range(1, numcams + 1)]
        offdf = pd.DataFrame(0, columns=offcols, index=range(len(outdata[ind])))
        offdf.iloc[0] = offsets
        offdf.to_csv((basename + 'offsets.csv'), na_rep='NaN', index=False)

    # # convert to dataframe
    # xydf = pd.DataFrame(arr, columns = xycols, index = range(len(arr)))
    # # write to CSV
    # xydf.to_csv((str(opath) + '-xypts.csv'), na_rep = 'NaN', index=False)
    #
    # # make "dummy" xyzpts
    # xyzcols = ['{}_{}'.format(x, d) for x in tracknames for d in ['x', 'y', 'z']]
    # xyzdf = pd.DataFrame(np.nan, columns = xyzcols, index = range(len(arr)))
    # xyzdf.to_csv((str(opath) + '-xyzpts.csv'), na_rep = 'NaN', index=False)
    # # dummy resid
    # residdf = pd.DataFrame(np.nan, columns = tracknames, index=range(len(arr)))
    # residdf.to_csv((str(opath) + '-xyzres.csv'), na_rep = 'NaN', index=False)
    # # dummy offsets
    # offcols = ['camera_{}'.format(cnum) for cnum in range(1, numcams+1)]
    # offdf = pd.DataFrame(0, columns = offcols, index=range(len(arr)))
    # offdf.iloc[0]=offsets
    # offdf.to_csv((str(opath) + '-offsets.csv'), na_rep = 'NaN', index=False)
    #

if __name__== '__main__':
    parser = argparse.ArgumentParser(
    description='convert argus to DLC labeled frames for training')
    parser.add_argument('-config', help='input path to DLC config file')
    parser.add_argument('-dlctracks', nargs='+', help='input paths of DLC tracked coordinates (hd5) in order used in DLT calibration, each path separated by a space')
    parser.add_argument('-newpath', type=str, help = 'enter a path for saving, will overwrite if it already exists, should not be in DLC project folder, should end with filename prefix')
    parser.add_argument('-flipy', default=True, help = 'flip y coordinates - necessar for Argus and DLTdv versions 1-7, set to False for DLTdv8')
    parser.add_argument('-offsets', nargs='+', default = None, help='enter offsets as space separated list including first camera e.g.: -offsets 0 -12 2')
    parser.add_argument('-like', default=0.9, help='enter the likelihood threshold - defaults to 0.9')
    parser.add_argument('-vid', default = None, nargs='+', help='path to video if it is not located with the data file')

    args = parser.parse_args()

    
    dlc2dlt(args.config, args.newpath, args.dlctracks, args.flipy, args.offsets, float(args.like), args.vid)
