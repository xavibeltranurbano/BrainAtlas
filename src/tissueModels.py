import os
import numpy as np
import matplotlib.pyplot as plt
from utils import Utils
from scipy.ndimage import gaussian_filter
import pandas as pd



class TissueModels:
    util = Utils()

    def __init__(self, imageFolder, maskFolder):
        self.imagePaths = self.util.getAllFiles(imageFolder)
        self.maskPaths = self.util.getAllFiles(maskFolder)
        self.numberOfLabels = 3

    def execute(self):
        # calculates and stores a TissueModel, masking and normalizing each image between 0 and 255
        vecIntensitiesDistributions = self.computeVecIntensityDistribtions()

        # Compute and plot histograms
        histograms, edgesList = self.computeDistribution(vecIntensitiesDistributions, normalize=True)
        histograms_probabilities = self.normalizeHistogramsList(histograms)

        self.plotDistributionsNorm(histograms, edgesList, name_axisy='p(X)',name_plot="Distribution_Norm.jpeg")
        self.plotHistogramProbabilities(histograms_probabilities,edgesList, name_axisy='p(X|Tissue)', name_plot="ProbabilityHistogram.jpeg")
        self.storeTissueModel(histograms_probabilities)

        histograms_distribution, edgesList = self.computeDistribution(vecIntensitiesDistributions, normalize=False)
        self.plotDistributions(histograms_distribution, edgesList,name_axisy='Pixel Count',name_plot="Distribution.jpeg")
        

    ######################################################
    ### Masking, Normalizing and Concatenating ###########
    ######################################################

    def computeVecIntensityDistribtions(self):
        # adds all pixels to the list of the corresponding label (multiple labels possible)
        pairs = self.matchMasksToImages()

        vecIntensitiesDistributions= [[] for _ in range(self.numberOfLabels)]
        for imagePath, maskPath in pairs:
            image, _ = self.util.readNiftiImage(imagePath)
            mask, _ = self.util.readNiftiImage(maskPath)
            maskedImage = np.where(mask > 0, image, 0)
            normalizedImage = self.normalizeImage(maskedImage)

            for label in range(self.numberOfLabels):
                vecIntensitiesDistributions[label].extend(normalizedImage[mask==label+1] )
        return vecIntensitiesDistributions

    def matchMasksToImages(self):
        # matches mask to image
        matches = []
        for imagePath in self.imagePaths:
            baseName = os.path.basename(imagePath).split('.')[0]
            expectedMaskName = f"{baseName}"

            for maskPath in self.maskPaths:
                if expectedMaskName in maskPath:
                    matches.append((imagePath,maskPath ))
                    break  
        return matches

    @staticmethod
    def normalizeImage(vec, newMin=0, newMax=255):
        # min max normalization
        minVal = np.min(vec)
        maxVal = np.max(vec)
        normalized = (vec - minVal) / (maxVal - minVal) * (newMax - newMin) + newMin
        return normalized


    ######################################################
    ### Compute Histograms ###############################
    ######################################################

    def computeDistribution(self, vecIntensitiesDistributions,normalize=False):
        histograms = []
        edgesList = []  
        for channel_data in vecIntensitiesDistributions:
            data_array = np.array(channel_data).reshape(-1, 1)
            data_array = data_array.astype(np.uint8)  # For 8-bit

            # Compute histogram
            hist, edges = np.histogram(data_array, bins=255, range=(0, 255))
            hist = hist.astype(np.float64)
            if normalize:
                hist/=np.sum(hist)

            hist = gaussian_filter(hist, sigma=20)

            histograms.append(hist)
            edgesList.append(edges)  

        return histograms, edgesList  

    def normalizeHistogramsList(self, histogramsList):
        # normalization the sum of probabilities for each triplet(CSF, GM, WM) to one
        stackedHistograms = np.stack(histogramsList, axis=0)
        sumOfBins = np.sum(stackedHistograms, axis=0)
        sumOfBins[sumOfBins == 0] = 1 # avoid division by zero
        normalizedHistograms = stackedHistograms / sumOfBins
        return list(normalizedHistograms)

    
    ######################################################
    ### Plot Histograms ##################################
    ######################################################

    def plotHistogramProbabilities(self, histograms, edgesList, name_axisy, name_plot):
        colors = ['red', 'green', 'blue']  
        labels = ['CSF', 'WM', 'GM']  
        plt.figure(figsize=(10, 5))

        for i, (hist, edges) in enumerate(zip(histograms, edgesList)):
            plt.plot(edges[:-1], hist, color=colors[i], label=labels[i])

        plt.title('Intensity Tissue Probabilities')
        plt.xlabel('Pixel Intensity')
        plt.ylabel(name_axisy)
        plt.legend(loc='upper right')
        plt.xlim([0, 255])
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.tight_layout()
        plt.savefig(f"images/{name_plot}",dpi=600)
        plt.show()

    def plotDistributionsNorm(self, histograms, edgesList, name_axisy, name_plot):
        colors = ['red', 'green', 'blue'] 
        labels = ['CSF', 'WM', 'GM']  
        plt.figure(figsize=(10, 5))

        for i, (hist, edges) in enumerate(zip(histograms, edgesList)):
            plt.plot(edges[:-1], hist, color=colors[i], label=labels[i])

        plt.title('Probability Density Function of Each Tissue')
        plt.xlabel('Pixel Intensity')
        plt.ylabel(name_axisy)
        plt.legend(loc='upper right')
        plt.xlim([0, 255])
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.tight_layout()
        plt.savefig(f"images/{name_plot}",dpi=600)
        plt.show()

    def plotDistributions(self, histograms, edgesList, name_axisy, name_plot):
        colors = ['red', 'green', 'blue']  
        labels = ['CSF', 'WM', 'GM']  

        fig, main_ax = plt.subplots(figsize=(10, 5))

        for i, (hist, edges) in enumerate(zip(histograms, edgesList)):
            main_ax.plot(edges[:-1], hist, color=colors[i], label=labels[i])

        main_ax.set_title('Histograms of Tissue Intensities')
        main_ax.set_xlabel('Pixel Intensity')
        main_ax.set_ylabel(name_axisy)
        main_ax.legend(loc='upper right')
        main_ax.set_xlim([0, 255])
        main_ax.grid(True, which='both', linestyle='--', linewidth=0.5)

        # zoom region
        x1, x2, y1, y2 = 0, 100, 0, 5000
        axins = main_ax.inset_axes([0.07, 0.7, 0.2, 0.2]) 
        for i, (hist, edges) in enumerate(zip(histograms, edgesList)):
            axins.plot(edges[:-1], hist, color=colors[i])

        axins.set_xlim(x1, x2)
        axins.set_ylim(y1, y2)

        main_ax.indicate_inset_zoom(axins)

        plt.tight_layout()
        plt.savefig(f"images/{name_plot}",dpi=600)  
        plt.show()

    @staticmethod
    def storeTissueModel(histograms_distribution):
        df = pd.DataFrame(histograms_distribution).T 
        df.columns = ['CSF', 'WM', 'GM']
        df.to_csv('TissueModel.csv', index=False)


    

if __name__ == "__main__":
    utils = Utils()

    maskFolder= "training-set/training-labels/"
    imageFolder = "training-set/training-images/"

    tissueModels=TissueModels(imageFolder, maskFolder)
    tissueModels.execute()


