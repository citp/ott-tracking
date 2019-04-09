#!/usr/bin/env bash
set -x
DATA_DIR=`realpath $1`
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
LOG_DIR="$1/logs"

TV_IP_ADDR=`grep -r "TV_IP_ADDR" $LOG_DIR/*.log | head -n1 | awk '{print $3}' |  awk -F'[=]' '{print $2}'`
TV_TCP_PORT=8060

####################################
######HTTP HEADER/URL ANALYSIS######
####################################

####TODO: We need to filter out TV interface packets
#### FILTER out src IP = TV_IP and src port = 80
#### AND dst IP = TV_IP and dst port = 80
FILTER="http and not ((ip.src == $TV_IP_ADDR && tcp.srcport == $TV_TCP_PORT) || (ip.dst == $TV_IP_ADDR && tcp.dstport == $TV_TCP_PORT))"
FORMAT="fields"
SUFFIX="csv"
FIELDS="-e eth.src -e ip.dst -e http.request.method -e http.request.full_uri"
./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT -r "|" $FIELDS

####################################
#######TLS INTERCEPT ANALYSIS#######
####################################
#List all SSL/TCP streams SYN packets
FORMAT="fields"
FILTER="tcp.flags.syn==1 && tcp.flags.ack==0 && tcp.port ==443"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="tcp_streams"
#./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

#MITM attemps (we search for all x509 certs that have mitmproxy in their name)
FORMAT="fields"
FILTER="x509sat.uTF8String==mitmproxy"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="mitmproxy-attemp"
#./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

#All TLS handshake failures
#Full list: https://tools.ietf.org/html/rfc5246#appendix-A.3
FORMAT="fields"
FILTER="ssl.alert_message.desc==46 or ssl.alert_message.desc==48"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="ssl_fail"
#./extract_fields.sh -w $TMP_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

#Post processing of files
#./post_process.sh $TMP_DIR

#python3 pcap_analysis.py $DATA_DIR $TMP_DIR
