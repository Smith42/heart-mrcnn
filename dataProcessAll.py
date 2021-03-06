from __future__ import print_function

import numpy as np
import pyfits
import os
import sklearn
import h5py
from numpy import interp
from sklearn.metrics import roc_curve, roc_auc_score
import scipy, scipy.ndimage

# Import and preprocess data
# If the heart image stored dir has changed:
#   * Change the directory and regex of the heart images to import in importType.
#   * Change the number of images to import.

def importHeartData(calmFile, stressFile, resize):
    """
    Import heart data and extract the pixel array.
    Slice halfway along ind axis.
    Concatenate and return stress file and calm file.
    If resize == 1, interpolate data to fit (34,34) arr.
    """
    calmTmp = pyfits.open(calmFile)[0].data
    stressTmp = pyfits.open(stressFile)[0].data

    calmTmp = cropHeart(calmTmp)
    stressTmp = cropHeart(stressTmp)

    # Pad the 3d arrays with zeros so that they are all the same size
    zeroArr0 = np.zeros((34,34,34))
    zeroArr1 = np.zeros((34,34,34))

    if resize == 1:
        # Resize the 3D slices
        calmRatio = 34.0/np.amax(calmTmp.shape)
        stressRatio = 34.0/np.amax(stressTmp.shape)

        calm3d = scipy.ndimage.interpolation.zoom(calmTmp, (calmRatio))
        stress3d = scipy.ndimage.interpolation.zoom(stressTmp, (stressRatio))

        zeroArr0[:calm3d.shape[0],:calm3d.shape[1],:calm3d.shape[2]] = calm3d
        zeroArr1[:stress3d.shape[0],:stress3d.shape[1],:stress3d.shape[2]] = stress3d

    else:
        zeroArr0[:calm3d.shape[0],:calm3d.shape[1],:calm3d.shape[2]] = calm3d
        zeroArr1[:stress3d.shape[0],:stress3d.shape[1],:stress3d.shape[2]] = stress3d

    zeroArr0 = normalise(zeroArr0)
    zeroArr1 = normalise(zeroArr1)

    catOut = [zeroArr0, zeroArr1]
    return catOut

def importType(pptType, n):
    """
    Get stress and calm scans for n patients with pptType illness.
    Return joined array.
    """
    tmplst = []
    simsDir = "/data/jim/Heart/sims/"
    for i in np.arange(0,n):
        cwdStress = str(simsDir+"stress_"+pptType+"_%0.4d.fits") %i
        cwdCalm = str(simsDir+"rest_"+pptType+"_%0.4d.fits") %i
        # Get zoomed 3d arrays:
        xAx = importHeartData(cwdCalm, cwdStress, 1) # zoom = 1
        tmplst.append(xAx)

    dataFile = np.array(tmplst)
    #print(dataFile.shape)

    return dataFile

def cropHeart(inp):
    """
    Crop the heart so that all the padding is done away with.
    Output cropped heart.
    """
    # argwhere will give you the coordinates of every point above smallest
    true_points = np.argwhere(inp)
    # take the smallest points and use them as the top left of your crop
    top_left = true_points.min(axis=0)
    # take the largest points and use them as the bottom right of your crop
    bottom_right = true_points.max(axis=0)
    out = inp[top_left[0]:bottom_right[0]+1,  # plus 1 because slice isn't
          top_left[1]:bottom_right[1]+1,   # inclusive
          top_left[2]:bottom_right[2]+1]
    return out

def normalise(inData):
    """
    Normalise 3D array.
    """
    inDataAbs = np.fabs(inData)
    inDataMax = np.amax(inData)
    normalisedData = inDataAbs/inDataMax
    return normalisedData

if __name__ == "__main__":

    # Do data import
    normName = "healthy"
    normDat = importType(normName,1000) # Normal and abnormal data same number of ppts
    normDat = np.moveaxis(normDat,1,-1)

    isName = "ischaemia"
    isDat = importType(isName,1000)
    isDat = np.moveaxis(isDat,1,-1)

    inName = "infarction"
    inDat = importType(inName,1000)
    inDat = np.moveaxis(inDat,1,-1)

    miName = "mixed"
    miDat = importType(miName,1000)
    miDat = np.moveaxis(miDat,1,-1)

    arName = "artefact"
    arDat = importType(arName,1000)
    arDat = np.moveaxis(arDat,1,-1)

    data = np.concatenate([normDat, isDat, inDat, miDat, arDat])

    # Do labelling
    normLab = np.full(normDat.shape[0], 0)
    isLab = np.full(isDat.shape[0], 1)
    inLab = np.full(inDat.shape[0], 2)
    miLab = np.full(miDat.shape[0], 3)
    arLab = np.full(arDat.shape[0], 4)
    labels = np.concatenate([normLab, isLab, inLab, miLab, arLab])

    # Mutual shuffle
    shufData, shufLab = sklearn.utils.shuffle(data, labels, random_state=1)
    shufLabOH = np.eye(5)[shufLab.astype(int)] # One hot encode
    shufData = np.reshape(shufData,(-1,34,34,34,2))

    # Save data as HDF5 object:
    h5f = h5py.File("./data/allTest.h5", "w")
    h5f.create_dataset("inData", data=shufData)
    h5f.create_dataset("inLabels", data=shufLabOH)
    h5f.close()
