#!/usr/bin/env bash
# set -x  # uncomment to debug
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
IMG_DIR="$1/screenshots"
LOG_DIR="$1/logs"


# Run OCR detection
python3 ../../imagetextparser/cloudvisiontextparser.py $IMG_DIR $OUT_DIR 4

#TV_IP_ADDR=`grep "TV_IP_ADDR" $LOG_DIR/*.log | head -n1 | awk '{print $3}' |  awk -F'[=]' '{print $2}'`
TV_IP_ADDR=`grep "TV_IP_ADDR" $DATA_DIR/crawl_info-*.txt | head -n1 | awk '{print $3}' |  awk -F'[=]' '{print $2}'`
TV_TCP_PORT=8060

######################################
###### HTTP HEADER/URL/POST ANALYSIS ######
######################################
FILTER="tcp.payload and not ((ip.src == $TV_IP_ADDR && tcp.srcport == $TV_TCP_PORT) || (ip.dst == $TV_IP_ADDR && tcp.dstport == $TV_TCP_PORT))"
FORMAT="json"
SUFFIX="http.json"
FIELDS="-e tcp.stream -e frame.time_epoch -e eth.src -e ip.dst -e tcp.dstport  -e ip.src -e tcp.srcport -e http.host -e http.request.method -e http.request.full_uri -e http.user_agent -e http.referer -e http.cookie -e http.set_cookie -e http.response.code -e http.location -e http.file_data -e data"
./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT -r "|" $FIELDS
python correct_http_pipelining.py $OUT_DIR

######################################
###### HTTP2 HEADER/URL/POST ANALYSIS ######
######################################
FILTER="tcp.payload and not ((ip.src==$TV_IP_ADDR&&tcp.srcport==$TV_TCP_PORT)||(ip.dst==$TV_IP_ADDR&&tcp.dstport==$TV_TCP_PORT))"
FORMAT="json"
SUFFIX="http2.json"
FIELDS="-e tcp.stream -e frame.time_epoch -e eth.src -e ip.dst -e tcp.dstport -e ip.src -e tcp.srcport -e http2.type -e http2.header.name -e http2.header.value -e http2.data.data"
./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT -r "|" $FIELDS


####################################
######HTTP POST ANALYSIS######
####################################
# FILTER="http.request and http.content_length>0 and not ((ip.src == $TV_IP_ADDR && tcp.srcport == $TV_TCP_PORT) || (ip.dst == $TV_IP_ADDR && tcp.dstport == $TV_TCP_PORT))"
# FORMAT="json"
# SUFFIX="post.csv"
# FIELDS="-e frame.time_epoch -e eth.src -e ip.dst -e tcp.dstport -e http.request.method -e http.request.full_uri -e http.user_agent -e http.referer -e http.cookie -e http.file_data"
# ./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT -r "|" $FIELDS


####################################
#######TLS INTERCEPT ANALYSIS#######
####################################
# List all SSL/TCP streams SYN packets
# FORMAT="fields"
# FILTER="tcp.flags.syn==1 && tcp.flags.ack==0 && tcp.port ==443"
# FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
# SUFFIX="tcp_streams"
# ./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS


####################################
#######TCP CONNECTION ANALYSIS#######
####################################
# List all TCP streams with SYN packets
FORMAT="fields"
FILTER="tcp.flags.syn==1 and tcp.flags.ack==0 and not ((ip.src == $TV_IP_ADDR && tcp.srcport == $TV_TCP_PORT) || (ip.dst == $TV_IP_ADDR && tcp.dstport == $TV_TCP_PORT))"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst -e tcp.dstport"
SUFFIX="tcp_streams"
./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS

######################################
###### MITM Attempts ######
######################################
# MITM attemps (we search for all x509 certs that have mitmproxy in their name)
FORMAT="fields"
FILTER="x509sat.uTF8String==mitmproxy"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
SUFFIX="mitmproxy-attempt"
./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS


# We don't use handshake failures as a proxy for SSL failures anymore.
#All TLS handshake failures
#Full list: https://tools.ietf.org/html/rfc5246#appendix-A.3
# FORMAT="fields"
# FILTER="ssl.alert_message.desc==46 or ssl.alert_message.desc==48"
# FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
# SUFFIX="ssl_fail"
# ./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS


########################################
###### Successful SSL connections ######
########################################
# All TLS streams with client sending at least some data.
# To prevent overcounting, we expect there to be some SSL data communication
# from the client side.
# In some cases, immediately after the handshake, the client sends a FIN to terminate the
# connection.
# FORMAT="fields"
# FILTER="ssl and ((ssl.record.content_type == 23) && (ip.src==$TV_IP_ADDR))"
# FIELDS="-e tcp.stream -e frame.time_epoch -e ip.src -e ip.dst"
# SUFFIX="ssl_success"
# ./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT $FIELDS


##################################################################
###### SSL Client handshakes and Successful SSL connections ######
##################################################################
# TODO: this CSV will contain 2 types of SSL frames. Filter in pandas using ssl.record.content_type
# 1- TLS streams with client sending at least some data: (filter: ssl.record.content_type == 23)
# 2- TLS client handshakes: (filter: ssl.record.content_type == 22)
FORMAT="fields"
FILTER="((ssl.handshake.type == 1) || (ssl.record.content_type == 23)) && (ip.src==$TV_IP_ADDR)"
FIELDS="-e tcp.stream -e frame.time_epoch -e ip.dst -e ssl.record.content_type -e ssl.handshake.extensions_server_name"
SUFFIX="ssl_connections"
./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT -r "|" $FIELDS



########################################################
###### DNS responses (A and AAAA) ######
########################################################
FORMAT="fields"
FILTER="((dns.flags.response==1) && (ip.dst==$TV_IP_ADDR))"
FIELDS="-e frame.time_epoch -e ip.src -e dns.qry.name -e dns.a -e dns.aaaa"
SUFFIX="dns.csv"
./extract_fields.sh -w $OUT_DIR -s $SUFFIX -i $PCAP_DIR -o $KEY_DIR -f $FILTER -t $FORMAT -r "|" $FIELDS

