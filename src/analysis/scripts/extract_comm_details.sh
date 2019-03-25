#!/usr/bin/env bash
set -x
DATA_DIR=$1
if [ ! -d "$DATA_DIR" ]; then
  echo "Usage: $0 CRAWL_DATA_DIR"
fi

TMP_DIR="temp"
PCAP_DIR="$1/pcaps"
KEY_DIR="$1/keys"

#List all TCP streams
#Call post_process.sh to find the first time epoch
FORMAT="fields"
FILTER="tcp and ssl"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="tcp_streams"
./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

#MITM attemps (we search for all x509 certs that have mitmproxy in their name)
FORMAT="fields"
FILTER="x509sat.uTF8String==mitmproxy"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="mitmproxy-attemp"
./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

#All TLS handshake failures
#Full list: https://tools.ietf.org/html/rfc5246#appendix-A.3
FORMAT="json"
FILTER="ssl.alert_message.desc==46 or ssl.alert_message.desc==48"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="ssl_fail"
./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

#Post processing of files
./post_process.sh $TMP_DIR
