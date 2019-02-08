#!/bin/bash
set -x
export PLATFORM=roku
export PLATFORM_DIR=`realpath ../platforms/${PLATFORM}`
export ScriptDir=`realpath $PWD`
export MainDir=`realpath ../`

source ${PLATFORM_DIR}/config.txt

#Global log file
mkdir -p ${MainDir}/log 2> /dev/null
export LOG_OUT_FILE="${MainDir}/log/output.txt"

echo 'Clearing Data Folder!'
mkdir ${DATA_DIR} 2> /dev/null
#rm -rf ${DATA_DIR}/*


cd $MainDir
stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee $LOG_OUT_FILE
