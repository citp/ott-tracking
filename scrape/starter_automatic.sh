#!/usr/bin/env bash

source ./pre_starter.sh

# Automatic crawler
stdbuf -oL -eL python3 -u ./scrape_channels.py $1 |& tee -a $LOG_OUT_FILE

cleanup
