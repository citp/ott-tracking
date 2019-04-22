#!/usr/bin/env bash
set -x
DATA_DIR=`realpath $1`
OUT_DIR=$DATA_DIR/post-process

if [ ! -d "$OUT_DIR" ] ; then
  mkdir -p $OUT_DIR
fi

if [ ! -d "$DATA_DIR" ] || [ ! -d "$OUT_DIR" ] ; then
  echo "Usage: $0 CRAWL_DATA_DIR"
  exit 1
fi

PCAP_DIR="$1/pcaps"
KEY_DIR="$1/keys"
LOG_DIR="$1/logs"

#TV_IP_ADDR=`grep "TV_IP_ADDR" $LOG_DIR/*.log | head -n1 | awk '{print $3}' |  awk -F'[=]' '{print $2}'`
TV_IP_ADDR=`grep "TV_IP_ADDR" $DATA_DIR/crawl_info-*.txt | head -n1 | awk '{print $3}' |  awk -F'[=]' '{print $2}'`
TV_TCP_PORT=8060

####################################################
###### HTTP RESPONSE ANALYSIS (for SSL Strip) ######
####################################################
FILTER="http.response and not ((ip.src == $TV_IP_ADDR && tcp.srcport == $TV_TCP_PORT) || (ip.dst == $TV_IP_ADDR && tcp.dstport == $TV_TCP_PORT))"
FORMAT="fields"
SUFFIX="http_response.csv"
FIELDS="-e frame.time_epoch -e eth.src -e ip.dst -e http.response.code"
./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT -r "|" $FIELDS

