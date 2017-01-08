"""Some utility functions."""

# Part of the Segmentator library
# Copyright (C) 2016  Omer Faruk Gulban and Marian Schneider
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt


def sub2ind(array_shape, rows, cols):
    """Pixel to voxel mapping (similar to matlab's function)."""
    # return (rows*array_shape + cols)
    return (cols*array_shape + rows)


def Ima2VolHistMapping(xinput, yinput, binsArray):
    """Image to volume histogram mapping (kind of inverse histogram)."""
    dgtzData = np.digitize(xinput, binsArray)-1
    dgtzGra = np.digitize(yinput, binsArray)-1
    nrBins = len(binsArray)-1  # subtract 1 (more borders than containers)
    vox2pixMap = sub2ind(nrBins, dgtzData, dgtzGra)  # 1D
    return vox2pixMap


def VolHist2ImaMapping(imaSlc2volHistMap, volHistMask):
    """Volume histogram to image mapping for slices (uses np.ind1)."""
    imaSlcMask = np.zeros(imaSlc2volHistMap.flatten().shape)
    idxUnique = np.unique(volHistMask)
    for idx in idxUnique:
        linIndices = np.where(volHistMask.flatten() == idx)[0]
        # return logical array with length equal to nr of voxels
        voxMask = np.in1d(imaSlc2volHistMap.flatten(), linIndices)
        # reset mask and apply logical indexing
        imaSlcMask[voxMask] = idx
    imaSlcMask = imaSlcMask.reshape(imaSlc2volHistMap.shape)
    return imaSlcMask


def TruncateRange(data, percMin=0.25, percMax=99.75):
    """Truncate too low and too high values."""
    # adjust minimum
    percDataMin = np.percentile(data, percMin)
    data[data < percDataMin] = percDataMin
    # adjust maximum
    percDataMax = np.percentile(data, percMax)
    data[data > percDataMax] = percDataMax
    return data


def ScaleRange(data, scaleFactor=500, delta=0):
    """Scale values as a preprocessing step.

    Lower scaleFactors give faster interface (0-500 or 600 seems fast enough).
    Delta ensures that the max data points fall inside the last bin when this
    function is used with histograms.
    """
    scaleFactor = scaleFactor - delta
    data = data - data.min()
    return scaleFactor / data.max() * data


def Hist2D(ima, gra):
    """Prepare 2D histogram related variables.

    This function is modularized to be caleld from the terminal.
    """
    dataMin = np.round(ima.min())
    dataMax = np.round(ima.max())
    nrBins = int(dataMax - dataMin)
    binEdges = np.arange(dataMin, dataMax+1)
    counts, _, _, volHistH = plt.hist2d(ima, gra, bins=binEdges, cmap='Greys')
    return counts, volHistH, dataMin, dataMax, nrBins, binEdges
