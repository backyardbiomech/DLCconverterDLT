"""Renames video files, which often have non-unique names in DLT projects (cam1.MP4, cam2.MP4, cam3.MP4...),
to unique names based on the parent folder for easier inclusion in DeepLabCut projects where each video must be
uniquely named.

Takes some level of parent folder (e.g. the project folder), name matches, the concatenates folder names with '_'
finishing with passed video name.

For example:
Research Projects
|--20190603
   |--trial01
      |--cam1.MP4
      |--cam2.MP4
      |--cam3.MP4
   |--trial02
      |--cam1.MP4
      |--cam2.MP4
      |--cam3.MP4

should produce 6 new videos in the defined output directory (these are copies of the files, so large videos will take
lots of space!) - 20190603_trial01_cam1.MP4 - 20190603_trial01_cam2.MP4 - 20190603_trial01_cam3.MP4 -
20190603_trial02_cam1.MP4 - 20190603_trial02_cam2.MP4 - 20190603_trial02_cam3.MP4


Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 4 Feb 2020
"""

import argparse
from pathlib import Path
import shutil


def main(opath, pardir, vidlist, ext):
    if not vidlist:
        # search for all videos in parent
        vidlist = list(pardir.glob('**/*.'+ ext))
    #     # save paths to vidlist
    for file in vidlist:
        file = Path(file)
        # create the filename
        namepath = file.relative_to(pardir.parent)
        filename = str(namepath).replace('/', '_')
        oname = opath / filename
        shutil.copy(file, oname)
    print('Copied and renamed {} videos to {}'.format(len(vidlist), str(opath)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='rename videos based on folder structure')

    parser.add_argument('opath', help='full path to directory to put new videos')
    parser.add_argument('parent', help='full path to parent directory (will be first part of new vid name')
    parser.add_argument('-vid', default = None, nargs='+', help='OPTIONAL: input path(s) to specific video file(s), space separated, if omitted will find all videos in parent')
    parser.add_argument('-ext', default='MP4', help='extension to search for to find videos if specific file not passed')

    args = parser.parse_args()

    opath = Path(args.opath)
    pardir = Path(args.parent)
    vidlist = args.vid
    ext = args.ext
    if not opath.exists():
        # make a new dir for output
        opath.mkdir(parents=True)

    main(opath, pardir, vidlist, ext)