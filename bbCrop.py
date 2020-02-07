"""
Uses DLC formatted xypts of ul (upper left) and br (bottom right) bounding boxes to make a new video of cropped frames.
New video has size = (max bb width, max bb height) padded with black on right and bottom
If no bounding box is available for a frame, inserts a black frame so frame numbers are consistent.
Saves as vidname_cropped.mov to same directory as original video, and saves rounded bounding box coordinates for use in cropped2full.py

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
    # load xypts
    bbdata = pd.read_hdf(xypath, 'df_with_missing')
    scorer = bbdata.columns.get_values()[0][0]
    # convert to ints
    bbdata[scorer]['ul'] = np.floor(bbdata[scorer]['ul'])
    bbdata[scorer]['br'] = np.ceil(bbdata[scorer]['br'])
    # save bbdata with these integers to use in cropped2full.py
    datapath = Path(vidpath.parent) / (str(xypath.stem) + '_cropped')
    bbdata.to_hdf(str(datapath) + '.h5', key='df_with_missing', mode='w')
    bbdata.to_csv(str(datapath) + '.csv')

    # fill nans and make true int for opencv
    bbdata.fillna(0, inplace=True)
    bbdata = bbdata.astype(int)
    # find maxwidth and maxheight
    diff = bbdata[scorer]['br'] - bbdata[scorer]['ul']
    maxwidth = (np.nanmax(diff['x']))
    maxheight = (np.nanmax(diff['y']))

    # make a template black frame
    allblack = np.zeros((maxheight, maxwidth, 3), np.uint8)

    # load video
    cap = cv2.VideoCapture(str(vidpath))
    numfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # set up video writer with size and codecs
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    outpath = vidpath.parent / (str(vidpath.stem) + '_cropped.mov')
    out = cv2.VideoWriter(str(outpath), fourcc, fps, (maxwidth, maxheight), True)
    cv2.namedWindow('output')

    # look in the index to see if these are frame numbers, or paths to extracted images (from labeled data of DLC)
    if '.png' in bbdata.index[0]:
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
            if (i in im) and np.count_nonzero(bbdata.loc[i]) == 4:
                xmin = bbdata.loc[i, (scorer, 'ul', 'x')]
                xmax = bbdata.loc[i, (scorer, 'br', 'x')]
                ymin = bbdata.loc[i, (scorer, 'ul', 'y')]
                ymax = bbdata.loc[i, (scorer, 'br', 'y')]
                cropped[0: ymax-ymin, 0: xmax-xmin, :] = frame[ymin:ymax, xmin:xmax, :]
                cv2.imshow('output', cropped)
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