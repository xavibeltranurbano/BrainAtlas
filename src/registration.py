import itk # itk-elastix
import numpy as np
import os

from utils import Utils

class Registration:

    util = Utils()

    def __init__(self, parameterFolder):
        self.parameterObject, self.registrationTypeList = self.initParamaterObject(parameterFolder)

    def initParamaterObject(self, parameterFolder):
        # initializes a parameter object with the registration in the parameter Folder. Automatically sorted after rigid -> affine -> bspline
        parameterObject = itk.ParameterObject.New()
        parameterMaps = self.util.getAllFiles(parameterFolder)
        sortedMaps = sorted(parameterMaps, key=self.util.getRegistrationSortKey)

        registrationTypeList = []
        for parameterPath in sortedMaps:
            parameterObject.AddParameterFile(parameterPath)
            registrationTypeList.append(os.path.basename(parameterPath).split(".")[0])
        return parameterObject, registrationTypeList

    def register(self, fixedImagePath, movingImagePath):
        # registers an image
        fixedImage = self.util.loadImageFrom(fixedImagePath)
        movingImage = self.util.loadImageFrom(movingImagePath)
        resultImage, resultTransformParameters = itk.elastix_registration_method(fixedImage, movingImage, parameter_object=self.parameterObject, log_to_console=False)
        self.safeTransformParameterObject(resultTransformParameters, movingImagePath)
        #itk.imwrite(resultImage,"test/registeredImage.nii.gz")

    def safeTransformParameterObject(self, resultTransformParameters, movingImagePath):
        # saves the computed registration parameter file
        nParameterMaps = resultTransformParameters.GetNumberOfParameterMaps()
        folderPath = "transformationMatrices"
        self.util.ensureFolderExists(folderPath)
        imageName = os.path.basename(movingImagePath)
        imageName = imageName.split(".")[0]

        for index in range(nParameterMaps):       
            fileName = imageName + "_" + self.registrationTypeList[index] + ".txt"
            finalPath = os.path.join(folderPath, fileName)
            parameterMap = resultTransformParameters.GetParameterMap(index)

            if index == nParameterMaps - 1:
                parameterMap['FinalBSplineInterpolationOrder'] =  "0"

            self.parameterObject.WriteParameterFile(parameterMap, finalPath)



if __name__ == "__main__":
    fixedImagePath = "training-set/training-images/1010.nii.gz"
    movingImagePath = "training-set/training-images/1017.nii.gz"
    paramterFolder = "fakeParameterFolder"

    reg = Registration(paramterFolder)
    reg.register(fixedImagePath, movingImagePath)


    
        