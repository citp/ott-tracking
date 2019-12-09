#!/usr/bin/env python3

import io
import os
import argparse
import re
import imutils
import csv
import threading
import sys
import json
from datetime import datetime
from queue import Queue
from collections import OrderedDict 
from fuzzysearch import find_near_matches
from fuzzywuzzy import process
from copy import deepcopy
from glob import glob
from os.path import basename, join, dirname
from nltk.corpus import words


USE_EXACT_MATCH = True
USE_NAME_FILE = False
OCR_JSON_EXT = ".ocr.json"
LOG_EXT = ".log"



MIN_IMDB_SEARCH_LEN = 3  # don't search string shorter than this
# otherwise get a ton of one character matches
EXCLUDE_MENU_INTERFACE_STRINGS = True
# TODO: some of these interface strings can be replaced by regexes
MENU_INTERFACE_STRINGS =   ['Help','Year', 'star', 'Films', 'BAB',
    'free', 'search', 'home', 'back', 'play', 'options', 'loading', 'loading...', 'quit', 'episodes',
    'login', 'the', 'welcome', 'clear',
    'features', 'channel', 'menu', 'settings', 'series', 'weather', '...', 'yes', 'subscribe!',
    'live', 'favorites', 'featured', 'headlines', 'streaming', 'videos',
    'schedule', 'live tv', 'browse', 'events', 'news', 'lifestyle', 'sports', 'beta', 'loading',
    '...', '00:01:18', '04:15', '100%', '10:00', '1-1', '11:33', '11:59 am',
    '11 pm', '19:00', '1 episode', '1 of 13', '20000 leagues under the sea', '2:00 am',
    '23:59', '28s', '3,000', '3:00 pm', '3:15 am', '3am', '4:12', '4:37', '58%', '70',
    '8:00 am', '8:28 am', '8am', '9:30 am', '9am', '9pm', 'about', 'account', 'accounts',
    'action', 'ad 2', 'advanced', 'after', 'air', 'all', 'alternative', 'audio', 'a-z',
    'blues', 'breaking news', 'cancel', 'canceled', 'cardio', 'cast', 'cast & crew',
    'chase', 'children', 'classics', 'clear', 'comedy', 'company', 'continue', 'coverage',
    'credits', 'culture', 'cycling', 'dads', 'dance', 'deals', 'delete', 'dismiss',
    'documentaries', "don't", 'double features', 'dragon', 'drama', 'e11', 'earth',
    "editor's picks", 'e-mail', 'english', 'episode 1', 'episode 2', 'episode 3',
    'episode 4', 'episode 5', 'episode 6', 'episode 7', 'episode 8', 'episodes',
    'eta', 'ever', 'everywhere', 'exchange', 'existing', 'exit', 'exit', 'explore',
    'extras', 'f13', 'family', 'fandango', 'fax', 'feed', 'fiction', 'filmmakers',
    'films', 'five', 'follow', 'followed', 'food', 'football', 'fresh', 'furniture',
    'gal', 'gals', 'game', 'games', 'go back', 'guide', 'hardware', 'help', 'history',
    'hope', 'horror', 'jazz', 'kids', 'kris', 'library', 'like', 'listening', 'live!',
    'live broadcast', 'live stream', 'livestream', 'live streams', 'loading', 'loading...',
    'local', 'local news', 'location', 'login', 'love', 'most popular', 'mothers', 'movie',
    'movies', 'music', 'music videos', 'name', 'network', 'new', 'news 12', 'news talk',
    'next', 'no. 6', 'noon', 'nov', 'now', 'now!', 'now playing', 'nursery rhymes',
    'on air', 'on demand', 'only', 'option', 'original', 'originals', 'out', 'photos',
    'player', 'policy', 'pop', 'popular', 'popular', 'present', 'presents', 'price',
    'privacy policy', 'pro', 'produce', 'producer', 'production', 'quit', 'registration',
    'related', 'replay', 'resume', 'running time', 'saved', 'sean', 'setup', 'shopping',
    'smile', 'special guest', 'sponsored by', 'star', 'start', 'states', 'stations',
    'store', 'submit', 'subscribe!', 'tattoo', 'teen', 'television', 'ten', 'terms of use',
    'test', 'the', 'then', 'time', "today's special", "tomorrow's world", 'top picks',
    'top stories', 'tour', 'trailer', 'treat', 'trending', 'tuesday', 'tweens',
    'uncommon', 'universe', 'up close', 'upcoming', 'up next', 'username',
    'warning', 'watch', 'watched', 'week 1', 'welcome', 'what', 'year']

MENU_INTERFACE_STRINGS = [w.lower() for w in MENU_INTERFACE_STRINGS]


class IMDBHelper(object):

    def __init__(self, titleFile, nameFile, matchDistance):
        self.matchingDistance = matchDistance
        self.channelData = []
        self.fwdEventTime = None
        self.playbackDetectTime = None
        self.imdb_titles = []
        self.found_titles = set()

    def searchHelper(self, names, titles, screenshot, channelName):
        screenshot["imdbTitle"] = []
        screenshot["ocrTitle"] = []
        screenshot["titleMatchDistance"] = {}
        searched_strs = set()
        for screenshot_str in screenshot["textBody"].split('\n'):
            if screenshot_str in searched_strs:
                continue
            searched_strs.add(screenshot_str)
            if not screenshot_str or len(screenshot_str) < MIN_IMDB_SEARCH_LEN:
                continue
            if EXCLUDE_MENU_INTERFACE_STRINGS and screenshot_str.lower() in MENU_INTERFACE_STRINGS:
                continue
            try:
                int(screenshot_str)
            except:
                pass
            else:  # this is just a number
                continue

            if screenshot_str.lower() in words.words():  # in dictionary
                continue

            # print("Will search for %s (Ch: %s)" % (screenshot_str, channelName))

            if USE_EXACT_MATCH:
                if screenshot_str in titles and screenshot_str not in self.found_titles:
                    self.found_titles.add(screenshot_str)
                    # print("\n============= IMDB TITLE MATCH - START=============")
                    print("%s\t%s\t%s" % (channelName, screenshot["timestamp"], screenshot_str))
                    # print(screenshot["textBody"])
                    # print("\n============= IMDB TITLE MATCH - END=============")
                    self.imdb_titles.append((channelName, screenshot["timestamp"], screenshot_str))
            else:
                matches = process.extract(screenshot_str, titles, limit=1)
                if not len(matches):
                    continue
                MIN_MATCH_THRESHOLD = 95
                for match in matches:
                    if match[1] >= MIN_MATCH_THRESHOLD:
                        title = match[0]
                        if "IMDB_TITLE" not in screenshot["customLabels"]:
                            screenshot["customLabels"].append("IMDB_TITLE")
                        print("Matched with IMDB title |", screenshot_str, "==", title, "| similarity", match[1], channelName)
                        screenshot["imdbTitle"].append(title)
                        screenshot["ocrTitle"].append(screenshot_str)
                        screenshot["titleMatchDistance"][title] = match[1]

    def searchText(self, names, titles, channelName):
        # Remove titles shorter than 3 chars
        titles = set([title for title in titles if len(title) >= MIN_IMDB_SEARCH_LEN])
        #Remove single word strings 
        titles = set([title for title in titles if len(title.split()) >= 2])
        matchFound = False
        for screenshot in self.channelData:
            if "TESSERACT" in screenshot["customLabels"] or "ACTIVATION" in screenshot["customLabels"] or "LOGIN" in screenshot["customLabels"]:
                continue
            if self.fwdEventTime and self.playbackDetectTime:
                if abs(int(float(screenshot["timestamp"]) + 1 - self.fwdEventTime)) < 0 or abs(int(float(screenshot["timestamp"]) - 1 - self.playbackDetectTime)) > 0:
                    continue
            else:
                continue
            self.searchHelper(names, titles, screenshot, channelName)
            if screenshot.get("imdbTitle") is not None or screenshot.get("imdbName") is not None:
                matchFound = True

    def searchText_old(self, names, titles, channelName):
        for name in names:
            for screenshot in self.channelData:
                if "TESSERACT" not in screenshot["customLabels"] and "ACTIVATION" not in screenshot["customLabels"] and "LOGIN" not in screenshot["customLabels"] :
                    screenshot["imdbName"] = []
                    screenshot["ocrName"] = [] 
                    screenshot["nameMatchDistance"] = {}               
                    compareResult = find_near_matches(name, screenshot["textBody"], max_l_dist=self.matchingDistance)
                    if len(compareResult) == 0:
                        continue
                    else:
                        if compareResult[0].end != compareResult[0].start:
                            if "IMDB_NAME" not in screenshot["customLabels"]:
                                screenshot["customLabels"].append("IMDB_NAME")
                            screenshot["imdbName"].append(name)
                            screenshot["ocrName"].append(screenshot["textBody"][compareResult[0].start:compareResult[0].end])
                            screenshot["nameMatchDistance"][name] = compareResult[0].dist

        for title in titles:
            if len(title) < MIN_IMDB_SEARCH_LEN:
                continue
            if EXCLUDE_MENU_INTERFACE_STRINGS and title in MENU_INTERFACE_STRINGS:
                continue

            for screenshot in self.channelData:
                if "TESSERACT" in screenshot["customLabels"] or "ACTIVATION" in screenshot["customLabels"] or "LOGIN" in screenshot["customLabels"]:
                    continue
                screenshot["imdbTitle"] = []
                screenshot["ocrTitle"] = []
                screenshot["titleMatchDistance"] = {}
                for screenshot_str in screenshot["textBody"].split('\n'):
                    if not screenshot_str or len(screenshot_str) < MIN_IMDB_SEARCH_LEN:
                        continue
                    compareResult = find_near_matches(screenshot_str, title,
                                                      max_l_dist=self.matchingDistance,
                                                      max_deletions=0,
                                                      max_insertions=0)
                # compareResult = find_near_matches(title, screenshot["textBody"], max_l_dist=self.matchingDistance)
                    if len(compareResult) == 0:
                        continue
                    else:
                        if compareResult[0].end != compareResult[0].start:
                            if "IMDB_TITLE" not in screenshot["customLabels"]:
                                screenshot["customLabels"].append("IMDB_TITLE")
                            print("Matched with IMDB title", screenshot_str, title, self.matchingDistance)
                            print("compareResult", compareResult)
                            screenshot["imdbTitle"].append(title)
                            screenshot["ocrTitle"].append(screenshot["textBody"][compareResult[0].start:compareResult[0].end])
                            screenshot["titleMatchDistance"][title] = compareResult[0].dist

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
        for item in self.channelData:
            print(OKGREEN + "timestamp" + '  -  ' + item["timestamp"] + ENDC + "\n")
            self.customPrinterDict(item, 1)
            print("\n")


    def readLog(self, logDirectory, logName):
        logFile = logDirectory + '/' + logName

        with open(logFile) as logFile:  
            logFileString = logFile.readlines()
            for line in logFileString:
                if "Playback detected on channel" in line:
                    time_str = line.split('[')[1].split(']')[0]
                    timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f').timestamp()
                    self.playbackDetectTime = timestamp
                if "Pressing Select" in line:
                    time_str = line.split('[')[1].split(']')[0]
                    timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f').timestamp()
                    self.fwdEventTime = int(timestamp)


    def readJSON(self, inputDirectory, channelName):
        inputFile = inputDirectory + '/' + channelName + '.ocr.json'
        with open(inputFile) as inFile:  
            self.channelData = json.load(inFile)


    def writeJSON(self, outputDirectory, channelName):
        outputFile = outputDirectory + '/' + channelName + '.ocr.json'
        with open(outputFile, 'w') as outFile:  
            json.dump(self.channelData, outFile)

    def dump_results(self, inputDirectory, channelName):
        outputFile = inputDirectory + '/global_imdb_titles.json'
        with open(outputFile, 'a') as outFile:
            # json.dump(self.imdb_titles, outFile)
            for channelName, ts, title in self.imdb_titles:
                outFile.write("%s\t%s\t%s\n" % (channelName, ts, title))


    def processChannel(self, inputDirectory, outputDirectory, logDirectory, imdbNames, imdbTitles, channelName, logName):
        self.readJSON(inputDirectory, channelName)
        self.readLog(logDirectory, logName)
        self.searchText(imdbNames, imdbTitles, channelName)
        # self.printChannel()
        self.writeJSON(outputDirectory, channelName)
        self.dump_results(inputDirectory, channelName)



class tagThreader(object):
    def __init__(self, titleFile, nameFile, inputDirectory, outputDirectory, logDirectory, matchDistance, threadCount):
        self.titleFile =   titleFile
        self.nameFile =    nameFile
        self.matchDistance = matchDistance
        self.inputDirectory = inputDirectory
        self.outputDirectory = outputDirectory
        self.logDirectory = logDirectory
        self.threadCount = threadCount

        self.names = []
        self.titles = []
        self.channelData = []
        self.logNames = {}

        self.q = Queue()


    def readIMDB(self):
        csv.field_size_limit(sys.maxsize)
        if USE_NAME_FILE:
            with open(self.nameFile) as tsvfile:
                reader = csv.DictReader(tsvfile, dialect='excel-tab')
                for screenshot in reader:
                    self.names.append(str(screenshot["primaryName"]))
        with open(self.titleFile) as tsvfile:
            reader = csv.DictReader(tsvfile, dialect='excel-tab')
            for screenshot in reader:
                self.titles.append(str(screenshot["title"]))

        print(len(self.titles), "titles loaded")


    def threader(self):
        while True:
            channelName = self.q.get()

            IMDBWorker = IMDBHelper(self.titleFile, self.nameFile, self.matchDistance)
            IMDBWorker.processChannel(self.inputDirectory, self.outputDirectory, self.logDirectory, self.names, self.titles, channelName, self.logNames[channelName])

            self.q.task_done()
            # print("Finished processing %s" % channelName)


    def processChannels(self, channelList):
        for thread in range(self.threadCount):
            t = threading.Thread(target=self.threader)
            t.daemon = True
            t.start()
        for channel in channelList:
            self.q.put(channel)
        self.q.join()


    def processDirectory(self):
        self.readIMDB()

        channels = set()
        for ocr_file in glob(join(self.inputDirectory, ("*%s" % OCR_JSON_EXT))):
            channel_id = basename(ocr_file).replace(OCR_JSON_EXT, '')
            channels.add(channel_id)
        
        for log_file in glob(join(self.logDirectory, ("*%s" % LOG_EXT))):
            channel_id = basename(log_file).split("-")[0]
            logFile = basename(log_file)
            self.logNames[channel_id] = logFile

        self.processChannels(list(channels))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Compares OCR text to the IMDB name and title"
        " databases using a fuzzy search with configurable matching distance")
    parser.add_argument('titleFile', help='IMDB Title TSV file')
    if USE_NAME_FILE:
        parser.add_argument('nameFile', help='IMDB Title TSV file')
    parser.add_argument(
        'inputDir',
        help='Name of the input folder where the JSONs are stored')
    parser.add_argument(
        'outputDir',
        help='Name of the out folder where the updated JSONs will be stored')
    parser.add_argument(
        'matchDistance',
        help='Distance a string can be away from the IMDB database and still be considered a match')
    parser.add_argument('threads', help='Number of threads to use')
    args = parser.parse_args()

    titleFile = args.titleFile
    if USE_NAME_FILE:
        nameFile = args.nameFile
    else:
        nameFile = ''

    inputDirectory = args.inputDir
    inputDirectory = inputDirectory.rstrip('/')
    logDirectory = join(inputDirectory, 'logs')
    inputDirectory = join(inputDirectory, 'post-process')
    outputDirectory = args.outputDir
    print(inputDirectory, logDirectory)

    matchDistance = int(args.matchDistance)
    threads = int(args.threads)

    IMDB = tagThreader(titleFile, nameFile, inputDirectory, outputDirectory, logDirectory, matchDistance, threads)
    IMDB.processDirectory()
