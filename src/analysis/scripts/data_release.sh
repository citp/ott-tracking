#!/usr/bin/env bash
# set -x
#
# Extract fields from pcaps and write to separate files.
#
# Usage:
#
#   data_release.sh data_dir
#
DATA_DIR=`realpath $1`
PCAP_DIR="${DATA_DIR}/pcaps"
KEY_DIR="${DATA_DIR}/keys"

OUT_DIR="${DATA_DIR}/data-release"
mkdir -p ${OUT_DIR} 2> /dev/null

#cp ${DATA_DIR}/crawl_info-*.txt ${OUT_DIR}

TV_IP_ADDR=`grep "TV_IP_ADDR" ${DATA_DIR}/crawl_info-*.txt | head -n1 | awk '{print $3}' |  awk -F'[=]' '{print $2}'`
TV_TCP_PORT=8060

FILTER="http.request and not ((ip.src == ${TV_IP_ADDR} && tcp.srcport == ${TV_TCP_PORT}) || (ip.dst == ${TV_IP_ADDR} && tcp.dstport == ${TV_TCP_PORT}))"
FORMAT="ek"
SUFFIX="http.json"
FIELDS="-e frame.time_epoch -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e http.request.method -e http.request.full_uri -e http.file_data"
./extract_fields.sh -w ${OUT_DIR} -s ${SUFFIX} -i ${PCAP_DIR} -o ${KEY_DIR} -f ${FILTER} -t ${FORMAT} ${FIELDS}

FILTER="dns"
SUFFIX="dns.json"
FIELDS="-e frame.time_epoch -e dns.qry.name -e dns.a -e dns.aaaa"
./extract_fields.sh -w ${OUT_DIR} -s ${SUFFIX} -i ${PCAP_DIR} -o ${KEY_DIR} -f ${FILTER} -t ${FORMAT} ${FIELDS}
