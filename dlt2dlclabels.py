"""
After extracting frames (which creates images and labeled data h5 and csv files) in a dlc project, this pulls labels for those frames from DLTdv or Argus based DLT 3D projects and saves to the dlc project

i.e., it skips the label frames DLC step

works for multianimal projects, but considers all labels to apply to individual 1

VERY IMPORTANT: Argus/DLTdv track names must exactly match DLC bodyparts in config for this to work

Works when no collected data file exists 20 Oct 2020, need to test when it exists already and more frames are extracted


Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 17 Oct 2020
"""

import argparse
import pandas as pd
import numpy as np
import cv2
from pathlib import Path
import re
import warnings
from deeplabcut.utils.auxiliaryfunctions import read_config

warnings.filterwarnings('ignore', category=pd.io.pytables.PerformanceWarning)


def dlt2dlclabels(config, xyfname, camname, cnum, numcams, flipy, offset):
    # make paths into Paths
    config=Path(config)
    #load dlc config
    cfg = read_config(config)
    scorer = cfg['scorer']
    individuals = cfg['individuals']
    bodyparts = cfg['multianimalbodyparts']
    coords = ['x', 'y']
    xyfname=Path(xyfname)
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
        header = pd.MultiIndex.from_product([[scorer],
                                             individuals,
                                             bodyparts,
                                             coords],
                                             names=['scorer', 'individuals','bodyparts', 'coords'])
        #copy just the rows of interest from DLT to a new df
        #get frame numbers from imgs, from full path, after img, before .png
        idx = [int(re.findall(r'\d+', s)[0]) for s in [x.stem for x in imgs]]
        df = pd.DataFrame(np.nan, columns=header, index=index)


    else:
        # the file has been created
        #load the file
        df = pd.read_hdf(colldata[0], 'df_with_missing')

        #get track names, scorer, first individual name (all gotten from config now?
        # scorer = df.columns.get_level_values('scorer')[0]
        # ind = df.columns.get_level_values('individuals')[0]
        # tracks = df[scorer][ind].columns.get_level_values('bodyparts')
        print(scorer, ind, tracks)

        index = ['labeled-data/{}/{}'.format(camname, im.name) for im in imgs]
        news = []
        for im in index:
            if im not in df.index.values:
                news.extend(im)
        foo = pd.DataFrame(np.nan, columns=header, index=news)
        df.append(foo, inplace=True)
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

    # go through df find indexes without any entries, extract those entries from xydata, and add

    news = df.index[df.isnull().all(1)]

    # go through news and get insert digitized points from xydata
    for new in news:
        for bp in bodyparts:
            xyrow = int(re.findall(r'img(\d+)\.png', new)[0])
            df.loc[new, (scorer, individuals[0], bp, ['x', 'y'])] = xypts.loc[xyrow, ['{}_cam_{}_x'.format(bp, cnum), '{}_cam_{}_y'.format(bp, cnum)]].values

    # replace DLT nans with empty entries
    df.fillna('', inplace=True)
    # # save out hdf and csv files
    df.to_hdf(Path(labdir) / ('CollectedData_' + scorer + '.h5'), key='df_with_missing', mode='w')
    df.to_csv(Path(labdir) / ('CollectedData_' + scorer + '.csv'))

    # make Set of frames to be extracted (they have digitized points), and get tracknames
    # frames = []
    # trackNames = []
    # for i in range(int(len(xypts.columns) / (2 * numcams))):
    #     icol = i * (2 * numcams) + (cnum * 2)
    #     arr = xypts.iloc[:, icol]
    #     frs = list(np.where(np.isfinite(arr))[0])
    #     frames += frs
    #     # get the track name
    #     if len(frs) > 0:
    #         trackNames.append(xypts.columns[icol])
    #         trackNames.append(xypts.columns[icol + 1])
    #
    # # get zero-indexed frame numbers that have digitized points in this camera
    # frames = sorted(set(frames))
    # # create a copy of just the relevant part of the data
    # df = xypts.loc[frames, trackNames].copy()

    # if flipy is True:
    #     print('flipping')
    #     # flip the y-coordinates (origin is lower left in Argus and DLTdv 1-7, upper left in openCV, DLC, DLTdv8)
    #     ycols = [x for x in df.columns if '_y' in x]
    #     df.loc[:, ycols] = height - df.loc[:, ycols]

    # # get unique track names
    # colnames = [x.split('_cam')[0] for x in trackNames[0:-1:2]]
    # # some standard multi-index headers for DLC compatability
    # s = [scorer]
    # coords = ['x', 'y']
    #
    # # create the multi index header and apply it
    # header = pd.MultiIndex.from_product([s,
    #                                      colnames,
    #                                      coords],
    #                                     names=['scorer', 'bodyparts', 'coords'])
    #
    # df.columns = header
    #
    # # if a crop file has been passed, convert full coordinates to the cropped coordinates
    # if croppath:
    #     dfnew = df.copy() * np.nan
    #     cropped = pd.read_hdf(croppath, 'df_with_missing')
    #     # get the scorer
    #     scorer = cropped.columns.get_level_values('scorer')[0]
    #     ul = cropped[scorer]['ul'][['x', 'y']]
    #     # if it's analyzed data, index is already set as 0-indexed frame integer, do nothing
    #     if cropped.index.dtype != 'int':
    #         # it's DLT created or training data during testing, indexed by a path to a training image, which is numbered
    #         new = [Path(x).stem for x in ul.index]
    #         ul.index = [int(re.findall(r'\d+', s)[0]) for s in new]
    #     # correct for offsets by reindexing, effectively inserting blank rows at the start or end of cropped
    #     # ul.index = ul.index - offset
    #     # get tracks in new format
    #     tracks = df.columns.get_level_values('bodyparts')[::2]
    #     for track in tracks:
    #         dfnew.loc[dfnew.index.intersection(ul.index), (scorer, track)] = df.loc[
    #                                                                              dfnew.index.intersection(ul.index), (
    #                                                                              scorer, track)].values - ul.loc[
    #                                                                                                       dfnew.index.intersection(
    #                                                                                                           ul.index),
    #                                                                                                       :].values
    #     df = dfnew
    #
    # # replace DLT nans with empty entries
    # df.fillna('', inplace=True)
    # indexPath = Path('labeled-data')
    # indexPath = indexPath / vname.stem
    #
    # # use the index int values to make names since this should line up with frame numbers
    # df.rename(inplace=True, index=lambda s: str(indexPath / 'img{:04d}.png'.format(s)))
    # # replace blank cells with nan, and convert to float64 dtype
    # df = df.replace(r'^\s*$', np.nan, regex=True)
    #
    # # save out hdf and csv files
    # df.to_hdf(opath / ('CollectedData_' + scorer + '.h5'), key='df_with_missing', mode='w')
    # df.to_csv(opath / ('CollectedData_' + scorer + '.csv'))
    #
    # if saveImgs is True:
    #     numfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    #     fps = cap.get(cv2.CAP_PROP_FPS)
    #     print("Writing images from video...")
    #     # loop through frames
    #     for fr in frames:
    #         # set the start frame for analysis
    #         cap.set(cv2.CAP_PROP_POS_MSEC, fr * 1000 / fps)
    #         success, frame = cap.read()
    #         if success:
    #             # make file name
    #             outimg = opath / ('img{:04d}.png'.format(fr))
    #             # save image
    #             cv2.imwrite(str(outimg), frame)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='convert argus to DLC labeled frames for training')
    parser.add_argument('-config', help='input path to DLC config file')
    parser.add_argument('-xy',
                        help='input path to xypts file')
    parser.add_argument('-camname', help='directory name in labeled-data in DLC project')
    #parser.add_argument('-vid', help='input path to video file')
    parser.add_argument('-cnum', default=1, help='enter 1-indexed camera number for extraction')
    parser.add_argument('-numcams', default=3, help='enter number of cameras')
    #parser.add_argument('-scorer', default='DLT', help='enter scorer name to match DLC project')
    #parser.add_argument('-saveImgs', default=True, help='save images in "labeled-data" folder')
    #parser.add_argument('-newpath', default=None,
    #                    help='enter a path for saving, existing target folder will be overwritten, should end with "labeled-data/<videoname>"')
    parser.add_argument('-flipy', default=True,
                        help='flip y coordinates - necessary for DLTdv versions 1-7 and Argus, set to False for DLTdv8')
    parser.add_argument('-offset', default=0, type=int, help='enter offset of chosen camera as integer')
    #parser.add_argument('-crop', default=None, help='input path to DLC crop file')
    #parser.add_argument('-origvid', default=None, help='input path to original video if adjusting cropped data')

    # TODO: add ability to pass frames for extraction instead of all frames?

    args = parser.parse_args()

    xyfname = args.xy
    labdir = args.labdir
    #vname = Path(args.vid)
    cnum = int(args.cnum) - 1
    numcams = int(args.numcams)
    # if args.crop:
    #     croppath = Path(args.crop)
    # else:
    #     croppath = None
    #
    # if args.origvid:
    #     origvidpath = Path(args.origvid)
    # else:
    #     origvidpath = None

    # make a new dir for output
    # if not args.newpath:
    #     opath = vname.parent / 'labeled-data' / vname.stem
    # else:
    #     opath = Path(args.newpath) / 'labeled-data' / vname.stem
    # if not opath.exists():
    #     opath.mkdir(parents=True, exist_ok=True)

    # dlt2dlclabels(fname, vname, cnum, numcams, args.scorer, opath, args.flipy, args.offset, croppath, origvidpath,
    #         args.saveImgs)
    dlt2dlclabels(config, xyfname, camname, cnum, numcams, args.flipy, int(args.offset))
