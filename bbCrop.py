"""
Uses DLC formatted xypts of ul (upper left) and br (bottom right) bounding boxes to make a new video of cropped frames.
New video has size = (max bb width, max bb height) padded with black on right and bottom
If no bounding box is available for a frame, inserts a black frame so frame numbers are consistent.
Saves as vidname_cropped.ext to same directory as original video

Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 6 Feb 2020
"""

import argparse
from pathlib import Path
import cv2
import numpy as np
import pandas as pd

def main(vidpath, xypath):
    # load xypts
    bbdata = pd.read_hdf(xypath, 'df_with_missing')
    scorer = bbdata.loc[:,data.columns.get_values()[0][0]]
    # find maxwidth and maxheight
    maxwidth = max(bbdata.loc[:, (scorer, 'br', 'x')] - bbdata.loc[:, (scorer, 'ul', 'x')])
    maxheight = max(bbdata.loc[:, (scorer, 'br', 'y')] - bbdata.loc[:, (scorer, 'ul', 'y')])

    # make a template black frame
    allblack = np.zeros((maxwidth, maxheight, 3), np.uint8)
    # load video
    cap = cv2.VideoCapture(vidpath)
    numfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # set up video writer with size and codecs
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    outpath = vidpath.parent / (str(vidpath.stem) + '.mov')
    out = cv2.VideoWriter(outpath, fourcc, fps, (maxwidth, maxheight))
    #cv2.namedWindow("output")

    # loop through frames
    for i in range(numfr):
        success, frame = cap.read()
        cropped = allblack.copy()
        if not success:
            print('failed to load frame: ', i)
        else:
            #get coords if they all exist
            if np.all(np.isfinite(bbdata.loc[i,:])):
                xmin = bbdata.loc[i, ('ul', 'x')]
                xmax = bbdata.loc[i, ('br', 'x')]
                ymin = bbdata.loc[i, ('ul', 'y')]
                ymax = bbdata.loc[i, ('br', 'y')]
                cropped[0: xmax-xmin, 0: ymax - ymin, :] = frame[xmin:xmax, ymin:ymax, :]
        out.write(cropped)

    # exit
    cap.release()
    out.release()
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