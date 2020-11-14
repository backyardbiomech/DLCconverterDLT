"""
Uses DLC formatted xypts of ul (upper left) and br (bottom right) bounding boxes to make a new video of cropped frames.
New video has size = (max bb width, max bb height) padded with black on right and bottom
If no bounding box is available for a frame, inserts a black frame so frame numbers are consistent.
Saves as vidname_cropped.mov to same directory as original video, and saves rounded bounding box coordinates for use in cropped2full.py and dlt2cropped.py

Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 7 Feb 2020
"""

import argparse
from pathlib import Path
import cv2
import numpy as np
import pandas as pd

def main(vidpath, xypath):
    vidpath=Path(vidpath)
    xypath=Path(xypath)
    # load xypts

    print('loading bb xypts')
    bbdata = pd.read_hdf(xypath, key='df_with_missing')
    bbdata=bbdata.replace('', 0)
    bbdata=bbdata.astype('float64')
    scorer = bbdata.columns.get_level_values('scorer')[0]
    indivs = sorted(set(bbdata.columns.get_level_values('individuals')))

    # convert to ints
    bbdata[scorer][indivs[0]]['ul'] = np.floor(bbdata[scorer][indivs[0]]['ul'])
    bbdata[scorer][indivs[0]]['br'] = np.ceil(bbdata[scorer][indivs[0]]['br'])
    # bbdata[bbdata == -1] = ''
    #bbdata = bbdata.astype('int64')
    # save bbdata with these integers to use in cropped2full.py
    datapath = Path(xypath.parent) / (str(xypath.stem) + '_cropped')
    print('saving rounded data to {}'.format(str(datapath)))
    bbdata.to_hdf(str(datapath) + '.h5', key='df_with_missing', mode='w')
    bbdata.to_csv(str(datapath) + '.csv')

    # fill nans and make true int for opencv
    bbdata.fillna(0, inplace=True)
    bbdata = bbdata.astype(int)
    # find maxwidth and maxheight
    diff = bbdata[scorer][indivs[0]]['br'] - bbdata[scorer][indivs[0]]['ul']
    maxwidth = (np.nanmax(diff['x']))
    maxheight = (np.nanmax(diff['y']))

    # make a template black frame
    allblack = np.zeros((maxheight, maxwidth, 3), np.uint8)

    # load video
    print('loading video')
    cap = cv2.VideoCapture(str(vidpath))
    numfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print('video has {} frames'.format(numfr))
    # set up video writer with size and codecs
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    outpath = xypath.parent / (str(vidpath.stem) + '_cropped.mp4')
    out = cv2.VideoWriter(str(outpath), fourcc, fps, (maxwidth, maxheight), True)
   # cv2.namedWindow('output')

    # look in the index to see if these are frame numbers, or paths to extracted images (from labeled data of DLC)
    if bbdata.index.dtype != np.int64:
        im = [int(Path(x).stem[-4:]) for x in bbdata.index]
        bbdata.index = im
    else:
        im = bbdata.index

    # loop through frames
    waitvar = 1
    for i in range(numfr):
        if i % 100 == 0:
            print('frame {} of {}.'.format(i, numfr))
        success, frame = cap.read()
        cropped = allblack.copy()
        if not success:
            print('failed to load frame: ', i)
        else:
            # get coords if they all exist
            if (i in im):# and np.count_nonzero(bbdata.loc[i]) == 4:
                print('here')
                xmin = bbdata.loc[i, (scorer, indivs[0], 'ul', 'x')]
                xmax = bbdata.loc[i, (scorer, indivs[0], 'br', 'x')]
                ymin = bbdata.loc[i, (scorer, indivs[0], 'ul', 'y')]
                ymax = bbdata.loc[i, (scorer, indivs[0], 'br', 'y')]
                cropped[0: ymax-ymin, 0: xmax-xmin, :] = frame[ymin:ymax, xmin:xmax, :]
                #cv2.imshow('output', cropped)
        out.write(cropped)
        k = cv2.waitKey(waitvar) & 0xFF
        if k == 27:
            break

    # exit
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print('Saved cropped frames to {}'.format(str(outpath)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='crop videos to bounding boxes')

    parser.add_argument('vid', help='full path video to crop')
    parser.add_argument('coords', help='full path to h5 file containing digitized data')

    args = parser.parse_args()

    vidpath = Path(args.vid)
    xypath = Path(args.coords)

    main(vidpath, xypath)