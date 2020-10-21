"""
This is a simpler function that uses data digitized in Argus or DLTdv and applies it as labels to extracted frames in DLC.
IMPORTANT: use deeplabcut to create a project, add videos, and extract the frames. Use this simply to bypass the label_frames function of deeplabcut.
Extracting frames  in deeplabcut creates images in the labeled-data folder in a dlc project
This function pulls labels for those frames from DLTdv or Argus based DLT 3D projects, one camera at a time.

This is written to only work with deeplabcut multianimal projects (even if only one individual animal)
and for now it considers all labels to apply to individual 1, so only pass it videos with one animal in view
After running, you can open the labeling GUI in deeplabcut to check, edit, and add labels, or run dlc.check_labels to make sure everything imported properly.

VERY IMPORTANT: Argus/DLTdv track names must exactly match DLC bodyparts (in config) for this to work. You can edit config or the xypts.csv file header to make them match if you need.

If you go back to Argus/DLTdv and digitize new frames/points, you have two options
1. delete the Collected_Data_...h5 file in labeled-data/camerafolder to fully reimport. This is your only option if you "correct" points in Argus/DLT
2. If you are adding points from DLT, but already made corrections in the label frames GUI in DLC, add -addbp to the command line call


Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 21 Oct 2020
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import re
import warnings
from deeplabcut.utils.auxiliaryfunctions import read_config

warnings.filterwarnings('ignore', category=pd.io.pytables.PerformanceWarning)

# TODO: set up to call deeplabcut functions for "add video" and "extract frames", including mannually passing a set of frame numbers
# TODO: add flag to assign to specific individual (assuming separate xypts.csv files for each individual by passing individual name from config

def dlt2dlclabels(config, xyfname, vid, cnum, offset, flipy=True, addbp=False):
    # make paths into Paths
    config=Path(config)
    #load dlc config
    cfg = read_config(config)
    scorer = cfg['scorer']
    ma = True if cfg['multianimalproject'] == 'true' else False
    if ma:
        individuals = cfg['individuals']
        bodyparts = cfg['multianimalbodyparts']
    else:
        bodyparts=cfg['bodyparts']
    coords = ['x', 'y']
    xyfname=Path(xyfname)

    vid=Path(vid)
    camname=vid.stem
    labdir = Path(cfg['project_path']) / 'labeled-data' / camname

    # load xypts file to dataframe
    xypts = pd.read_csv(xyfname)
    xypts = xypts.astype('float64')
    # just get the columns for this camera
    camstr = 'cam_{}_'.format(cnum)
    thiscam = [x for x in xypts.columns if camstr in x]
    xypts = xypts[thiscam]
    newcols = {}
    #store track name and column index - start of tracks - in dict
    for i in range(0, len(xypts.columns), 2):
        newcol = xypts.columns[i].split('_')[0]
        newcols[newcol]=i

    #find ./CollectedData_scorerintitials.h5 in labdir
    colldata = list(labdir.glob('**/CollectedData_*.h5'))

    # find extracted images
    imgs = list(labdir.glob('**/*.png'))

    # if the labeled data file has NOT already been created with DLC label frames function
    if len(colldata) == 0:
        # no file exists, check to see if images extracted, and make the file based on config

        index = ['labeled-data/{}/{}'.format(camname,im.name) for im in imgs]
        # build the empty df
        # get tracknames from cfg
        if ma:
            header = pd.MultiIndex.from_product([[scorer],
                                             individuals,
                                             bodyparts,
                                             coords],
                                             names=['scorer', 'individuals','bodyparts', 'coords'])
        else:
            header = pd.MultiIndex.from_product([[scorer],
                                                 bodyparts,
                                                 coords],
                                                names=['scorer', 'bodyparts', 'coords'])
        #copy just the rows of interest from DLT to a new df
        #get frame numbers from imgs, from full path, after img, before .png
        idx = [int(re.findall(r'\d+', s)[0]) for s in [x.stem for x in imgs]]
        df = pd.DataFrame(np.nan, columns=header, index=index)


    else:
        # the file has already been created
        #load the file
        df = pd.read_hdf(colldata[0], 'df_with_missing')
        df.sort_index(inplace=True)

    if offset < 0:
        # the DLT digitized value on the n-th row was actually digitized at n+offset frame
        # e.g. if offset = -5, a point digitized in the first frame of the video will be placed
        # on the 5th row of the xypts csv file, so negative offsets mean that many blank rows
        # need to be removed from the front of the df
        print('dropping offset')
        xypts.drop(range(-1 * offset), inplace=True)
        xypts.reset_index(drop=True, inplace=True)

    if offset > 0:
        # remove that many rows from the end of the df
        xypts.drop(range(len(xypts) - offset, len(xypts)), inplace=True)


    if flipy is True:
        print('flipping')
        # get the vertical resolution from cropped parameter in config
        height = int(cfg['video_sets'][str(vid)]['crop'].split(',')[3])
        # flip the y-coordinates (origin is lower left in Argus and DLTdv 1-7, upper left in openCV, DLC, DLTdv8)
        ycols = [x for x in xypts.columns if '_y' in x]
        xypts.loc[:, ycols] = height - xypts.loc[:, ycols]



    # make if option flag is thrown, it checks if any bodypart x/y is empty
    if addbp:
        newbp=[]
        indx=[]
        for bp in bodyparts:
            #isolate the bodypart
            if ma:
                _ = df.loc[:, (scorer, individuals[0], bp)]
            else:
                _ = df.loc[:, (scorer, bp)]
            #find empty rows
            r = _.index[_.isnull().all(1)]
            #if there are empty rows for that bp
            if len(r) > 0:
                # add to list of places to fill
                newbp.extend([bp] * len(r))
                indx.extend(r)
        news = list(zip(indx, newbp))
        for new in news:
            xyrow = int(re.findall(r'img(\d+)\.png', new[0])[0])
            bp = new[1]
            if ma:
                df.loc[new[0], (scorer, individuals[0], bp, ['x', 'y'])] = xypts.loc[
                    xyrow, ['{}_cam_{}_x'.format(bp, cnum), '{}_cam_{}_y'.format(bp, cnum)]].values
            else:
                df.loc[new[0], (scorer, bp, ['x', 'y'])] = xypts.loc[
                    xyrow, ['{}_cam_{}_x'.format(bp, cnum), '{}_cam_{}_y'.format(bp, cnum)]].values

    else:
        # go through df find indexes without any entries, extract those entries from xydata, and add
        news = df.index[df.isnull().all(1)]
        # go through news and get insert digitized points from xydata
        for new in news:
            for bp in bodyparts:
                xyrow = int(re.findall(r'img(\d+)\.png', new)[0])
                if ma:
                    df.loc[new, (scorer, individuals[0], bp, ['x', 'y'])] = xypts.loc[
                        xyrow, ['{}_cam_{}_x'.format(bp, cnum), '{}_cam_{}_y'.format(bp, cnum)]].values
                else:
                    df.loc[new, (scorer, bp, ['x', 'y'])] = xypts.loc[
                        xyrow, ['{}_cam_{}_x'.format(bp, cnum), '{}_cam_{}_y'.format(bp, cnum)]].values



    # replace DLT nans with empty entries for DLC formatting
    df.astype('float64')
    df.sort_index(inplace=True)

    # # save out hdf and csv files
    df.to_hdf(Path(labdir) / ('CollectedData_' + scorer + '.h5'), 'df_with_missing', format='table', mode='w')
    df.to_csv(Path(labdir) / ('CollectedData_' + scorer + '.csv'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='convert argus to DLC labeled frames for training')
    parser.add_argument('-config', help='input path to DLC config file')
    parser.add_argument('-xy',
                        help='input path to xypts file')
    parser.add_argument('-vid', help='input path to video file')
    parser.add_argument('-cnum', default=1, help='enter 1-indexed camera number for extraction')
    parser.add_argument('-flipy', default=True,
                        help='flip y coordinates - necessary for DLTdv versions 1-7 and Argus, set to False for DLTdv8')
    parser.add_argument('-offset', default=0, type=int, help='enter offset of chosen camera as integer')
    parser.add_argument('-addbp', default=False, help='if new tracks/bodyparts were digitized in Argus/DLTdv, add this flag to add those to labeled data')


    args = parser.parse_args()

    xyfname = args.xy
    labdir = args.labdir
    #vname = Path(args.vid)
    cnum = int(args.cnum) - 1
    numcams = int(args.numcams)

    dlt2dlclabels(config, xyfname, vid, cnum, int(args.offset), flipy=args.flipy, addbp=args.addbp)

