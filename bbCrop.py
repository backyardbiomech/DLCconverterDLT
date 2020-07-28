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
    # load xypts
    print('loading bb xypts')
    data = pd.read_hdf(xypath, key='df_with_missing')
    # bbdata=bbdata.replace(np.nan, 0)
    # bbdata=bbdata.astype('float64')

    # loop through individuals for multianimal tracking
    # initialize dict of bbdata[individualName]:df[bodyparts][coords]
    bbdata={}
    if 'individuals' in data.columns.names:
        for animal_name, df_ in data.groupby(level='individuals', axis=1):
            temp = df_.droplevel(['scorer', 'individuals'], axis=1)
            temp = temp[['ul','br']]
            #temp just has headers of bodyparts and coords (x, y, liklihood)
            if animal_name != 'single':
                #TODO: also test if all values are nan for this individual
                temp['ul'] = np.floor(temp['ul'])
                temp['br'] = np.ceil(temp['br'])
                #TODO: should drop likelihood columns or threshold based on flag
                # fill nans and make true int for opencv
                temp.fillna(0, inplace=True)
                temp = temp.astype(int)
                # if either corner is missing, zero out the row
                ulz = temp['ul'][['x','y']].eq(0).all(axis=1)
                brz = temp['br'][['x','y']].eq(0).all(axis=1)
                temp.loc[ulz] = 0
                temp.loc[brz] = 0
                # if all zeros (no data for individual) move on
                if temp.eq(0).all(axis=None):
                    continue
                # save bbdata with these integers to use in cropped2full.py and dlt2dlc.py
                datapath = Path(xypath.parent) / (str(xypath.stem) + "_{}_cropped".format(animal_name))
                print("saving rounded data to {}".format(str(datapath)))
                temp.to_hdf(str(datapath) + '.h5', key='df_with_missing', mode='w', nan_rep='')
                temp.to_csv(str(datapath) + '.csv')

                bbdata[animal_name] = {}
                bbdata[animal_name]['df'] = temp

    #loop through animals, load video, write cropped video for each
    for animal_name in bbdata.keys():
        print('working on {}'.format(animal_name))
        df = bbdata[animal_name]['df']
        # find maxwidth and maxheight
        diff = df['br'] - df['ul']
        maxwidth = (np.nanmax(diff['x']))
        maxheight = (np.nanmax(diff['y']))

        # make a template black frame
        allblack = np.zeros((maxheight, maxwidth, 3), np.uint8)

        # look in the index to see if these are frame numbers, or paths to extracted images
        # this is based on the labeled-data format from DLC, incase DLT was used to label all cropped frames
        # if paths, convert to just frame numbers
        if '.png' in str(df.index.tolist()[0]):
            im = [int(Path(x).stem[-4:]) for x in df.index.values]
            df.index.values = im
        else:
            im = df.index.tolist()
        # load video
        print('loading video')
        cap = cv2.VideoCapture(str(vidpath))
        numfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        print("video has {} frames".format(numfr))
        # set up video writer with size and codecs
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        outpath = xypath.parent / (str(vidpath.stem) + '_{}_cropped.mov'.format(animal_name))
        out = cv2.VideoWriter(str(outpath), fourcc, fps, (maxwidth, maxheight), True)
        # cv2.namedWindow('output')

        # loop through frames
        waitvar = 1
        for i in range(numfr):
            if i % 100 == 0:
                print('frame {} of {}.'.format(i, numfr))
            success, frame = cap.read()
            cropped = allblack.copy() #writes all black frame if not all points are present
            if not success:
                print('failed to load frame: ', i)
            else:
                # get coords if they all exist
                if (i in im) and np.count_nonzero(df.loc[i,(['ul', 'br'], ['x','y'])]) == 4:
                    xmin = df.loc[i, ('ul', 'x')]
                    xmax = df.loc[i, ('br', 'x')]
                    ymin = df.loc[i, ('ul', 'y')]
                    ymax = df.loc[i, ('br', 'y')]
                    cropped[0: ymax - ymin, 0: xmax - xmin, :] = frame[ymin:ymax, xmin:xmax, :]
                    # cv2.imshow('output', cropped)
            out.write(cropped)
            k = cv2.waitKey(waitvar) & 0xFF
            if k == 27:
                break

        # exit
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        print('Saved cropped frames to {}'.format(str(outpath)))


    # scorer = bbdata.columns.get_level_values('scorer')[0]
    # # convert to ints
    # bbdata[scorer]['ul'] = np.floor(bbdata[scorer]['ul'])
    # bbdata[scorer]['br'] = np.ceil(bbdata[scorer]['br'])
    # bbdata = bbdata.astype(int)
    #
    # # save bbdata with these integers to use in cropped2full.py and dlt2dlc.py
    # datapath = Path(xypath.parent) / (str(xypath.stem) + '_cropped')
    # print('saving rounded data to {}'.format(str(datapath)))
    # bbdata.to_hdf(str(datapath) + '.h5', key='df_with_missing', mode='w', nan_rep='')
    # bbdata.to_csv(str(datapath) + '.csv')
    #
    # # fill nans and make true int for opencv
    # bbdata.fillna(0, inplace=True)

    # find maxwidth and maxheight
    # diff = bbdata[scorer]['br'] - bbdata[scorer]['ul']
    # maxwidth = (np.nanmax(diff['x']))
    # maxheight = (np.nanmax(diff['y']))

    # # make a template black frame
    # allblack = np.zeros((maxheight, maxwidth, 3), np.uint8)

    # load video
    # print('loading video')
    # cap = cv2.VideoCapture(str(vidpath))
    # numfr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # fps = cap.get(cv2.CAP_PROP_FPS)
    # print('video has {} frames'.format(numfr))
    # # set up video writer with size and codecs
    # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    # outpath = xypath.parent / (str(vidpath.stem) + '_cropped.mov')
    # out = cv2.VideoWriter(str(outpath), fourcc, fps, (maxwidth, maxheight), True)
    # #cv2.namedWindow('output')
    #
    # # look in the index to see if these are frame numbers, or paths to extracted images (from labeled data of DLC)
    # if '.png' in bbdata.index[0]:
    #     im = [int(Path(x).stem[-4:]) for x in bbdata.index]
    #     bbdata.index = im
    # else:
    #     im = bbdata.index
    #
    # # loop through frames
    # waitvar = 1
    # for i in range(numfr):
    #     if i % 100 == 0:
    #         print('frame {} of {}.'.format(i, numfr))
    #     success, frame = cap.read()
    #     cropped = allblack.copy()
    #     if not success:
    #         print('failed to load frame: ', i)
    #     else:
    #         # get coords if they all exist
    #         if (i in im) and np.count_nonzero(bbdata.loc[i]) == 4:
    #             xmin = bbdata.loc[i, (scorer, 'ul', 'x')]
    #             xmax = bbdata.loc[i, (scorer, 'br', 'x')]
    #             ymin = bbdata.loc[i, (scorer, 'ul', 'y')]
    #             ymax = bbdata.loc[i, (scorer, 'br', 'y')]
    #             cropped[0: ymax-ymin, 0: xmax-xmin, :] = frame[ymin:ymax, xmin:xmax, :]
    #             #cv2.imshow('output', cropped)
    #     out.write(cropped)
    #     k = cv2.waitKey(waitvar) & 0xFF
    #     if k == 27:
    #         break
    #
    # # exit
    # cap.release()
    # out.release()
    # cv2.destroyAllWindows()
    # print('Saved cropped frames to {}'.format(str(outpath)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='crop videos to bounding boxes')

    parser.add_argument('vid', help='full path video to crop')
    parser.add_argument('coords', help='full path to h5 file containing digitized data')

    args = parser.parse_args()

    vidpath = Path(args.vid)
    xypath = Path(args.coords)

    main(vidpath, xypath)