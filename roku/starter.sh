#!/bin/bash
source roku.config


echo 'Clearing Data Folder!'
mkdir ${DATA_DIR} 2> /dev/null
rm -rf ${DATA_DIR}/*

#Creating global log file
export LOG_OUT_FILE="./output.txt"
touch $LOG_OUT_FILE

#Creating global key log file
export MITMPROXY_SSLKEYLOGFILE="${DATA_DIR}/SSLKEYLOGFILE.txt"
touch $MITMPROXY_SSLKEYLOGFILE

stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee $LOG_OUT_FILE
