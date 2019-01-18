#!/bin/bash

source roku.config
#export SSLKEYLOGFILE="./data/keys/SSLKEYLOGFILE.txt" && python3 -u ./scrape_channels.py |& tee output.txt
export LOG_OUT_FILE="output.txt"
export MITMPROXY_SSLKEYLOGFILE="./data/keys/SSLKEYLOGFILE.txt" && stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee $LOG_OUT_FILE