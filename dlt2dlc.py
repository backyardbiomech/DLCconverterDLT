"""
Takes digitized frames from DLTdv or Argus based DLT 3D projects, exports hd5, csv, and images for training DeepLabCut with those images.

Before starting, the video file should be re-named something unique to the DLC project. 

Makes a new directory that can be copied directly into a deeplabcut_project_folder/labeled-images

You must also edit the deeplabcut project config.yaml file to include a path to the video (with the unique name), or "add video" to the DLC project.
"""

import argparse
import pandas as pd
import numpy as np
import cv2
from pathlib import Path

def main(fname, vname, cnum, numcams, scorer, opath):
    
    # load xypts file to dataframe
    xypts = pd.read_csv(fname)
    # make Set of frames to be extracted, and get tracknames
    frames = []
    trackNames = []
    for i in range(int(len(xypts.columns)/(2*numcams))):
        icol = i*(2*numcams) + (cnum * 2)
        arr = xypts.iloc[:, icol]#.to_numpy()
        frs = list(np.where(np.isfinite(arr))[0])
        frames += frs 
        # get the track name
        if len(frs) > 0:
            trackNames.append(xypts.columns[icol])
            trackNames.append(xypts.columns[icol+1])
    
    # get zero-indexed frame numbers that have digitized points in this camera
    frames = set(frames)
    # create a copy of just the relevant part of the data
    df = xypts.loc[frames,trackNames].copy()
    
    # get unique track names
    colnames = [ x.split('_cam')[0] for x in trackNames[0:-1:2]]
    # some standard multi-index headers
    s = [scorer]
    coords = ['x','y']
    
    # create the multi index header and apply it
    header = pd.MultiIndex.from_product([s,
                                     colnames,
                                     coords],
                                    names=['scorer','bodyparts', 'coords'])

    df.columns=header
    # replace DLT nans with empty entries
    df.fillna('', inplace=True)
    indexPath = Path('labeled-data')
    indexPath = indexPath / vname.stem
    #df.index.values = [str(indexPath / 'img{:04d}.png'.format(df.index.values[x])) for x in range(len(df.index.values))]
    df.rename(inplace = True, index = lambda s: str(indexPath / 'img{:04d}.png'.format(s)))
    # save out hdf and csv files
    df.to_hdf(opath / ('CollectedData_' + scorer + '.h5'), key='df_with_missing', mode='w')
    df.to_csv(opath / ('CollectedData_' + scorer + '.csv'))

    # load video
    cap = cv2.VideoCapture(str(vname))
    #get some info about the file (in case I need size to save png
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    width = size[0]
    height = size[1]
    numfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # loop through frames
    for fr in frames:
        #set the start frame for analysis
        cap.set(cv2.CAP_PROP_POS_MSEC, fr*1000/fps)
        success, frame = cap.read()
        if success:
            # make file name
            outimg = opath / ('img{:04d}.png'.format(fr))
            #save image
            cv2.imwrite(str(outimg), frame)




if __name__== '__main__':
    parser = argparse.ArgumentParser(
    description='convert argus to DLC labeled frames for training')

    parser.add_argument('-xy', 
                         help='input path to xyzpts file')
    parser.add_argument('-vid', help='input path to video file')
    parser.add_argument('-cnum', default=1, help='enter 1-indexed camera number for extraction')
    parser.add_argument('-numcams', default=3, help='enter number of cameras')
    parser.add_argument('-scorer', default='bej', help='enter scorer name to match DLC project')
    parser.add_argument('-newpath', default = None, help = 'enter a path for saving, existing target folder will be overwritten, should end with "labeled-data/<videoname>"')
    
    #TODO: add ability to pass frames for extraction instead of all frames?

    args = parser.parse_args()
    
    fname = Path(args.xy)
    vname = Path(args.vid)
    cnum = int(args.cnum)-1
    numcams = int(args.numcams)
    scorer = args.scorer
    
    # make a new dir for output
    if not args.newpath:
        opath = vname.parent / 'labeled-data' / vname.stem
    else:
        opath = Path(args.newpath)
    opath.mkdir(parents = True, exist_ok = True)
    
    main(fname, vname, cnum, numcams, scorer, opath)
