#!/bin/bash
source roku.config


echo 'Clearing Data Folder!'
mkdir ${DATA_DIR} 2> /dev/null
rm -rf ${DATA_DIR}/*


touch $LOG_OUT_FILE
touch $MITMPROXY_SSLKEYLOGFILE

stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee $LOG_OUT_FILE
