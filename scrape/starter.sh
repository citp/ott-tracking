#!/bin/bash
set -x

#We have to run source twice to write to a file
source global.conf
source global.conf |& tee $LOG_OUT_FILE

#creating local log folder
mkdir -p ${LogDir} 2> /dev/null
rm -rf ${LogDir}/*

#echo 'Clearing Data Folder!'
mkdir ${DATA_DIR} 2> /dev/null
#rm -rf ${DATA_DIR}/*

#optional
DATE_PREFIX=`python3 -c 'from datetime import datetime; print(datetime.now().strftime("%Y%m%d-%H%M%S"))'`
DATA_DIR=${DATA_DIR}-${DATE_PREFIX}

##CRAWL COMMANDS!
# Automatic crawler
stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee -a $LOG_OUT_FILE
# Manual crawler
#stdbuf -oL -eL python3 -u ./manual_scraper.py |& tee $LOG_OUT_FILE
