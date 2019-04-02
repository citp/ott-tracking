#!/usr/bin/env bash
set -x
DATA_DIR=$1
TMP_DIR=$DATA_DIR/post-process

if [ ! -d "$TMP_DIR" ] ; then
  mkdir -p $TMP_DIR
fi

if [ ! -d "$DATA_DIR" ] || [ ! -d "$TMP_DIR" ] ; then
  echo "Usage: $0 CRAWL_DATA_DIR"
  exit 1
fi


PCAP_DIR="$1/pcaps"
KEY_DIR="$1/keys"

#List all SSL/TCP streams SYN packets
FORMAT="fields"
FILTER="tcp.flags.syn==1 && tcp.flags.ack==0 && tcp.port ==443"
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
FORMAT="fields"
FILTER="ssl.alert_message.desc==46 or ssl.alert_message.desc==48"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="ssl_fail"
./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

#Post processing of files
./post_process.sh $TMP_DIR

#python3 pcap_analysis.py $DATA_DIR $TMP_DIR
