# DLC2DLT2DLC

A small set of utilities that allow conversion between the data storage formats of [DeepLabCut](https://github.com/AlexEMG/DeepLabCut) (DLC) and one of the DLT-based 3D tracking systems: either Ty Hedrick's [DigitizingTools](http://biomech.web.unc.edu/dltdv/) in MATLAB, or the Python-based [Argus](http://argus.web.unc.edu). These functions should allow you to use data previously digitized in a DLT system to create the files needed to train a DLC model, and to import DLC-tracked points back into a DLT 3D calibration to reconstruct 3D points. 

While DLC has 3D capabilities (using checkerboards), many field-based setups necessitate the ability to use a wand calibration (easywand or Argus). DLC can be used to auto-track the wand and/or subjects in each video (treated as separate 2D videos), then moved back to DLT for 3d reconstruction. 

Multi-camera setups that are not frame-synced (e.g. GoPros) must have offsets calculated (Argus), and adjusted for. These scripts account for those offset values.

As a bonus (i.e. because I needed it), I'm also including bbCrop.py to allow digitizing (labeling) of a bounding box (upperleft - 'ul', and bottom right - 'br') to produced individual images cropped to that bounding box. These images could then be trained and analyzed in DLC. Those output coordinates can then be put back into the full video resolution with cropped2full.py for full 2d coordinates, or processed with dlc2dlt.py to be brought back into a DLT system for 3D coordinates.

**NOTE**: As of 6 February, 2020, these "work" in so far as they produce files that look like they have the correct format without spitting out errors. They have NOT been tested in a complete workflow to make sure that everything matches up where it should. Please feel free to test, edit, contribute, suggest. Consider these a first draft!

Once they are well tested, I will include these functions directly in Argus, and I'm sure a similar set of MATLAB scripts will find their way into DLTdv8.

## Getting Started

Download the scripts. Put them somewhere handy. Call them on the command-line.  See below.

## Usage

For both functions, the flag `-flipy` will default to `True` which is necessary if your data are from Argus or DLTdv versions prior to 8.0. In those packages, the coordinate origin is in the lower left of the video, but the computer vision standard (used by DeepLabCut and by DLTdv8) is for the origin to be in the **upper** left. If you are using DLTdv8, just add `-flipy False` to the call.

### dlt2dlc

Many of us have lots of data already digitized in a DLT-calibrated environment. Those already digitized points can be used in place of "labeling" video in DeepLabCut. That's what dlt2dlc.py is for. It "essentially" replaces/parallels the labelling function in DLC.

```
python dlt2dlc.py --help
usage: dlt2dlc.py [-h] [-xy XY] [-vid VID] [-cnum CNUM] [-numcams NUMCAMS]
                  [-scorer SCORER] [-newpath NEWPATH] [-flipy FLIPY]
                  [-offset OFFSET]

convert argus to DLC labeled frames for training

optional arguments:
  -h, --help        show this help message and exit
  -xy XY            input path to xyzpts file
  -vid VID          input path to video file
  -cnum CNUM        enter 1-indexed camera number for extraction
  -numcams NUMCAMS  enter number of cameras
  -scorer SCORER    enter scorer name to match DLC project (default = DLT)
  -newpath NEWPATH  enter a path for saving, existing target folder will be
                    overwritten, should end with "labeled-data/<videoname>"
  -flipy FLIPY      flip y coordinates - necessar for Argus and DLTdv versions
                    1-7, set to False for DLTdv8
  -offset OFFSET    enter offset of chosen camera as integer
```

For example, 

```
python dlt2dlc.py -xy /path/to/xypts/file-xypts.csv -vid /path/to/xypts/video.mp4 -cnum 2 -numcams 3 -scorer sej -newpath /path/to/a/different/place/labeled-date/thisvideo -offset -21
```

will take the data and video from the second camera (with a -21 frame offset) in a three camera setup, and save the coordinates and images in `newpath`. Note that it will overwrite newpath if it exists. If `newpath` isn't given, it will make a `labeled-data/vidname/` directory at the same path as the video. You *should* then be able to take the `vidname` directory and move it into your DLC project folder (put it in labeled-data). You *may* then have to update the config.yaml file to get DLC to see these data (not tested). This will save **every* frame with something digitized in it, which can take a while and eat up a lot of space.

TODO: allow cropping, sub-selection of frames

### dlc2dlt

If you have some beautifully accurate 3d DLT calibrations, but are sick of manually digitizing each video, then train and use DLC to digitize your videos independently.  Once they are digitized, dlc2dlt will create the needed files to complete DLT reconstruction. It essentially allows you to use DLC to replace the clicking part of DLT.

```
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
```

for example, if you have a three camera DLT setup, and each camera has been tracked in DLC...

```
python dlc2dlt.py -dlctracks /pathtoDLCproectfolder/videos/cam1tracked.h5 /pathtoDLCproectfolder/videos/cam2tracked.h5 /pathtoDLCproectfolder/videos/cam3tracked.h5 -newpath /a/path/to/somewhere/else/trial01DLCtracked -offsets 0 -20 34
```
will make the standard DLT files (4 of them) at new path, named trial01DLCtracked-xypts.csv, trial01DLCtracked-xyzpts.csv, trial01DLCtracked-xyzres.csv, trial01DLCtracked-offsets.csv. The -xyzpts and -xyzres files will be empty, but they must be created to be able to load the data into DLTdv or Argus.

To get xyz pts, load the new -xypts.csv as data in DLTdv or Argus as if you digitized it there, load your DLT coefficients, camera profiles, check the data, and save. Note that both DLTdv and Argus have command-line functions (dlt_reconstruct) to get the 3d points without loading in the GUI.


## Authors

* **Brandon E. Jackson, Ph.D.** 

## References

If you use this code, for now, please cite the appropriate DeepLabCut and Argus or DLTdv papers.

## License

This project is licensed under the GNU Lesser General Public License v3.0; see the [LICENSE.md](LICENSE.md) file for details. Note that the software is provided "as is", without warranty of any kind, express or implied. If you use the code, please cite DeepLabCut and either DLTdv or Argus.

