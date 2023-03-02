"""
Much of the following code is copied from the argus software package. 
More details are available at https://argus.web.unc.edu/ and https://github.com/kilmoretrout/argus_gui

If you use this code, please cite the argus paper, which can be found at https://journals.biologists.com/bio/article/5/9/1334/1215/3D-for-the-people-multi-camera-motion-capture-in
"""
import numpy as np
import pandas as pd


def DLTcameraPosition(coefs):
    m1 = np.matrix([[coefs[0], coefs[1], coefs[2]],
                [coefs[4], coefs[5], coefs[6]],
                 [coefs[8], coefs[9], coefs[10]]])
    m2 = np.matrix([-1*coefs[3], -1*coefs[7], -1]).T

    xyz = np.linalg.inv(m1)*m2

    D = (1/(coefs[8]**2 + coefs[9]**2 + coefs[10]**2))**0.5

    Uo = (D**2) * (coefs[0] * coefs[8] + coefs[1] * coefs[9] + coefs[2] * coefs[10])
    Vo = (D**2) * (coefs[4] * coefs[8] + coefs[5] * coefs[9] + coefs[6] * coefs[10])

    du = (((Uo * coefs[8] - coefs[0])**2 + (Uo * coefs[9] - coefs[1])**2 + (Uo * coefs[10] - coefs[2])**2) * D**2)**0.5
    dv = (((Vo * coefs[8] - coefs[4])**2 + (Uo * coefs[9] - coefs[5])**2 + (Uo * coefs[10] - coefs[6])**2) * D**2)**0.5

    Z = -1 * np.mean([du, dv])

    T3 = D * np.matrix([
        [(Uo*coefs[8]-coefs[0])/du ,(Uo*coefs[9]-coefs[1])/du ,(Uo*coefs[10]-coefs[2])/du],
        [(Vo*coefs[8]-coefs[4])/dv ,(Vo*coefs[9]-coefs[5])/dv ,(Vo*coefs[10]-coefs[6])/dv],
        [coefs[8] , coefs[9], coefs[10]]
    ])

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
    return xyz, T, ypr, Uo, Vo, Z

def cFlip(camdlt, height):
    m = np.hstack([np.identity(3), np.zeros((3,1))])
    #decompose original DLT
    xyz, T, ypr, Uo, Vo, Z = DLTcameraPosition(camdlt)
    # instrinsics
    K = np.vstack([np.array([Z, 0, Uo]),
                    np.array([0, Z, Vo - height]),
                    np.array([0, 0, 1])
    ])
    # extrinsics
    R = T[0:3, 0:3]
    tv = np.matmul(T[3, 0:3], R)

    # camera rotations + translation as a 4x4 transform matrix
    P1 = np.hstack([R.T, tv.T])
    P1e = np.vstack([P1, np.array([0, 0, 0, 1])])
    coefsraw = np.matmul(np.matmul(K, m), P1e)
    coefs = np.reshape(coefsraw, (12,1))
    out = coefs[0:-1]/coefs[-1]
    out[0:3] = out[0:3]*-1
    out[7:11] = out[7:11]*-1
    return out.T


def dlt_invert(dlt, heights):
    """
    inverts implicit vertical coordinate to switch from old lower left to upper left origin
    """
    invcoefs = dlt.copy() * 0
    # for each camera (row) in dlt
    for c in range(dlt.shape[0]):
        invcoefs[c,:] = cFlip(dlt[c,:], heights[c])

def load_camera(filename):
    if filename:
        camera_profile = np.loadtxt(filename)
        # Pinhole distortion
        if camera_profile.shape[1] == 12:
            # Format the camera profile to how SBA expects it
            # i.e. take out camera number column, image width and height, then add in skew.
            camera_profile = np.delete(camera_profile, [0, 2, 3, 6], axis=1)
            return camera_profile

# undistort using OpenCV
"""
Parameters:
    - pts: Nx2 array of pixel coordinates
    - prof: either an array of pinhole distortion coefficients or a Omnidirectional distortion object from Argus
Returns:
    - Nx2 array of undistorted pixel coordinates
"""


def undistort_pts(pts, prof):
    import cv2
    if (type(prof) == list) or (type(prof) == np.ndarray):
        prof = np.array(prof)

        # try block to discern whether or not we are using the omnidirectional model
        # define the camera matrix
        K = np.asarray([[prof[0], 0., prof[1]],
                        [0., prof[0], prof[2]],
                        [0., 0., 1.]])
        src = np.zeros((1, pts.shape[0], 2), dtype=np.float32)
        src[0] = pts
        ret = cv2.undistortPoints(src, K, prof[-5:], P=K)
        return ret[0]

    else:
        # return prof.undistort_points(pts.T).T # broken due to numpy 1d transpose no-op
        return prof.undistort_points(pts.reshape((-1, 1))).T

def uv_to_xyz(pts, dlt, prof=None):
    """
    takes uv coordinates for a single point (ncols = ncams *2) and dlt array
    returns xyz coordinates for that point
    prof is a camera profile array to undistort - undistortion ignored if None
    """

    xyzs = np.zeros((len(pts), 3))
    # for each frame
    for i in range(len(pts)):
        uvs = list()
        # for each uv pair
        for j in range(int(len(pts[i]) / 2)):
            # do we have a NaN pair?
            if not True in np.isnan(pts[i, 2 * j:2 * (j + 1)]):
                # if not append the undistorted point and its camera number to the list
                if prof is None:
                    uvs.append([pts[i, 2 * j:2 * (j + 1)], j])
                else:
                    uvs.append([undistort_pts(pts[i, 2 * j:2 * (j + 1)], prof[j])[0], j])

        if len(uvs) > 1:
            # if we have at least 2 uv coordinates, setup the linear system
            A = np.zeros((2 * len(uvs), 3))

            for k in range(len(uvs)):
                A[2*k] = np.asarray([uvs[k][0][0] * dlt[uvs[k][1]][8] - dlt[uvs[k][1]][0],
                                   uvs[k][0][0] * dlt[uvs[k][1]][9] - dlt[uvs[k][1]][1],
                                   uvs[k][0][0] * dlt[uvs[k][1]][10] - dlt[uvs[k][1]][2]])
                A[2*k + 1] = np.asarray([uvs[k][0][1] * dlt[uvs[k][1]][8] - dlt[uvs[k][1]][4],
                                       uvs[k][0][1] * dlt[uvs[k][1]][9] - dlt[uvs[k][1]][5],
                                       uvs[k][0][1] * dlt[uvs[k][1]][10] - dlt[uvs[k][1]][6]])

            B = np.zeros((2 * len(uvs), 1))
            for k in range(len(uvs)):
                B[2*k] = dlt[uvs[k][1]][3] - uvs[k][0][0]
                B[2*k + 1] = dlt[uvs[k][1]][7] - uvs[k][0][1]

            # solve it
            xyz = np.linalg.lstsq(A, B, rcond=-1)[0]
            # place in the proper frame
            xyzs[i] = xyz[:, 0]

    # replace everything else with NaNs
    xyzs[xyzs == 0] = np.nan
    return xyzs

# like the above function but for single xyz value
def reconstruct_uv(L, xyz):
    # u = (np.dot(L[:3].T, xyz) + L[3]) / (np.dot(L[-3:].T, xyz) + 1.)
    # v = (np.dot(L[4:7].T, xyz) + L[7]) / (np.dot(L[-3:].T, xyz) + 1.)
    u = (np.dot(L[:3], xyz) + L[3]) / (np.dot(L[-3:], xyz) + 1.)
    v = (np.dot(L[4:7], xyz) + L[7]) / (np.dot(L[-3:], xyz) + 1.)
    return np.array([u, v])

def get_repo_errors(xyzs, pts, prof, dlt):
    errorss = list()
    # how many tracks, for each track
    ncams = len(dlt)
    for k in range(int(xyzs.shape[1] / 3)):
        xyz = xyzs[:, 3 * k:3 * (k + 1)]
        uv = pts[:, k * (2 * ncams):(k + 1) * (2 * ncams)]
        errors = np.zeros(xyz.shape[0])

        twos = list()
        s = 0

        # for each point in track
        for j in range(xyz.shape[0]):
            if not True in np.isnan(xyz[j]):
                toSum = list()
                # for each camera
                for i in range(int(uv.shape[1] / 2)):
                    if not np.isnan(uv[j, i * 2]):
                        if prof is not None:
                            ob = undistort_pts(np.array([uv[j, i * 2:(i + 1) * 2]]), prof[i])[0]
                        else:
                            ob = np.array([uv[j, i * 2:(i + 1) * 2]])[0]
                        re = reconstruct_uv(dlt[i], xyz[j])

                        toSum.append(((ob[0] - re[0]) ** 2 + (ob[1] - re[1]) ** 2))
                # sum the sums of square diffs across cameras
                epsilon = sum(toSum)
                errors[j] = np.sqrt(epsilon / float(len(toSum) * 2 - 3))
                if len(toSum) == 2:
                    twos.append(j)
                    s += errors[j]
                if errors[j] == np.nan or errors[j] == 0:
                    print('Somethings wrong!', uv[j], xyz[j])
        # rmse error from two cameras unreliable, replace with the average rmse over all two camera situations
        # if len(twos) > 1:
        #     s = s / float(len(twos))
        #     errors[twos] = s
        errorss.append(errors)
    ret = np.asarray(errorss)
    ret[ret == 0] = np.nan
    return ret

def triangulate(xypath, dltpath, profpath=None, flipy = False, heights = [688, 688]):
    """
    This function is specific to the DLTconvertDLC repository.
    It provides a function to automate triangulation of xypts files from either DLC conversion or manual digitizing. 

    Parameters
    ----------
    xypath: string
        Full path to xypts.csv file
    dltpath: string
        Full path to the dlt coefficients file (.csv) generated by Argus Wand or DLTdv
    profpath: string
        Full path to the camera profile file (.txt) generated from Argus Calibrate. If 'None', no undistortion is performed.
    flipy: boolean
        Flips y-coordinates. 'False' if dlt coefficients were created with DLTdv8, true for dlt coefficients from Argus or from DLTdv < 7.
    heights: list
        One entry per camera, the vertical resolution. Important for flipping y coordinates. 
    Outputs
    -------
    dataf1: Pandas dataframe of xyzpts
    dataf2: Pandas dataframe of reconstruction residuals
    dataf1 and dataf2 are saved as _xyzpts.csv and _res.csv files, respectively, with the same file name stem as the file entered for xypath
    """
    
    filename = str(xypath).split('xypts')[0]
    # get track names
    track_csv = open(xypath)
    header = track_csv.readline()
    track_csv.close()
    new_tracks = []
    header = header.split(',')
    for st in header:
        if st.rsplit('_', 3)[0] not in new_tracks:
            new_tracks.append(st.rsplit('_', 3)[0])

    # load files
    pts = pd.read_csv(xypath, index_col = False).values
    ncams = int(pts.shape[1]/(2*len(new_tracks)))

    DLTCoefficients = pd.read_csv(dltpath, index_col = False, header = None).values.T
    if flipy:
        for c in range(ncams):
            DLTCoefficients[c, :] = cFlip(DLTCoefficients[c, :], heights[c])
    if profpath is not None:
        camera_profile = load_camera(profpath)
    else:
        camera_profile = None
    

    # make a data frame for the xyz coordinates for all tracks and all frames
    xyzss = list()
    for j in range(int(pts.shape[1] / (2 * ncams))):
        if flipy:
            flippts = pts[:, j * 2 * ncams:(j + 1) * 2 * ncams].copy()
            flippts[:, 1] = heights[0] - flippts[:, 1]
            flippts[:, 3] = heights[1] - flippts[:, 3]
            xyzs = uv_to_xyz(flippts, DLTCoefficients, prof=camera_profile)
        else:
            xyzs = uv_to_xyz(pts[:, j * 2 * ncams:(j + 1) * 2 * ncams], DLTCoefficients, prof=camera_profile)
        xyzss.append(xyzs)

    xyzss = np.asarray(xyzss)
    _ = xyzss[0]
    for k in range(1, len(xyzss)):
        _ = np.hstack((_, xyzss[k]))

    xyz_cols = list()
    # sTracks = sorted(new_tracks)
    for k in range(len(new_tracks)):
        xyz_cols.append(new_tracks[k] + '_X')
        xyz_cols.append(new_tracks[k] + '_Y')
        xyz_cols.append(new_tracks[k] + '_Z')
    dataf1 = pd.DataFrame(_, columns=xyz_cols)
    # write to CSV
    dataf1.to_csv(filename + 'xyzpts.csv', index=False, na_rep='NaN')
    # get reprojection errors for all 3d points and make a data frame for it
    repoErrs = get_repo_errors(_, pts, camera_profile, DLTCoefficients).T
    # cols = sorted(new_trac)
    dataf2 = pd.DataFrame(repoErrs, columns=new_tracks)
    dataf2.to_csv(filename + 'xyzres.csv', index=False, na_rep='NaN')
    return dataf1, dataf2