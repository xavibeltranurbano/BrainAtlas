import gc
import os
import itk # itk-elastix
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt



from utils import Utils
from registration import Registration


class Atlas:
    util = Utils()


    def __init__(self, fixedImagePath,  movingImagePaths, paramterFolder):
        self.fixedImagePath = fixedImagePath
        self.movingImagePaths = movingImagePaths
        self.labelPathsToPropagate = self.getAllRelativeLabelPaths()
        self.paramterFolder = paramterFolder
        self.numberOfLabels = 3

    ######################################################
    ### Registration #####################################
    ######################################################     

    def registerAllImages(self):
        # registers all moving images
        for movingImagePath in movingImagePaths:
            reg = Registration(self.paramterFolder)
            reg.register(self.fixedImagePath, movingImagePath)

            del reg
            gc.collect()


    ######################################################
    ### Label Propagation ################################
    ######################################################

    def propagate(self):
        # propagates the labels (only of the moving images)
        for labelPath in self.labelPathsToPropagate:
            matrixPaths = self.matchLabelPathToMatrixPaths(labelPath)
            transformParameterObject = self.util.loadTransformParameterObject(matrixPaths)
            labelImage = self.util.loadImageFrom(labelPath)
            for label in range(1, self.numberOfLabels + 1):
                image = self.extractLabel(labelImage, label)
                propagatedImage = self.applyTransform(image, transformParameterObject)

                fileName = os.path.basename(labelPath)
                fileNumber = fileName.split(".")[0]
                storeName = fileNumber + f"_label_{label}.nii.gz"
                storeFolder = f"propagated_images/label_{label}"
                self.util.ensureFolderExists(storeFolder)
                imagePath = os.path.join(storeFolder, storeName)
                itk.imwrite(propagatedImage,imagePath)


    def applyTransform(self, movingImage, transformParameterObject):
        # applies the transformation to the moving image
        resultImage = itk.transformix_filter(
            movingImage,
            transform_parameter_object=transformParameterObject
        )
        return resultImage
            
     
    def matchLabelPathToMatrixPaths(self, labelPath):
        # matches the labelpath to the matrixpath (the path of the transformation files)
        matrixPaths = []
        matrixFolder = "transformationMatrices"
        fileName = os.path.basename(labelPath)
        fileNumber = fileName.split("_")[0]

        for filePath in os.listdir(matrixFolder):
            if fileNumber in filePath:
                finalPath = os.path.join(matrixFolder, filePath)
                matrixPaths.append(finalPath)
        sortedMatrixPaths= sorted(matrixPaths, key=self.util.getRegistrationSortKey)

        return sortedMatrixPaths
        
    @staticmethod
    def extractLabel(inputImage, label):
        # sets label to 1 and all other values to 0
        thresholdFilter = itk.BinaryThresholdImageFilter.New(inputImage)
        thresholdFilter.SetLowerThreshold(label)
        thresholdFilter.SetUpperThreshold(label)
        thresholdFilter.SetInsideValue(1)
        thresholdFilter.SetOutsideValue(0)
        thresholdFilter.Update()
        
        outputImage = thresholdFilter.GetOutput()
        outputImage.CopyInformation(inputImage) # copy metadata
        
        return outputImage

    def getAllRelativeLabelPaths(self):
        # returns all relative label paths of the moving images
        labelFolder = "training-set/training-labels"
        AllFileNumbers = self.getAllFileNumbers(self.movingImagePaths)
        labelPathsToPropagate = []
        for fileNumber in AllFileNumbers:
            labelName = fileNumber + "_3C.nii.gz"
            labelPath = os.path.join(labelFolder, labelName)
            labelPathsToPropagate.append(labelPath)
        return labelPathsToPropagate

    @staticmethod
    def getAllFileNumbers(relativePaths):
        # returns all fileNumbers/fileNames from relativePaths (list)
        AllFileNumbers = []
        for relativePath in relativePaths:
            fileName = os.path.basename(relativePath)
            fileNumber = fileName.split(".")[0]
            AllFileNumbers.append(fileNumber)
        return AllFileNumbers

 
    ######################################################
    ### Building The Probabalistic Atlas #################
    ######################################################

    def buildAtlas(self):
        # builds the atlas and saves it as a nii.gz
        atlases = []
        for label in range(1, self.numberOfLabels + 1):
            labelFolder = f"propagated_images/label_{label}"
            labelImagePaths = self.util.getAllFiles(labelFolder)
            labelImages = self.loadAllImagesFromList(labelImagePaths)
            atlas = self.probabilisticAtlas(labelImages)
            atlas = atlas[..., np.newaxis] # new axis for storing
            atlases.append(atlas)
        self.storeAtlas(atlases)

    def loadAllImagesFromList(self, pathList):
        # loads all images from pathList
        allImages = [] 
        for imagePath in pathList:
            allImages.append(self.util.loadImageFrom(imagePath))
        return allImages

    @staticmethod
    def probabilisticAtlas(labelImages):
        # calculates the probabilistic Atlas 
        probabilisticAtlas = np.zeros(labelImages[0].shape)
        maskClass = np.zeros(labelImages[0].shape)
        for registeredMask in labelImages:

            maskClass += registeredMask

        maskClass/=len(labelImages)

        return maskClass

    def storeAtlas(self, atlases): 
        # stores the atlas           
        _, affine = self.readNiftiImage(self.fixedImagePath)
        finalAtlas = np.concatenate(atlases, axis=-1)
        reorderedImage = np.transpose(finalAtlas, (2, 1, 0, 3))
        newImage = nib.Nifti1Image(reorderedImage,affine)
        newImage.to_filename('atlas.nii.gz')

    @staticmethod
    def readNiftiImage(filePath):
        # reads a nifti 
        if not os.path.exists(filePath):
            raise FileNotFoundError(f"The file {imagePath} does not exist.")
        try:
            niftiImage = nib.load(filePath)
            return niftiImage.get_fdata(), niftiImage.affine
        except Exception as e:
            print(f"Error reading NIFTI image from {filePath}: {str(e)}")

    ######################################################
    ### Building The mean image ##########################
    ######################################################

    def buildMeanImage(self):
        # computes and stores the mean image
        self.propagateImages()
        propagatedImagePaths = self.util.getAllFiles("propagated_intesities")

        fixedImage = self.util.loadImageFrom(self.fixedImagePath)
        meanImage = itk.GetArrayFromImage(fixedImage)

        for imagePath in propagatedImagePaths:
            image = self.util.loadImageFrom(imagePath)
            meanImage += image
        
        meanImage /= len(propagatedImagePaths)
        self.storeMeanImage(meanImage)


    def propagateImages(self):
        # applies the calculated registrations to all moving images
        for movingImagePath in movingImagePaths:
            matrixPaths = self.matchImagePathToMatrixPaths(movingImagePath)
            transformParameterObject = self.util.loadTransformParameterObject(matrixPaths)
            movigImage = self.util.loadImageFrom(movingImagePath)
            propagatedImage = self.applyTransform(movigImage, transformParameterObject)

            storeName = os.path.basename(movingImagePath)
            storeFolder = f"propagated_intesities/"
            self.util.ensureFolderExists(storeFolder)
            imagePath = os.path.join(storeFolder, storeName)
            itk.imwrite(propagatedImage,imagePath)

    def matchImagePathToMatrixPaths(self, imagePath):
        # matches the image path to the matrix paths (the path of the transformation files)
        matrixPaths = []
        matrixFolder = "transformationMatrices"
        fileName = os.path.basename(imagePath)
        fileNumber = fileName.split(".")[0]

        for filePath in os.listdir(matrixFolder):
            if fileNumber in filePath:
                finalPath = os.path.join(matrixFolder, filePath)
                matrixPaths.append(finalPath)
        sortedMatrixPaths= sorted(matrixPaths, key=self.util.getRegistrationSortKey)

        return sortedMatrixPaths

    def storeMeanImage(self, meanImage):
        # stores the mean images as a nii.gz            
        _, affine = self.readNiftiImage(self.fixedImagePath)
        reorderedImage = np.transpose(meanImage, (2, 1, 0))
        newImage = nib.Nifti1Image(reorderedImage,affine)
        newImage.to_filename('meanImage.nii.gz')


if __name__ == "__main__":
    util = Utils()

    imagePaths = util.getAllFiles("training-set/training-images")
    fixedImagePath, movingImagePaths = util.splitFixedFromMoving(imagePaths, "1010")
    parameterFolder = "Par0038"

    atlas = Atlas(fixedImagePath, movingImagePaths, parameterFolder)

    atlas.registerAllImages()
    atlas.propagate()
    atlas.buildAtlas()
    atlas.buildMeanImage()

