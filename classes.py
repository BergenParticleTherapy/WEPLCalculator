import numpy as np
from matplotlib import pyplot as plt
from scipy.ndimage.interpolation import rotate
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
from math import *
import matplotlib.patches as patches
import pydicom, os

class IndexTracker(object):
    def __init__(self, ax1, ax2, ax3, imageSeries, extStructFile, options, rotations):
        self.ax1 = ax1
        self.ax2 = ax2
        self.ax3 = ax3
        self.imageSeries = imageSeries
        self.options = options
        self.ind = 0
        self.rot = rotations[0]

        colors = ['r', 'g', 'b', 'y', 'c', 'm', 'orange', 'lightcoral',
                  'peachpuff', 'olive', 'gold', 'navy', 'sienna', 'tan', 'crimson',
                  'lime', 'goldenrod', 'moccasin', 'beige', 'tomato', 'mistyrose', 'darksalmon',
                  'navajowhite', 'darkorange', 'snow', 'teal', 'deeppink', 'orchid']

        self.imageSeries = imageSeries
        self.extStructFile = extStructFile
        self.structures = self.imageSeries.structures # Has been propagated earlier
        self.structureColor = {s:c for s,c in zip(self.structures,colors)}
        
        if self.extStructFile:
            self.UIDs = self.extStructFile.getUIDsFromStructures()
            self.imgList = self.zposList = sorted(self.extStructFile.getZposFromStructures())
            self.imageSeries.loadImageFromPosZ(self.zposList[self.ind])
        else:
            self.imgList = self.UIDs = sorted(self.imageSeries.getUIDsFromStructures())
            self.imageSeries.loadImageFromUID(self.UIDs[self.ind])

        self.imageSeries.resetImage()   
        self.ax1.set_title(imageSeries.amplitude)

        self.im1 = self.ax1.imshow(self.imageSeries.image, cmap="gray")
        self.im2 = self.ax2.imshow(self.imageSeries.image, vmin=0, vmax=2, cmap="gray")
        self.im3 = self.ax3.imshow(self.imageSeries.image, vmin=0, vmax=300)

        
        ax2_divider = make_axes_locatable(self.ax2)
        cax2 = ax2_divider.append_axes("right", size="7%", pad="2%")
        self.cb2 = plt.colorbar(self.im2, cax=cax2)
        ax3_divider = make_axes_locatable(self.ax3)
        cax3 = ax3_divider.append_axes("right", size="7%", pad="2%")
        self.cb3 = plt.colorbar(self.im3, cax=cax3)
        

        self.update()
    
    def onscroll(self, event):
        if event.button == 'up':
            self.ind = (self.ind + 1)
            if self.ind >= len(self.imgList):
                self.ind = 0
        else:
            self.ind = (self.ind - 1)
            if self.ind < 0:
                self.ind = len(self.imgList) - 1
        self.update()

    def update(self):
        if self.extStructFile:
            self.UIDs = self.extStructFile.getUIDsFromStructures()
            self.imgList = self.zposList = sorted(self.extStructFile.getZposFromStructures())
            self.imageSeries.loadImageFromPosZ(self.zposList[self.ind])
        else:
            self.imgList = self.UIDs = sorted(self.imageSeries.getUIDsFromStructures())
            self.imageSeries.loadImageFromUID(self.UIDs[self.ind])
            
        self.imageSeries.resetImage()
        self.imageSeries.rotateImage(self.rot)
        self.imageSeries.recalculateContourBounds()        
        self.imageSeries.convertImageToRSP()
        self.imageSeries.convertImageToWEPL()
        self.imageSeries.rotateImage(-self.rot)

        self.im1.set_data(self.imageSeries.image)
        self.im2.set_data(self.imageSeries.imageRSP)
        self.im3.set_data(self.imageSeries.imageWEPL)

        
        
        self.ax1.set_ylabel('slice %s; z = %.1f' % (self.ind, self.imageSeries.zpos))

        self.ax1.lines = []
        rot = 0

        for structure in self.structures:
            self.imageSeries.structure = structure
            #try:
                # self.imageSeries.dicomRotation = self.rot
            #self.imageSeries.loadStructures()
            contours = self.imageSeries.getStructuresInImageCoordinates()

            #except:
                #continue

            first = True
            for contourX, contourY in zip(*contours):
                labelText = first and structure or None
                self.ax1.plot(contourX, contourY, color=self.structureColor[structure], label=labelText)
                first = False
                
        plt.legend()
        self.im1.axes.figure.canvas.draw()
        self.im2.axes.figure.canvas.draw()
        self.im3.axes.figure.canvas.draw()

        self.lines = list()
        self.ax1.set_title('Hounsfield Units')
        self.ax2.set_title('Relative Stopping Power')
        self.ax3.set_title(f'Water Equivalent Path Length (beam angle = {self.rot}°)')
"""
        self.X = X
        self.slices, cols, rows = X.shape
        self.ind = self.slices//2
        self.ind = 96
        
        self.im = self.ax1.imshow(self.X[self.ind, :, :], cmap="gray")

        self.update()
"""

class Line:
    """Used to aid in the pixels in structure calculation."""
    
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = x0, y0
        self.x1, self.y1 = x1, y1        
        
        if (y1 == y0):  self.dxdy = 0
        else:           self.dxdy = (x1 - x0) / (y1 - y0)
        
        if (x1 == x0):  self.dydx = 1e5
        else:           self.dydx = (y1 - y0) / (x1 - x0)

    def findIntercept(self, x=None, y=None):
        if x:
            if self.x0 < x <= self.x1:
                return (x-self.x0) * self.dydx + self.y0
            elif self.x1 < x <= self.x0:
                return (x-self.x0) * self.dydx + self.y0
    
        elif y:
            if self.y0 < y <= self.y1:
                return (y-self.y0)* self.dxdy + self.x0
            elif self.y1 < y <= self.y0:
                return (y-self.y0) * self.dxdy + self.x0
            
        return None

class LinearContour:
    """Calculate which pixels are contained in structures."""
    
    def __init__(self, dicomTranslation, pixelSpacing):
        self.lines = list()
        self.dicomTranslation = dicomTranslation
        self.pixelSpacing = pixelSpacing
        self.xmin = self.ymin = self.xmax = self.ymax = None

    def addLines(self, listOfPoints):
        lastPoint = listOfPoints[-1]
        self.xmin = self.xmax = lastPoint[0]
        self.ymin = self.ymax = lastPoint[1]
        
        for point in listOfPoints:
            self.xmin = min(self.xmin, point[0])
            self.ymin = min(self.ymin, point[1])
            self.xmax = max(self.xmax, point[0])
            self.ymax = max(self.ymax, point[1])
            
            self.lines.append(Line(*lastPoint, *point))
            lastPoint = point

    def getInterceptingLines(self, x=None, y=None):
        interceptPoints = []
        for line in self.lines:
            intercept = line.findIntercept(x,y)
            if intercept:
                interceptPoints.append(intercept)

        return interceptPoints   

    def findPixelInsideContourColumn(self, x, sh):
        column = np.zeros(sh[0])
        ray = self.getInterceptingLines(x, None)

        yRangesInsideContour = []
        for k in range(int((len(ray)+1)/2)):
            yRangesInsideContour.append([int(ray[2*k]), int(ray[2*k+1]+1)])
        
        for yFrom, yTo in yRangesInsideContour:
            ymin, ymax = sorted([yFrom, yTo])
            column[ymin:ymax] = True

        return column
    
    def getListOfPixelsInContour(self, image):
        sh = np.shape(image)
        contourMap = np.zeros(sh, dtype="bool")
        for x in range(int(self.xmin), int(self.xmax+1)):
            contourMap[:,x] = self.findPixelInsideContourColumn(x, sh)
            
        return contourMap

class Series:
    """Load DS and RS images from DICOM folder.

        Load images, structures and do various analyses."""
    
    def __init__(self, path = None, zpos = None, translation = None, rs = None, options = None):
        self.path = path
        self.zpos = zpos
        self.zposLUT = dict()
        self.structures = list()
        self.translation = translation
        self.dicomTranslation = None
        self.dicomRotation = 0
        #if path:
            #self.amplitude = # " ".join(path.split(" ")[-2:])
        #else:

        self.amplitude = None
        self.rs = None
        self.ds = None
        self.extStructFile = None
        self.image = None
        self.imageWEPL = None
        self.imageRSP = None
        self.zlim = []
        self.contourWEPL = list()
        self.pixelSpacing = None
        self.imageUID = None
        self.xbounds = [0,0]
        self.ybounds = [0,0]
        self.contours = dict()
        self.xminRot = self.yminRot = 1e5
        self.xmaxRot = self.ymaxRot = -1e5
        self.options = options

        if rs:
            self.rs = pydicom.dcmread(rs)

    def loadImages(self, load_rs):
        self.fDS, fRS = list(), list()
        for (dirpath, dirnames, filenames) in os.walk(self.path):
            self.fDS += [os.path.join(dirpath, file) for file in filenames if "CT" in file]
            fRS += [os.path.join(dirpath, file) for file in filenames if "RS" in file]

        if load_rs:
            self.rs = pydicom.dcmread(fRS[0])
        if self.zpos:
            self.loadImageFromPosZ()

        self.makeImageIndex()

    def getAllDatesAndSeriesDescription(self):
        names = dict()
        for dsFile in self.fDS:
            try:
                ds = pydicom.dcmread(dsFile, stop_before_pixels=True)
                name = f"{ds.SeriesDescription} ({ds.StudyDate})"
                if not name in names.keys():
                    names[name] = len(self.fDS)
                break
            except:
                continue
            
        return names

    def makeImageIndex(self):
        self.zposLUT = dict()
        
        for fDS in self.fDS:
            ds = pydicom.dcmread(fDS, stop_before_pixels=True)
            zpos = ds.ImagePositionPatient[2] + self.translation[2]
            self.zposLUT[zpos] = fDS
            if not self.amplitude:
                self.amplitude = ds.SeriesDescription
    
    def findImageIndex(self, zpos=None):
        if zpos == None:
            zpos = self.zpos

        if not self.zlim:
            first = pydicom.dcmread(self.fDS[0], stop_before_pixels=True)
            last = pydicom.dcmread(self.fDS[-1], stop_before_pixels=True)

            zlim = [k.ImagePositionPatient[2] + self.translation[2] for k in [first,last]]        
            deltaz = copysign(first.SliceThickness, zlim[1] - zlim[0])

            self.zlim = zlim
            self.deltaz = deltaz
            self.sliceThickness = first.SliceThickness
            
        return int((zpos - self.zlim[0])/self.deltaz + 0.5)

    def setUIDFromZ(self, zpos):
        idx = self.findImageIndex(zpos)
        self.ds = pydicom.dcmread(self.fDS[idx], stop_before_pixels=True)
        self.pixelSpacing = float(self.ds.PixelSpacing[0])
        self.dicomTranslation = [float(k) for k in self.ds.ImagePositionPatient]
        self.imageUID = self.ds.SOPInstanceUID

    def loadImageFromUID(self, UID):
        UIDidxInFDS = 0
        for idx,k in enumerate(self.fDS):
            if UID in k:
                UIDidxInFDS = idx

        assert UIDidxInFDS
        
        self.ds = pydicom.dcmread(self.fDS[UIDidxInFDS])
        assert self.ds.SOPInstanceUID == UID

        self.zpos = self.ds.ImagePositionPatient[2] + self.translation[2]
        self.pixelSpacing = float(self.ds.PixelSpacing[0])
        self.dicomTranslation = [float(k) for k in self.ds.ImagePositionPatient]
        self.imageUID = self.ds.SOPInstanceUID
        self.resetImage()
        
    def loadImageFromPosZ(self, zpos=None):
        self.zpos = zpos

        if not zpos in self.zposLUT:
            if not self.zlim:
                first = pydicom.dcmread(self.fDS[0], stop_before_pixels=True)
                last = pydicom.dcmread(self.fDS[-1], stop_before_pixels=True)

                zlim = [k.ImagePositionPatient[2] + self.translation[2] for k in [first,last]]        
                deltaz = copysign(first.SliceThickness, zlim[1] - zlim[0])

                self.zlim = zlim
                self.deltaz = deltaz
                self.sliceThickness = first.SliceThickness

            idx = self.findImageIndex(self.zpos)
            
            self.ds = pydicom.dcmread(self.fDS[idx])
        else:
            self.ds = pydicom.dcmread(self.zposLUT[zpos])
            self.sliceThickness = self.ds.SliceThickness
        
        # assert self.ds.ImagePositionPatient[2]+self.translation[2] - self.zpos <= self.sliceThickness/2
        
        self.pixelSpacing = float(self.ds.PixelSpacing[0])
        self.dicomTranslation = [float(k) for k in self.ds.ImagePositionPatient]
        self.imageUID = self.ds.SOPInstanceUID
        self.resetImage()

    def getUIDsFromStructures(self):
        contourIdxList = list()
        imageUIDSet = set()
        
        for idx, seq in enumerate(self.rs.StructureSetROISequence):
            if seq.ROIName in self.structures:
                contourIdxList.append(idx)

        for contourIdx in contourIdxList:
            for idx, seq in enumerate(self.rs.ROIContourSequence[contourIdx].ContourSequence):
                imageUIDSet.add(seq.ContourImageSequence[0].ReferencedSOPInstanceUID)

        return sorted(imageUIDSet)

    def getZposFromStructures(self):
        contourIdxList = list()
        posZset = set()
        
        for idx, seq in enumerate(self.rs.StructureSetROISequence):
            if seq.ROIName in self.structures:
                contourIdxList.append(idx)

        for contourIdx in contourIdxList:
            for idx, seq in enumerate(self.rs.ROIContourSequence[contourIdx].ContourSequence):
                posZset.add(float(seq.ContourData[2]))

        return posZset

    def loadStructureNames(self, progress = None):
        structureDict = dict()
        for seq in self.rs.StructureSetROISequence:
            structureDict[seq.ROINumber] = seq.ROIName

        self.listOfStructures = structureDict.values()
        self.structureDict = { k:v for k,v in structureDict.items() } # { Number : Name }

    def loadStructures(self, progress = None):
        for structure in self.structures:
            self.contours[structure] = list()

        #selectedROINumbers = [ k for k,v in self.structureDict.items() if v in self.structures ]
        selectedROINumbers = [ k for k,v in self.structureDict.items() if v in self.structures ]
        
        for seq in self.rs.ROIContourSequence:
            if not seq.ReferencedROINumber in selectedROINumbers:
                continue
            
            if not 'ContourSequence' in seq:
                continue
            
            if progress:
                progress.step(1)
                progress.update_idletasks()
            
            for contour in seq.ContourSequence:
                contourReshape = np.reshape(contour.ContourData, (len(contour.ContourData)//3, 3))
                self.contours[self.structureDict[seq.ReferencedROINumber]].append(contourReshape)

    def loadStructuresFromExternalStructureFile(self, extStructFile, progress = None):
        self.extStructFile = extStructFile
        self.extStructFile.loadStructures(progress)
        self.contours = self.extStructFile.contours
        
    def getStructuresInImageCoordinates(self):
        X, Y = list(), list()
        x0,y0 = [k/2 for k in np.shape(self.ds.pixel_array)]
        ps = self.pixelSpacing

        for structure in self.structures:
            for contour in self.contours[structure]:
                if abs(contour[0,2] - self.zpos) > 0.1:
                    continue

                x = (contour[:,0] - self.dicomTranslation[0] - self.translation[0]) / ps
                y = (contour[:,1] - self.dicomTranslation[1] - self.translation[1]) / ps
                
                if self.dicomRotation:
                    theta = -self.dicomRotation * 3.14159265 / 180
                    x -= x0; y -= y0
                    x,y = x * cos(theta) - y * sin(theta), x * sin(theta) + y * cos(theta)
                    x += x0; y += y0

                x -= self.xbounds[0]

                X.append(x); Y.append(y)

        print(np.shape(X[0]))
        if self.options.structureNumberVar.get() == 1 or len(np.shape(X)) == 2:
            return X[0], Y[0]
        else:
            print("LOOP B")
            print(np.shape(X[0][0]))
            return X[0][self.options.structureNumberVar.get()], Y[0][self.options.structureNumberVar.get()]

    def recalculateContourBounds(self):
        X, Y = self.getStructuresInImageCoordinates()


        if len(np.shape(X)) == 1:
            self.xminRot = min(self.xminRot, np.min(X))
            self.xmaxRot = max(self.xmaxRot, np.max(X))
            self.yminRot = min(self.yminRot, np.min(Y))
            self.ymaxRot = max(self.ymaxRot, np.max(Y))
        else:
            for eachX in X:
                self.xminRot = min(self.xminRot, np.min(eachX))
                self.xmaxRot = max(self.xmaxRot, np.max(eachX))
            for eachY in Y:
                self.yminRot = min(self.yminRot, np.min(eachY))
                self.ymaxRot = max(self.ymaxRot, np.max(eachY))

    def convertImageToRSP(self):
        """HU - RSP calibration

            Schneider et al., PMB 41(1) (1996)."""
        
        fHigh = lambda x: 1.06037 + 0.00046761*x
        fLow  = lambda x: 1.02365 + 0.00100547*x
        
        threshold = self.image >= 200

        self.imageRSP = np.where(threshold, fHigh(self.image), 0) \
                        + np.where(~threshold, fLow(self.image), 0)
        
        return self.imageRSP

    def resetImage(self, reloadImage = True):
        self.xbounds = [0,0]
        self.ybounds = [0,0]
        self.xminRot = self.yminRot = 1e5
        self.xmaxRot = self.ymaxRot = -1e5
        self.dicomRotation = 0
        if reloadImage:
            self.image = np.array(self.ds.pixel_array, dtype='int')
            self.image += int(self.ds.RescaleIntercept)        
            self.imageWEPL = self.imageRSP = None

    def rotateImage(self,angle):
        self.image = rotate(self.image, angle=angle, reshape=False, cval=-1000)
        self.dicomRotation = angle
        
    def reduceImageSize(self, pad):
        self.xbounds = [int(self.xminRot - pad), int(self.xmaxRot + pad)]
        self.ybounds = [0,int(self.ymaxRot + pad)]

        self.image = self.image[self.ybounds[0]:self.ybounds[1],
                                self.xbounds[0]:self.xbounds[1]]

    def convertImageToWEPL(self):
        shRSP = np.shape(self.imageRSP)
        self.imageWEPL = np.zeros(shRSP)
        for y in range(shRSP[0]):
            self.imageWEPL[y,:] = self.imageRSP[y,:] * self.pixelSpacing
            if y > 0: self.imageWEPL[y,:] += self.imageWEPL[y-1,:]

        return self.imageWEPL

    def createWEPLcurve(self):
        for contourX, contourY in zip(*self.getStructuresInImageCoordinates()):
            for xi, yi in zip(contourX, contourY):
                self.contourWEPL.append(self.imageWEPL[int(yi), int(xi)])

        return self.contourWEPL

    def getImageDate(self):
        return self.ds[0x8,0x20].value            
