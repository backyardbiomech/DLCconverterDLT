"""
Takes dlc tracked coordinates (from <DLC_project_folder>/videos/<name>.hd5) files from multiple DLT calibrated cameras, and exports a DLTdv or Argus based DLT -xypts.csv file. Will also make "dummy" -xyzpts.csv, -offsets.csv, and -xyzres.csv for backwards compatibility.

When passing the '-newpath' flag, input a full path ending with a filename prefix. e.g. /path/to/desired/folder/trial01
will make trial01-xypts.csv, trial01-xyzpts.csv, trial01-xyzres.csv, trial01-offsets.csv

That file can then be loaded into DLTdv* or Argus, along with the camera profile and DLT coefficents files. Saving data there then produces an updated -xyzpts.csv file.

Argus and DLTdv* also contain 3d_reconstruct commands that can be called on the command line with the xypts file output here.

"""

import argparse
import pandas as pd
import numpy as np
import cv2
from pathlib import Path

def main(opath, camlist):
    numcams = len(camlist)
    
    for c in range(numcams):
        #load the hd5
        camdata = pd.read_hdf(camlist[c], 'df_with_missing')
        # for the first file, initialize the new dataframe
        if c = 0:
            numframes = max(camdata.index.values)
            tracks = camdata.columns[0:-1:3]
            #create empty array
            arr = np.empty((numframes, tracks * 2 * numcams)) * np.nan
        # fill the array
        for i in range(len(comdata.columns)/3):
            incol = i*3
            outcol = (i * 2 * numcams) + (2 * c)
            arr[camdata.index, outcol:outcol+2] = camdata.iloc[camdate.index, incol:incol+2]
    # make col names
    xycols = ['{}_cam_{}_{}'.format(x, c, d) for x in tracknames for c in range(1,numcams+1) for d in ['x', 'y']]
    # convert to dataframe
    xydf = pd.DataFrame(xycols, columns = xycol, index = range(numframes))
    # write to CSV
    xydf.to_csv((opath / '-xypts.csv'))
    
    # make "dummy" xyzpts
    xyzcols = ['{}_{}'.format(x, d) for x in tracknames for d in ['x', 'y', 'z']]
    xyzdf = pd.DataFrame(np.nan, columns = xyzcols, index = range(numframes))
    xyzdf.to_csv((opath / '-xyzpts.csv'))
    # dummy resid
    residdf = pd.DataFrame(np.nan, columns = tracknames, index=range(numframes))
    residdf.to_csv((opath / '-xyzres.csv'))
    # dummy offsets
    offcols = ['camera_{}'.format(cnum) for cnum in range(1, numcams+1)]
    offdf = pd.DataFrame(0, columns = offcols, index=range(numframes))
    offdf.to_csv((opath / '-offsets.csv')


if __name__== '__main__':
    parser = argparse.ArgumentParser(
    description='convert argus to DLC labeled frames for training')

    parser.add_argument('-dlctracks', nargs='+', help='input paths of DLC tracked coordinates (hd5) in order used in DLT calibration, each path separated by a space')
    parser.add_argument('-newpath', type=str, help = 'enter a path for saving, will overwrite if it already exists, should not be in DLC project folder, should end with filename prefix')

    args = parser.parse_args()
    opath = Path(args.newpath)
    opath.mkdir(parents = True, exist_ok = True)
    
    main(opath, args.dlctracks)
