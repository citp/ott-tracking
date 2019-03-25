#!/usr/bin/env bash
set -x
DATA_DIR=$1
if [ ! -d "$DATA_DIR" ]; then
  echo "Usage: $0 DataDir"
fi

for file in $DATA_DIR/*.pcap.tcp_streams
do
  head -n +1 "$file" > "$file".uniq
  tail -n +2 "$file" | sort -n -u -t, -k1,1  >> "$file".uniq
done
