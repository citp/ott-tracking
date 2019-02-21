#!/bin/bash
set -x

# Change platform if needed
#export PLATFORM=amazon
export PLATFORM=roku

export MITMPROXY_ENABLED=0
export MITMABLE_DOMAINS_WARM_UP_CRAWL=0  # if 1 it'll launch each channel 5times

export PLATFORM_DIR=`realpath ./platforms/${PLATFORM}`
export ScriptDir=`realpath ./scripts/`
export MainDir=`realpath $PWD`

source ${PLATFORM_DIR}/config.txt

#Global log folder/file
mkdir -p ${MainDir}/logs 2> /dev/null
export LogDir=${MainDir}/logs
export LOG_OUT_FILE="${LogDir}/output.txt"

#echo 'Clearing Data Folder!'
mkdir ${DATA_DIR} 2> /dev/null
#rm -rf ${DATA_DIR}/*


cd $MainDir
stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee $LOG_OUT_FILE
