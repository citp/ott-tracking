#!/bin/bash

export TV_IP_ADDR=172.24.1.135
export SSLKEYLOGFILE="./data/keys/SSLKEYLOGFILE.txt" && python3 -u ./scrape_channels.py |& tee output.txt