# DLC2DLT2DLC

A small set of utilities that allow conversion between the data storage formats of [DeepLabCut](https://github.com/AlexEMG/DeepLabCut) (DLC) and one of the DLT-based 3D tracking systems: either Ty Hedrick's [DigitizingTools](http://biomech.web.unc.edu/dltdv/) in MATLAB, or the Python-based [Argus](http://argus.web.unc.edu). These functions should allow you to use data previously digitized in a DLT system to create the files needed to train a DLC model, and to import DLC-tracked points back into a DLT 3D calibration to reconstruct 3D points. 

While DLC has 3D capabilities (using checkerboards), many field-based setups necessitate the ability to use a wand calibration (easywand or Argus). DLC can be used to auto-track the wand and/or subjects in each video (treated as separate 2D videos), then moved back to DLT for 3d reconstruction. 

Multi-camera setups that are not frame-synced (e.g. GoPros) must have offsets calculated (Argus Sync), and adjusted for. These scripts use those offset values.

**NOTE**: These have been tested on *minimal* sample data and in a single complete workflow. Be especially careful to make sure your data lines up on the appropriate frame of video, and that frame offsets are working correctly. Please feel free to test, edit, contribute, suggest.

Once they are well tested, I may include these functions directly in Argus, and welcome others to modify these to generate a similar set of MATLAB scripts for  DLTdv8.

## Getting Started

Download the scripts. Put them somewhere handy. Call them on the command-line.  See below.

## Usage ouline:
1. The videos used **for training** DeepLabCut must have unique names. If, like me, your DLT videos are all named `cam1.mp4`, `cam2.mp4`, etc, `renameVids.py` will help give unique names.
2. If you have data digitized in a DLT program that you want to use as labelled data in DLC:
    1. Use DLC to add videos to your project and extract frames
    2. Use `dlt2dlclabels.py` to skip the DLC labeling GUI. This requires DLC version 2.2b8 or higher.
    3. If you have multiple animals visible and are using multianimal DLC, then label each animal in separate DLT data files.
    4. DLT track names must exactly match bodyparts in DLC `config.yaml`.
3. Train DLC, and analyze your videos.
4. Use `dlc2dlt.py` to convert DLC coordinates back to DLT style coordinates (this is *might* be working with multianimal projects...not well tested as of 12 Nov. 2020)
5. In your DLT program (Argus or DLTdv), either load the videos and new data, or use command line functions in each to perform the 3D reconstruction with your dlt coefficients.  

## Detailed Usage

In all relevant functions, the flag `-flipy` defaults to `True` which is necessary if your data are from Argus, or DLTdv versions prior to 8.0. In those packages, the coordinate origin is in the lower left of the video, but the computer vision standard (used by DeepLabCut and by DLTdv8) is for the origin to be in the **upper** left. If you are using DLTdv8, just add `-flipy False` to the call.

### dlt2dlclabels

Many of us have lots of data already digitized in a DLT-calibrated environment. Those already digitized points can be used in place of "labeling" video in DeepLabCut. That's what dlt2dlc.py and dlt2dlclabels.py are for. It "essentially" replaces/parallels the labelling function in DLC.

```python
python dlt2dlclabels.py --help
usage: dlt2dlclabels.py [-h] [-config CONFIG] [-xy XY] [-vid VID] [-cnum CNUM]
                        [-flipy FLIPY] [-offset OFFSET] [-ind IND] [-addbp ADDBP]

convert Argus or DLTdv to DLC labeled frames for training

optional arguments:
  -h, --help      show this help message and exit
  -config CONFIG  input path to DLC config file
  -xy XY          input path to xypts file
  -vid VID        input path to video file
  -cnum CNUM      enter 1-indexed camera number for extraction
  -flipy FLIPY    flip y coordinates - necessary for DLTdv versions 1-7 and
                  Argus, set to False for DLTdv8, default = True
  -offset OFFSET  enter offset of chosen camera as integer
  -ind IND        enter 0-indexed individual number from config file.
                  xypts.csv must have only one indiv digitized
  -addbp          if new tracks/bodyparts were digitized in Argus/DLTdv, add
                  this flag to add those to already labeled data in DLC.
                  Not including this flag means the DLT data will overwrite any existing DLC labels for that video.

```
For example, 

```python
python dlt2dlclables.py -config /path/to/deeplabcut/project/config.yaml -xy /path/to/xypts/file-xypts.csv -vid /path/to/xypts/cam2.mp4 -cnum 2 -flipy False -offset -21 -ind 1 -addbp
```

will take the data and video from the second camera (with a -21 frame offset) in a three camera setup, with individual 2 digitized, and save those data in the `CollectedData` file of the relevant camera in the DLC project. With the `-addbp` flag, it will not overwrite existing data in that file. 


### dlc2dlt

If you have some beautifully accurate 3d DLT calibrations, but are sick of manually digitizing each video, then train and use DLC to digitize your videos independently.  Once they are digitized, dlc2dlt will create the needed files to complete DLT reconstruction. It essentially allows you to use DLC to replace the clicking part of DLT.

```python
python dlc2dlt.py --help
usage: dlc2dlt.py [-h] [-dlctracks DLCTRACKS [DLCTRACKS ...]]
                  [-newpath NEWPATH] [-flipy FLIPY]
                  [-offsets OFFSETS [OFFSETS ...]]

convert argus to DLC labeled frames for training

optional arguments:
  -h, --help            show this help message and exit
  -dlctracks DLCTRACKS [DLCTRACKS ...]
                        input paths of DLC tracked coordinates (h5) in order
                        used in DLT calibration, each path separated by a
                        space
  -newpath NEWPATH      enter a path for saving, will overwrite if it already
                        exists, should not be in DLC project folder, should
                        end with filename prefix
  -flipy FLIPY          flip y coordinates - necessar for Argus and DLTdv
                        versions 1-7, set to False for DLTdv8
  -offsets OFFSETS [OFFSETS ...]
                        enter offsets as space separated list including first
                        camera e.g.: -offsets 0 -12 2

  -like LIKE            set a likelihood threshold so that only good DLC fits
                        are allowed to pass. 0.9 by default.
```

for example, if you have a three camera DLT setup, and each camera has been tracked in DLC, and you want only the very best fits...

```python
python dlc2dlt.py -dlctracks /pathtoDLCproectfolder/videos/cam1tracked.h5 /pathtoDLCproectfolder/videos/cam2tracked.h5 /pathtoDLCproectfolder/videos/cam3tracked.h5 -newpath /a/path/to/somewhere/else/trial01DLCtracked -offsets 0 -20 34 -like 0.9999
```

will make the standard DLT files (4 of them) at new path, named trial01DLCtracked-xypts.csv, trial01DLCtracked-xyzpts.csv, trial01DLCtracked-xyzres.csv, trial01DLCtracked-offsets.csv. The -xyzpts and -xyzres files will be empty, but they must be created to be able to load the data into DLTdv or Argus.

To get xyz pts, load the new -xypts.csv as data in DLTdv or Argus as if you digitized it there, load your DLT coefficients, camera profiles, check the data, and save. Note that both DLTdv and Argus have command-line functions (dlt_reconstruct) to get the 3d points without loading in the GUI.


## Authors

* **Brandon E. Jackson, Ph.D.** 

## References

If you use this code, for now, please cite the appropriate DeepLabCut and Argus or DLTdv papers.

## License

This project is licensed under the GNU Lesser General Public License v3.0; see the [LICENSE.md](LICENSE.md) file for details. Note that the software is provided "as is", without warranty of any kind, express or implied. If you use the code, please cite DeepLabCut and either DLTdv or Argus.

