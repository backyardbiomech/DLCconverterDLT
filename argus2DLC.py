# takes marked and named tracks and converts them to DLC labled format, while grabbing and exporting proper video frames
# wiki Page (on github) some notes

import argparse
import pandas as pd
import numpy as np
import cv2
from pathlib import Path

def main(fname, vname, cnum, numcams, scorer, opath):
    # edit any paths
    # load xypts file to dataframe
    xypts = pd.read_csv(fname)
    # narrow down to just the columns pertaining to the proper camera
#     print(len(xypts.columns))

# make Set of frames to be extracted (combine lists, set, sort)
    frames = []
    trackNames = []
    dataDict = {}
    for i in range(int(len(xypts.columns)/(2*numcams))):
        icol = i*(2*numcams) + (cnum * 2)
        arr = xypts.iloc[:, icol].to_numpy()
        frs = list(np.where(np.isfinite(arr))[0])
        frames += frs 
        # get the track name
        if len(frs) > 0:
            trackNames.append(xypts.columns[icol])#.split('_cam')[0])
            trackNames.append(xypts.columns[icol+1])
      
    frames = sorted(set(frames))
#     collist = 
    data = xypts.loc[frames,trackNames]
#     print(data)
    #colnames needs to be duplicated tracknames [head, head, arm, arm...]
    #colnames = [ (x, x) for x in trackNames]
    #colnames = [item for t in colnames for item in t] 
    # initialize dataFrame to store
    colnames = [ x.split('_cam')[0] for x in trackNames[0:-1:2]]
    s = [scorer] #*len(colnames)
    coords = ['x','y']# * int(len(colnames)/2)
#     print(len(s), len(colnames),len(coords))
    header = pd.MultiIndex.from_product([s,
                                     colnames,
                                     coords],
                                    names=['scorer','bodyparts', 'coords'])
#     df = pd.DataFrame(data, 
#                       index=frames, 
#                       columns=header)
    df=data.copy()
    df.columns=header
    #TODO convert NaN to empty (blank string: '' ?)
    # make a new directory with the name of the video for the hdf, csv, and pngs
    
    # save out hdf and csv files
    frame.to_hdf(opath / ('CollectedData_' + scorer + '.h5'), key='df_with_missing', mode='w')
    frame.to_csv(opath / ('CollectedData_' + scorer + '.csv'))

    # load video
    cap = cv2.VideoCapture(str(vidfile))
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
            #save image
            cv2.




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
                    
    # parser.add_argument('-sf', '--sampfreq', help = 'sampling frequency in sf')
    # parser.add_argument('-c', '--cutoff', help = 'lowpass cutoff frequency')

    args = parser.parse_args()
    
    fname = args.xy
    vname = args.vid
    cnum = int(args.cnum)-1
    numcams = int(args.numcams)
    scorer = args.scorer
    # make a new dir for output
    if not args.newpath:
        opath = vname.parent / 'labeled-data' / vname.stem
    else:
        opath = Path(args.newpath)
    opath = Path(opath)
    opath.mkdir(parents = True, exists_ok = True)
    
    main(fname, vname, cnum, numcams, scorer, opath)
    # sf = int(args.sampfreq)
    # c = int(args.cutoff)
    # main(args.filename, sf, c)