"""
Converts 3D calibration and instrinsic camera information from DLT (easywand or Argus) to opencv (Deeplabcut, anipose, etc).

Inputs:
coefs - the DLT coefficients file containing 11 DLT coefficietns per camera
prof - the camera profile containing camera intrinsic information (e.g. as created by Argus.caliibrate)

containing variables:
xyz - the camera position in calibration frame xyz space
T - the 4x4 trasnformation matrix for camera position and orientation
ypr - Yaw,Pitch,Roll angles in degrees (Maya compatible)
Uo - perceived image center along the camera width axis
Vo - perceived image center along the camera height axis
Z - distance from camera to image plane

Outputs:
Will save an anipose-style calibration.toml to the same directory as the dlt coefficients file

Example call:
python DLTcameraPosition.py -dlt /full/path/to/dlt-coefficients.csv -prof /full/path/to/camera-profile.txt

Based on code from Ty Hedrick, Ph.D., The University of North Carolina

Author: Brandon E. Jackson, Ph.D.
email: jacksonbe3@longwood.edu
Last edited: 2021-08-23

NOT COMPLETE OR TESTED
"""

import argparse
import pandas as pd
import numpy as np
import cv2
from pathlib import Path
import toml

def DLTcameraPosition(coefs):
    m1 = np.matrix([[coefs[0], coefs[1], coefs[2]],
                [coefs[4], coefs[5], coefs[6]],
                 [coefs[8], coefs[9], coefs[10]]])
    m2 = np.matrix([-coefs[3], -coefs[7], -1]).T

    xyz = np.linalg.inv(m1)*m2

    D = (1/(coefs[8]**2 + coefs[9]**2 + coefs[10]**2))**0.5

    Uo = (D**2) * (coefs[0] * coefs[8] + coefs[1] * coefs[9] + coefs[2] * coefs[10])
    Vo = (D**2) * (coefs[4] * coefs[8] + coefs[5] * coefs[9] + coefs[6] * coefs[10])

    du = (((Uo * coefs[8] - coefs[0])**2 + (Uo * coefs[9] - coefs[1])**2 + (Uo * coefs[10] - coefs[2])**2) * D**2)
    dv = (((Vo * coefs[8] - coefs[4])**2 + (Uo * coefs[9] - coefs[5])**2 + (Uo * coefs[10] - coefs[6])**2) * D**2)

    Z = -1 * np.mean([du, dv])

    T3 = D * np.matrix([
        [(Uo*coefs[8]-coefs[0])/du ,(Uo*coefs[9]-coefs[1])/du ,(Uo*coefs[10]-coefs[2])/du],
        [(Vo*coefs[8]-coefs[4])/dv ,(Vo*coefs[9]-coefs[5])/dv ,(Vo*coefs[10]-coefs[6])/dv],
        [coefs[8] , coefs[9], coefs[10]]
    ])

    rvecs = cv2.Rodrigues(T3)[0]

    dT3 = np.linalg.det(T3)

    if dT3 < 0:
        T3 = -1 * T3

    T = np.linalg.inv(T3)
    T = np.hstack([T, [[0], [0], [0]]])
    T = np.vstack([T, [xyz.item(0), xyz.item(1), xyz.item(2), 1]])

    # compute YPR from T3
    # Note that the axes of the DLT based transformation matrix are
    # rarely orthogonal, so these angles are only an approximation of the correct
    # transformation matrix

    alpha = np.arctan2(T.item((1,0)), T.item((0,0))) #yaw
    beta = np.arctan2(-T.item((2,0)), (T.item((2,1))**2 + T.item((2,2))**2)**0.5) #pitch
    gamma = np.arctan2(T.item((2,1)), T.item((2,2))) #roll

    # Check for orthongonal transforms by back-calculating one of the matrix elements
    if abs(np.cos(alpha) * np.cos(beta) - T.item((0,0))) > 1e-8:
        print('Warning - the transformation matrix represents transformation about')
        print('non-orthgonal axes and connot be represented as a roll, pitch, and yaw')
        print('series with 100% accuracy.')

    ypr=np.rad2deg(np.array([gamma,beta,alpha]))
    return xyz, T, ypr, Uo, Vo, Z, rvecs

def dlt2dlcCoefs(dltp, profp):
    #make paths into Paths
    dltp = Path(dltp)
    profp = Path(profp)

    dlt = pd.read_csv(dltp, header=None)
    prof = pd.read_csv(profp, header=None, delimiter=' ', index_col=0)
    numcams = len(prof)
    # in dltcoefs, treat columns as camera "names", not python indexing
    dlt.columns = list(range(1,numcams+1))

    # start building the calibration.toml
    cal = {}
    for cam in prof.index:
        xyz, T, ypr, Uo, Vo, Z, rvec = DLTcameraPosition(dlt[cam])
        camdict = {
            "name": str(cam),
            "size": [float(prof.loc[cam, 2]), float(prof.loc[cam,3])],
            "matrix": [[float(prof.loc[cam, 1]), 0.0, float(prof.loc[cam, 4])],
                       [0.0, float(prof.loc[cam,1]), float(prof.loc[cam,5])],
                       [0.0, 0.0, 1.0]],
            "distortions" : prof.loc[cam, [7, 8, 9, 10, 11]],
            "rotation": rvec.T.tolist()[0],
            "translation" : xyz.T.tolist()[0]
        }
        cal['cam_{}'.format(cam-1)]=camdict
    # not clear if metadata is important, and can't calculate "error" without original checkerboard pattern, so making somehting up for now
    # might be able to grab the reconstruction error from the wand calibration output
    cal["metadata"]= {"adjusted": False, "error": 0.1}
    # write toml
    ofile = dltp.parent / 'calibration.toml'
    print(cal)

    with open(str(ofile), "w") as f:
        toml.dump(cal, f)
    print("data written to ", ofile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='convert 3d calibration from DLT to opencv, or back')
    parser.add_argument('-dlt', help='path to dlt coefficients file')
    parser.add_argument('-prof', help='path to camera profile')
    parser.add_argument('-dlt2dlc', default=True, help='direction of conversion')

    args = parser.parse_args()

    if args.dlt2dlc == True:
        dlt2dlcCoefs(args.dlt, args.prof)