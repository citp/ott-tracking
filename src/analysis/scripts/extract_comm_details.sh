#!/usr/bin/env bash
set -x
DATA_DIR=$1
if [ ! -d "$DATA_DIR" ]; then
  echo "Usage: $0 CRAWL_DATA_DIR"
fi

PCAP_DIR="$1/pcaps"
KEY_DIR="$1/keys"


#All TLS handshake failures
FILTER="x509sat.uTF8String == \"mitmproxy\""
./extract_fields.sh -w temp -s attemp -i $PCAP_DIR -o $KEY_DIR -f $FILTER  -e frame.time_epoch -e ip.dst
FILTER="ssl and ssl.alert_message.desc==48"
./extract_fields.sh -w temp -s ssl_fail -i $PCAP_DIR -o $KEY_DIR -f $FILTER  -e frame.time_epoch -e ip.dst