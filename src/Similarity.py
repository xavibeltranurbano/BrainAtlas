import itk # itk-elastix
import numpy as np

from utils import Utils


class SimilarityAtlas:
    util = Utils()

    def __init__(self):
        self.imagePaths = self.util.getAllFiles("training-set/training-images")
        self.fixedImagePath, self.movingImagePaths = self.util.splitFixedFromMoving(self.imagePaths, "1000")

    def run(self):
        # finds the image with the highest similarity by comparison with the mean sqaure error
        registeredImages = self.registerAllImages()
        fixedImage = self.util.loadImageFrom(self.fixedImagePath)
        registeredImages.append(itk.GetArrayFromImage(fixedImage))

        vecSimilarities=[]
        for i,fixed in enumerate(registeredImages):
            similarityValue=0
            for j,moving in enumerate(registeredImages):
                if i!=j: # we do this to not to compute ther MSE of the same image
                    # Compute MSE
                    similarityValue+=np.mean((fixed - moving) ** 2)
            vecSimilarities.append(np.mean(similarityValue))

        nameFixed=np.argmin(vecSimilarities)
        print(f"The name of the fixed image with the highest similarity is {self.movingImagePaths[nameFixed]}" )
        return nameFixed

    def registerAllImages(self):
        # registers all moving images
        resultImages = []
        for movingImagePath in self.movingImagePaths:
            registeredImage = self.register(self.fixedImagePath, movingImagePath)
            resultImages.append(itk.GetArrayFromImage(registeredImage))
        return resultImages

    def register(self, fixedImagePath, movingImagePath):
        # registers an image
        fixedImage = self.util.loadImageFrom(fixedImagePath)
        movingImage = self.util.loadImageFrom(movingImagePath)
        resultImage, resultTransformParameters = itk.elastix_registration_method(fixedImage, movingImage, parameter_object=self.initParamaterObject(), log_to_console=False)
        return resultImage

    def initParamaterObject(self):
        # initializes a parameter object
        parameterObject = itk.ParameterObject.New()
        defaultRigidParameterMap = parameterObject.GetDefaultParameterMap('rigid')
        parameterObject.AddParameterMap(defaultRigidParameterMap)
        return parameterObject



if __name__ == "__main__":
    simAtlas = SimilarityAtlas()
    simAtlas.run()
