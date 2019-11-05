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

if [[ -z "$2" ]];then
    echo "No out dir given, using default"
    OUT_DIR="${DATA_DIR}/data-release"
else
    OUT_DIR=$2
fi


mkdir -p ${OUT_DIR} 2> /dev/null

OUT_DIR_HTTP=${OUT_DIR}/http
mkdir -p ${OUT_DIR_HTTP} 2> /dev/null

OUT_DIR_DNS=${OUT_DIR}/dns
mkdir -p ${OUT_DIR_DNS} 2> /dev/null

# Copy crawl status
OUT_DIR_STATUS=${OUT_DIR}/stat
mkdir -p ${OUT_DIR_STATUS} 2> /dev/null
cp ${DATA_DIR}/finished/* ${OUT_DIR_STATUS}/

# Copy crawl timestamps
OUT_DIR_TIMESTAMP=${OUT_DIR}/timestamp
mkdir -p ${OUT_DIR_TIMESTAMP} 2> /dev/null
cp ${DATA_DIR}/logs/*-timestamps.txt ${OUT_DIR_TIMESTAMP}/

#Get TV IP address and Web interface port
TV_IP_ADDR=`grep "TV_IP_ADDR" ${DATA_DIR}/crawl_info-*.txt | head -n1 | awk '{print $3}' |  awk -F'[=]' '{print $2}'`
TV_TCP_PORT=8060

#Get all HTTP requests except those for TV's Web interface
FILTER="http.request and not ((ip.src == ${TV_IP_ADDR} && tcp.srcport == ${TV_TCP_PORT}) || (ip.dst == ${TV_IP_ADDR} \
&& tcp.dstport == ${TV_TCP_PORT}))"
FORMAT="json"
SUFFIX="http.json"
FIELDS="-e frame.time_epoch -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e http.request.method \
-e http.request.full_uri -e http.file_data"
../extract_fields.sh -w ${OUT_DIR_HTTP} -s ${SUFFIX} -i ${PCAP_DIR} -o ${KEY_DIR} -f ${FILTER} -t ${FORMAT} ${FIELDS}

#Get all DNS requests and responses
FILTER="dns"
SUFFIX="dns.json"
FIELDS="-e frame.time_epoch -e dns.qry.name -e dns.a -e dns.aaaa"
../extract_fields.sh -w ${OUT_DIR_DNS} -s ${SUFFIX} -i ${PCAP_DIR} -o ${KEY_DIR} -f ${FILTER} -t ${FORMAT} ${FIELDS}

#Create the crawl info file
CRAWL_INFO_FILE="${OUT_DIR}/crawl_info.txt"
echo "" > ${CRAWL_INFO_FILE}

#Extract necessary fields
SearchTerms="ENABLE_SMART_CRAWLER MITMABLE_DOMAINS_WARM_UP_CRAWL TLS_INTERCEPT SSL_STRIP MITMPROXY_ENABLED \
LAUNCH_RETRY_CNT SMART_CRAWLS_CNT TV_IP_ADDR"

# Iterate the string variable using for loop
for val in ${SearchTerms}; do
    grep -h "'${val}'" ${DATA_DIR}/crawl_info-*.txt | uniq >> ${CRAWL_INFO_FILE}
done
