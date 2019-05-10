#!/usr/bin/env python3

import io
import os
import argparse
import re
import imutils
import copy
import cv2
import threading
import json
from queue import Queue
from google_auth_oauthlib import flow
from google.cloud import vision
from google.cloud.vision import types
from skimage.measure import compare_ssim
from itertools import tee, islice, chain
from itertools import zip_longest as izip
import pytesseract


class OCRHelper(object):

    def __init__(self, keyFile):
        self.LOGIN =        ["WATCH FREE", 
                            "SIGN IN", 
                            "TRIAL", 
                            "REGISTER",
                            "CUSTOMERS",
                            "EMAIL ADDRESS",
                            "PASSWORD",
                            "NEW USER",
                            "JOIN FOR FREE",
                            "PREMIUM",
                            "PER MONTH"]

        self.ACTIVATION =    ["ACTIVATE DEVICE",
                            "DEVICES",
                            "TV PROVIDER",
                            "ACTIVATION CODE",
                            "ACTIVATE",
                            "CONNECT",
                            "AUTOMATICALLY REFRESH"]

        self.ENTRYDEVICE =   ["SPACE BAR",
                            "KEYBOARD",
                            "KEYPAD",
                            "INPUT DEVICE"]

        self.ROKUACCOUNT =   ["FROM YOUR ROKU ACCOUNT",
                            "GO.ROKU.COM/CHANNELSIGNUP"]

        self.DUPLICATE =     .95

        self.cloudVisionClient = vision.ImageAnnotatorClient.from_service_account_json(keyFile)

        self.screenshotList = []
        self.screenshot =  {    'timestamp' : "",
                                'customLabels' : [],
                                'labels' : [],
                                'labelScores': {},
                                'textBody' : "",
                                'textBodyBoundsX' : [],
                                'textBodyBoundsY' : [],
                                'words' : [],
                                'wordBoundsX' : {},
                                'wordBoundsY' : {},
                                'SSIM' : ""}


    def previous_and_next(self, some_iterable):
        prevs, items, nexts = tee(some_iterable, 3)
        prevs = chain([None], prevs)
        nexts = chain(islice(nexts, 1, None), [None])
        return izip(prevs, items, nexts)


    def imageDiff(self, firstImagePath, secondImagePath, secondImageName):
        imageA = cv2.imread(firstImagePath)
        imageB = cv2.imread(secondImagePath)
        
        grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
        grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)

        (score, diff) = compare_ssim(grayA, grayB, full=True)
        diff = (diff * 255).astype("uint8")
        self.screenshot["SSIM"] = float(score)


    def cloudVision(self, imageFile, currentScreenshotName):
        with io.open(imageFile, 'rb') as image_file:
            content = image_file.read()

        image = types.Image(content=content)

        response = self.cloudVisionClient.label_detection(image=image)
        labels = response.label_annotations

        for label in labels:
            self.screenshot["labels"].append(str(label.description))
            self.screenshot["labelScores"][label.description] = float(label.score)

        response = self.cloudVisionClient.text_detection(image=image)
        texts = response.text_annotations

        if len(texts) > 0:
            self.screenshot["textBody"] = texts[0].description
            for vertex in texts[0].bounding_poly.vertices:
                self.screenshot["textBodyBoundsX"].append(int(vertex.x))
                self.screenshot["textBodyBoundsY"].append(int(vertex.y))

            for text in texts[1:]:
                self.screenshot["words"].append(str(text.description))
                self.screenshot["wordBoundsX"][text.description] = []
                self.screenshot["wordBoundsY"][text.description] = []
                for vertex in text.bounding_poly.vertices:
                    self.screenshot["wordBoundsX"][text.description].append(int(vertex.x))
                    self.screenshot["wordBoundsY"][text.description].append(int(vertex.y))


    def processImage(self, screenshotDirectory, previousScreenshotName, currentScreenshotName):
        imagePathPrefix = screenshotDirectory + '/'
        currentScreenshot = imagePathPrefix + currentScreenshotName

        if previousScreenshotName != None:
            previousScreenshot = imagePathPrefix + previousScreenshotName
            self.imageDiff(previousScreenshot, currentScreenshot, currentScreenshotName)
        else:
            self.screenshot["SSIM"] = None
            
        tesseractOutput = pytesseract.image_to_string(currentScreenshot)
        unicodeStrippedTesseractOutput = re.sub(r'[^\x00-\x7f]',r'', tesseractOutput)
        filteredTesseractOutput = re.sub('[^A-Za-z0-9]+', '', unicodeStrippedTesseractOutput)

        if self.screenshot["SSIM"] == None:
            self.cloudVision(currentScreenshot, currentScreenshotName)
        else:
            if self.screenshot["SSIM"] <= self.DUPLICATE and len(filteredTesseractOutput) > 5:
                self.cloudVision(currentScreenshot, currentScreenshotName)
            else:
                self.screenshot["textBody"] = unicodeStrippedTesseractOutput
                if "TESSERACT" not in self.screenshot["customLabels"]:
                    self.screenshot["customLabels"].append("TESSERACT")
                self.screenshot["customLabels"]
        self.applyCustomLabels()


    def isInt(self, character):
        try: 
            int(character)
            return True
        except ValueError:
            return False


    def applyCustomLabels(self):
        for keyword in self.LOGIN:
            if keyword in self.screenshot["textBody"].upper():
                if "LOGIN" not in self.screenshot["customLabels"]:
                    self.screenshot["customLabels"].append("LOGIN")
        for keyword in self.ENTRYDEVICE:
            if keyword in self.screenshot["textBody"].upper():
                if "ENTRY DEVICE" not in self.screenshot["customLabels"]:
                    self.screenshot["customLabels"].append("ENTRYDEVICE")
        for keyword in self.ROKUACCOUNT:
            if keyword in self.screenshot["textBody"].upper():
                if "ROKUACCOUNT" not in self.screenshot["customLabels"]:
                    self.screenshot["customLabels"].append("ROKUACCOUNT")
        for keyword in self.ACTIVATION:
            if keyword in self.screenshot["textBody"].upper():
                if "ACTIVATION" not in self.screenshot["customLabels"]:
                    self.screenshot["customLabels"].append("ACTIVATION")
            for word in self.screenshot["words"]:
                if len(word) == 6 or len(word) == 7:
                    for letter in word:
                        if self.isInt(letter):
                            if "ENTRYDEVICE" not in self.screenshot["customLabels"]:
                                if "ACTIVATION" not in self.screenshot["customLabels"]:
                                    self.screenshot["customLabels"].append("ACTIVATION")
        if self.screenshot["SSIM"] != None:    
            if self.screenshot["SSIM"] > self.DUPLICATE:
                if "DUPLICATE" not in self.screenshot["customLabels"]:
                    self.screenshot["customLabels"].append("DUPLICATE")
        

    def customPrinterDict(self, d, indent=0):
        OKGREEN = '\033[92m'
        ENDC = '\033[0m'
        for key, value in d.items():
            if str(key) != "timestamp":
                print(OKGREEN + '\t' * indent + str(key) + ENDC)
                if isinstance(value, dict):
                    self.customPrinterDict(value, indent+1)
                else:
                    print('\t' * (indent+1) + str(value).replace("\n", "\n\t\t"))


    def printChannel(self):
        OKGREEN = '\033[92m'
        ENDC = '\033[0m'
        for item in self.screenshotList:
            print(OKGREEN + "timestamp" + '  -  ' + item["timestamp"] + ENDC + "\n")
            self.customPrinterDict(item, 1)
            print("\n")

    def writeJson(self, outputDirectory, channelName):
        outputFile = outputDirectory + '/' + channelName + '.ocr.json'
        with open(outputFile, 'w') as outFile:  
            json.dump(self.screenshotList, outFile)

    def processChannel(self, screenshotDirectory, outputDirectory, channelName):
        directoryFiles = os.listdir(screenshotDirectory)
        channelList = []
        for file in directoryFiles:
            if file.startswith(channelName + '-'):
                try:
                    cv2.imread(screenshotDirectory + '/' + file)
                except:
                    continue
                channelList.append(file)
        channelList.sort()
        for previousScreenshot, currentScreenshot, _ in self.previous_and_next(channelList):
            if currentScreenshot != None:
                self.screenshot["timestamp"] = currentScreenshot.split('-', 1)[-1].split('.')[0]
                self.processImage(screenshotDirectory, previousScreenshot, currentScreenshot)    
                self.screenshotList.append(copy.deepcopy(self.screenshot))
                self.screenshot =  {    'timestamp' : "",
                        'customLabels' : [],
                        'labels' : [],
                        'labelScores': {},
                        'textBody' : "",
                        'textBodyBoundsX' : [],
                        'textBodyBoundsY' : [],
                        'words' : [],
                        'wordBoundsX' : {},
                        'wordBoundsY' : {},
                        'SSIM' : ""}
        self.writeJson(outputDirectory, channelName)
        #self.printChannel()
        return self.screenshotList

class OCRManager(object):
    def __init__(self, keyFile, screenshotDirectory, outputDirectory, threadCount):
        self.keyFile = keyFile
        self.screenshotDirectory = screenshotDirectory
        self.outputDirectory = outputDirectory
        self.threadCount = threadCount

        self.q = Queue()
        self.result = {}


    def threader(self):
        while True:
            channelName = self.q.get()

            OCRWorker = OCRHelper(self.keyFile)
            self.result[channelName] = OCRWorker.processChannel(self.screenshotDirectory, self.outputDirectory, channelName)

            self.q.task_done()


    def processChannels(self, channelList, result):
        self.result = result
        for thread in range(self.threadCount):
            t = threading.Thread(target=self.threader)
            t.daemon = True
            t.start()       
        for channel in channelList:
            self.q.put(channel)
        self.q.join()  

    def processDirectory(self, result):
        directoryFiles = os.listdir(self.screenshotDirectory)
        channelList = []
        for file in directoryFiles:
            if channelList.count(file.split('-')[0]) == 0:
                channelList.append(file.split('-')[0])
        self.processChannels(channelList, result)

if __name__ == '__main__':
    # relative paths don't work if the script is called from a different path
    CLOUD_VISION_API_KEY = "service_key.json"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_key_path = os.path.join(script_dir, CLOUD_VISION_API_KEY)

    parser = argparse.ArgumentParser(
        description="Gets the text in all the image files in the given"
        " directory using the Google Cloud Vision API")
    parser.add_argument('image_dir', help='Folder containing the images')
    parser.add_argument(
        'output_dir',
        help='Name of the output folder where the results will be dumped')
    parser.add_argument('threads', help='Number of threads to use')

    args = parser.parse_args()

    img_dir = args.image_dir
    threads = int(args.threads)
    output_dir = args.output_dir   
    
    OCRResult = {}
    OCR = OCRManager(api_key_path, img_dir, output_dir, threads)
    OCR.processDirectory(OCRResult)
