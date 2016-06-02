#!/usr/bin/env python

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


from nibabel import load, save, Nifti1Image
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.widgets import Slider, Button, LassoSelector
from matplotlib import path
from sector_mask import sector_mask
from utils import Ima2VolHistMapping, VolHist2ImaMapping
from draggable import DraggableSector


#%%
"""Load Data"""
#
nii = load('/media/sf_D_DRIVE/Segmentator/ExampleNii/P06_T1w_divPD_IIHC_v16.nii')

#
"""Data Processing"""
orig = np.squeeze(nii.get_data())

# auto-scaling for faster interface (0-500 or 600 seems fine)
percDataMin = np.percentile(orig, 0.01)
orig[np.where(orig < percDataMin)] = percDataMin
orig = orig - orig.min()
dataMin = orig.min()
percDataMax = np.percentile(orig, 99.9)
orig[np.where(orig > percDataMax)] = percDataMax
orig = 500./orig.max() * orig
percDataMax = orig.max()

# gradient magnitude (using L2 norm of the vector)
ima = orig.copy()
gra = np.gradient(ima)
gra = np.sqrt(np.power(gra[0], 2) + np.power(gra[1], 2) + np.power(gra[2], 2))

# reshape ima (more intuitive for voxel-wise operations)
ima = np.ndarray.flatten(ima)
gra = np.ndarray.flatten(gra)

#%%
#
"""Plots"""
# Set up a colormap:
palette = plt.cm.Reds
palette.set_over('r', 1.0)
palette.set_under('w', 0)
palette.set_bad('m', 1.0)

# Plot 2D histogram
fig = plt.figure()
ax = fig.add_subplot(121)
nrBins = int(percDataMax - dataMin + 2)  # TODO: variable name fix
binVals = np.arange(dataMin, percDataMax)
_, xedges, yedges, _ = plt.hist2d(ima, gra,
                                  bins=binVals,
                                  norm=LogNorm(vmax=10000),
                                  cmap='Greys'
                                  )
ax.set_xlim(dataMin, percDataMax)
ax.set_ylim(0, percDataMax)
bottom = 0.30
plt.subplots_adjust(bottom=bottom)
plt.colorbar()
plt.xlabel("Intensity f(x)")
plt.ylabel("Gradient Magnitude f'(x)")
plt.title("2D Histogram")


# plot 3D ima by default
ax2 = fig.add_subplot(122)
slc = ax2.imshow(orig[:, :, int(orig.shape[2]/2)],
                 cmap=plt.cm.gray, vmin=ima.min(), vmax=ima.max(),
                 interpolation='none'
                 )
imaMask = np.ones(orig.shape[0:2])  # TODO: Magic numbers
ovl = ax2.imshow(imaMask,
                 cmap=palette, vmin=0.1,
                 interpolation='none',
                 alpha=0.5
                 )
# plt.subplots_adjust(left=0.25, bottom=0.25)
plt.axis('off')



#%%
#
"""Functions and Init"""
# define a image to volume histogram map
ima2volHistMap = Ima2VolHistMapping(xinput=ima, yinput=gra, binsArray=binVals)
invHistVolume = np.reshape(ima2volHistMap, orig.shape)

# initialise scliceNr
sliceNr = int(0.5*orig.shape[2])

# create first instance of sector mask
shape = (nrBins,nrBins)
centre = (0,0)
radius = 200
theta = (0,360)
sectorObj = sector_mask(shape, centre, radius, theta)

# draw sector mask for the first time
sectorFig, volHistMask = sectorObj.draw(ax, cmap='Reds', alpha=0.2, vmin=0.1,
                 interpolation='nearest',
                 origin='lower',
                 extent=[percDataMin, percDataMax, gra.min(), percDataMax])

# pass on some properties to the sector object
sectorObj.figure = ax.figure
sectorObj.axes = ax.axes
sectorObj.axes2 = ax2.axes
sectorObj.invHistVolume = invHistVolume
sectorObj.brainMaskFigHandle = ovl
sectorObj.sliceNr = sliceNr
sectorObj.nrOfBins = len(binVals)

# make sector draggable                 
drSectorObj = DraggableSector(sectorObj)
drSectorObj.volHistMask = volHistMask
drSectorObj.connect() 

# define what should happen if update is called
def updateHistBrowser(val): 
    # update slider for scaling log colorbar in 2D hist
    histVMax = np.power(10, sHistC.val)
    plt.clim(vmax=histVMax)

def updateBrainBrowser(val):
    global sliceNr
    # Scale slider value [0,1) to dimension index to allow variation in shape
    sliceNr = int(sSliceNr.val*orig.shape[2])
    slc.set_data(orig[:,:,sliceNr])
    # update slice number for draggable sector mask
    drSectorObj.sector.sliceNr = sliceNr
    # get current volHistMask
    volHistMask = drSectorObj.volHistMask
    # update the mask (2D mask is for fast visualization)
    imaMask = VolHist2ImaMapping(invHistVolume[:,:,sliceNr],volHistMask)
    ovl.set_data(imaMask)
    fig.canvas.draw_idle() # TODO:How to do properly? (massive speed up)
    
    
def updateTheta(val):
    # get current theta value from slider
    thetaVal = sTheta.val
    # update mouth of sector mask
    diff = thetaVal-drSectorObj.thetaInit
    drSectorObj.sector.mouthChange(diff)

    # update volHistMask    
    drSectorObj.pixMask = drSectorObj.sector.binaryMask()
    drSectorObj.sector.FigObj.set_data(drSectorObj.pixMask)
    # update imaMask
    drSectorObj.mask = VolHist2ImaMapping(
        drSectorObj.sector.invHistVolume[:,:,drSectorObj.sector.sliceNr],
        drSectorObj.pixMask)
    drSectorObj.sector.brainMaskFigHandle.set_data(drSectorObj.mask)                
    # draw to canvas
    drSectorObj.sector.figure.canvas.draw()
    drSectorObj.thetaInit = thetaVal

#%%
"""Sliders"""
# colorbar slider
axcolor = 'lightgoldenrodyellow'
axHistC = plt.axes([0.15, bottom-0.15, 0.25, 0.025], axisbg=axcolor)
sHistC = Slider(axHistC, 'Colorbar', 1, 5, valinit=3, valfmt='%0.1f')

# circle slider
aTheta = plt.axes([0.15, bottom-0.10, 0.25, 0.025], axisbg=axcolor)
thetaInit = 0 
drSectorObj.thetaInit = thetaInit
sTheta = Slider(aTheta, 'Theta', 0, 359.99, valinit=thetaInit, valfmt='%0.1f')

# ima browser slider
axSliceNr = plt.axes([0.6, bottom-0.15, 0.25, 0.025], axisbg=axcolor)
sSliceNr  = Slider(axSliceNr, 'Slice', 0, 0.999, valinit=0.5, valfmt='%0.3f')


#
"""Buttons"""
# cycle button
cycleax = plt.axes([0.6, bottom-0.275, 0.075, 0.075])
bCycle = Button(cycleax, 'Cycle\nView',
                color=axcolor, hovercolor='0.975')
cycleCount = 0

def cycleView(event):
    global orig, imaMask, cycleCount, invHistVolume
    cycleCount = (cycleCount+1) % 3
    orig = np.transpose(orig, (2, 0, 1))
    invHistVolume = np.transpose(invHistVolume, (2, 0, 1))  
     

# export button
exportax = plt.axes([0.8, bottom-0.275, 0.075, 0.075])
bExport  = Button(exportax, 'Export\nNifti',
                  color=axcolor, hovercolor='0.975')

def exportNifti(event):
    linIndices = np.arange(0, nrBins*nrBins)
    # get current volHistMask
    volHistMask = drSectorObj.volHistMask
    # get linear indices
    idxMask = linIndices[volHistMask.flatten()]
    # return logical array with length equal to nr of voxels
    voxMask = np.in1d(drSectorObj.sector.invHistVolume.flatten(), idxMask)
    # reset mask and apply logical indexing
    mask3D = np.zeros(drSectorObj.sector.invHistVolume.flatten().shape)
    mask3D[voxMask] = 1
    mask3D = mask3D.reshape(drSectorObj.sector.invHistVolume.shape)
    # save image, check whether nii or nii.gz
    new_image = Nifti1Image(mask3D, header=orig.get_header() ,affine=orig.get_affine())
    if orig.get_filename()[-4:] == '.nii':
        save(new_image, orig.get_filename()[:-4]+'_OUT.nii.gz')
    elif orig.get_filename()[-7:] == '.nii.gz':
        save(new_image, orig.get_filename()[:-7]+'_OUT.nii.gz')
        
        
# reset button
resetax = plt.axes([0.7, bottom-0.275, 0.075, 0.075])
bReset  = Button(resetax, 'Reset', color=axcolor, hovercolor='0.975')

def resetMask(event):
    global sliceNr
    # reset brain browser slider
    sSliceNr.reset()
    # Scale slider value [0,1) to dimension index to allow variation in shape
    sliceNr = int(sSliceNr.val*orig.shape[2])
    slc.set_data(orig[:,:,sliceNr])
    # update slice number for draggable sector mask
    drSectorObj.sector.sliceNr = sliceNr
    # revert to initial sector mask paramters 
    drSectorObj.sector.update(shape, centre, radius, theta)
    # update pix mask (histogram)  
    volHistMask = drSectorObj.sector.binaryMask()
    drSectorObj.sector.FigObj.set_data(volHistMask)
    # update brain mask
    imaMask = VolHist2ImaMapping(
        drSectorObj.sector.invHistVolume[:,:,sliceNr],
        volHistMask)
    drSectorObj.sector.brainMaskFigHandle.set_data(imaMask)   
             

#%%
"""Updates"""
sSliceNr.on_changed(updateBrainBrowser)
sHistC.on_changed(updateHistBrowser)
sTheta.on_changed(updateTheta)
bCycle.on_clicked(cycleView)  
bExport.on_clicked(exportNifti)
bReset.on_clicked(resetMask)

#%%
"""New stuff: Lasso (Experimental)"""
# Lasso button
lassoax = plt.axes([0.15, bottom-0.275, 0.1, 0.075])
bLasso  = Button(lassoax, 'Lasso\nON OFF', color=axcolor, hovercolor='0.975')

# define switch of Lasso option
switchCounter = 1 # TODO: use modulus 
def lassoSwitch(event):
    global lasso, switchCounter, OnSelectCounter
    lasso = []
    switchCounter += 1
    switchStatus = switchCounter%2
    print switchStatus
    if switchStatus == 0:
        # disable drag function of sector mask
        drSectorObj.disconnect()
        # enable lasso
        lasso = LassoSelector(ax, onselect)
    elif switchStatus == 1:
        OnSelectCounter = 0
        lasso = [] 
        # enable drag function of sector mask
        drSectorObj.connect() 

# Pixel coordinates
pix = np.arange(nrBins)
xv, yv = np.meshgrid(pix,pix)  
pix = np.vstack( (xv.flatten(), yv.flatten()) ).T

def updateArray(array, indices):
    lin = np.arange(array.size)
    newArray = array.flatten()
    newArray[lin[indices]] = 1
    return newArray.reshape(array.shape)

OnSelectCounter = 0
def onselect(verts):
    global volHistMask, pix, OnSelectCounter
    p = path.Path(verts)
    ind = p.contains_points(pix, radius=1.5)
    # update pix mask (histogram)
    # PROBLEM: it gets pix mask from dr every time (lasso from previous time gets lost )
    if OnSelectCounter == 0:
        volHistMask = drSectorObj.sector.binaryMask()
    OnSelectCounter +=1
    volHistMask = updateArray(volHistMask, ind)
    drSectorObj.sector.FigObj.set_data(volHistMask)    
    # update brain mask
    sliceNr = drSectorObj.sector.sliceNr
    imaMask = VolHist2ImaMapping(
        drSectorObj.sector.invHistVolume[:,:,sliceNr],
        volHistMask)
    drSectorObj.sector.brainMaskFigHandle.set_data(imaMask) 

    fig.canvas.draw_idle()

bLasso.on_clicked(lassoSwitch)

## does not work
#LassoSelector(ax, onselect)
## works
#lasso = LassoSelector(ax, onselect)

plt.show()
#plt.close()
