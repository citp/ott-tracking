#!/usr/bin/env bash
set -x
DATA_DIR=$1
if [ ! -d "$DATA_DIR" ]; then
  echo "Usage: $0 CRAWL_DATA_DIR"
fi

TMP_DIR="temp"
PCAP_DIR="$1/pcaps"
KEY_DIR="$1/keys"


#MITM attemps (we search for all x509 certs that have mitmproxy in their name)
FILTER="x509sat.uTF8String==mitmproxy"
./extract_fields.sh -w $TMP_DIR -s attemp -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t json -e frame.time_epoch -e ip.src -e ip.dst -e tcp.stream
#All TLS handshake failures
#Full list: https://tools.ietf.org/html/rfc5246#appendix-A.3
FILTER="ssl.alert_message.desc==46 or ssl.alert_message.desc==48"
./extract_fields.sh -w $TMP_DIR -s ssl_fail -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t json  -e frame.time_epoch -e ip.src -e ip.dst -e tcp.stream

