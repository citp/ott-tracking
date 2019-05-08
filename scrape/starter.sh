#!/bin/bash
#We have to run source twice to write to a file
source global.conf


function cleanup(){
  echo "Will run cleanup"
  pkill -f capture_screenshot
  pkill -2 -f dump_netstat.sh
  ./scripts/iptables_flush_all.sh
  ./scripts/kill_ffmpeg.sh
}


#creating local log folder
rm -rf ${LogDir} 2> /dev/null
mkdir -p ${LogDir} 2> /dev/null

set -x
#echo 'Clearing Data Folder!'
mkdir ${DATA_DIR} 2> /dev/null
#rm -rf ${DATA_DIR}/*

#Source this again to have a copy of imported envs
source global.conf |& tee $CRAWL_INFO_FILE && python3 scrape_config.py >> $CRAWL_INFO_FILE
source global.conf |& tee $LOG_OUT_FILE

cleanup
##CRAWL COMMANDS!
# Automatic crawler
stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee -a $LOG_OUT_FILE
# Manual crawler
#stdbuf -oL -eL python3 -u ./manual_scraper.py $@ |& tee $LOG_OUT_FILE

cleanup
