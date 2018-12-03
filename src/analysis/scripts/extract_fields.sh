#!/usr/bin/env bash
#
# Extract requested fields from pcaps and write to separate files.
#
# Usage:
#
#   extract_fields.sh -i /path/to/pcaps [-f filter] -e field1 -e field2 ... -e fieldN
#
# Extract all destination IP addresses
#   extract_fields.sh -i /path/to/pcaps -e eth.src -e ip.dst
#
# HTTP Request hosts and methods
#   extract_fields.sh -i /path/to/pcaps -f http.request -e eth.src -e ip.dst -e http.request.method -e http.host
#
# SSL SNI
#   extract_fields.sh -i /path/to/pcaps -f ssl.handshake.extensions_server_name -e eth.src -e ip.dst -e ssl.handshake.extensions_server_name
#
#
# SSL ciphersuites
#   extract_fields.sh -i /path/to/pcaps -f ssl.handshake.type==1 -e eth.src -e ssl.handshake.ciphersuite -e ip.dst -e ssl.handshake.extensions_server_name
#
# Used Protocols
#   extract_fields.sh -i /path/to/pcaps -f udp -e eth.src -e frame.protocols
#
# Geolocation (and pretty much everything)
#   extract_fields.sh /path/to/pcaps -e eth.src -e ip.proto -e ip.dst -e frame.protocols -e tcp.dstport -e udp.dstport -e http.request.method -e http.host -e ssl.handshake.extensions_server_name -e ip.geoip.dst_country -e ip.geoip.dst_city -e ip.geoip.dst_asnum -e ip.geoip.dst_lat -e ip.geoip.dst_lon
#
# Inspired by the command at:
# https://docs.google.com/document/d/12w11tJux344TZe3wLajzCD6D3BJJVZEYMMePgLvZSPg/edit#


FILTER="eth"  # do not filter out any packets by default
FORMAT="fields"  # output format, CSV by default. -T in tshark

usage()
{
    echo "Usage: extract_fields.sh -i /path/to/pcaps [-f filter] [-t format] -e field1 -e field2 ... -e fieldN"
}

while [ "$1" != "" ]; do
    case $1 in
         # directory that contains the pcaps
        -i | --input_dir )      shift
                                PCAP_DIR=$1
                                ;;
		# packet filter, optional
        -f | --filter )         shift
                                FILTER=$1
                                ;;
		# output format, optional
        -t | --format )         shift
                                FORMAT=$1
                                ;;
        # use SSLKEYLOGFOLDER to decrypt traffic
		-o | --sslkeydir)
                                shift
                                SSLKEYLOGFOLDER=$1
                                ;;
        # list of fields to be extracted
        -e )
                                FIELDS=$@
                                break
                                ;;
    esac
    shift
done


#echo "DEBUG" $PCAP_DIR $FILTER $FIELDS;

# create a temp dir to store intermediate files
OUTDIR=$(mktemp -d pcap_extract_fields.XXXXXXXXX)
mkdir -p $OUTDIR
MAX_PROCESS=8
i=0
for f in $PCAP_DIR/*.pcap; do
  basename=$(basename "$f")
  channelid=`echo $basename | awk -F'[-]' '{print $1}'`

  SSLKEYOPTION=""
  # We assume that each SSLKEYLOGFILE is like 1234.txt
  SSLKEYFILE=${SSLKEYLOGFOLDER}/`ls $SSLKEYLOGFOLDER | grep "^${channelid}\.txt"`
  [[ ! -z "${SSLKEYLOGFOLDER}" ]] && SSLKEYOPTION="-o ssl.keylog_file:'${SSLKEYFILE}'"

  tshark -r $f $SSLKEYOPTION -E separator="|" -T $FORMAT $FIELDS -Y "$FILTER" | uniq > $OUTDIR/$basename.txt &
  #sleep 0.05;
  n_running+=1
  ((i=i%MAX_PROCESS)); ((i++==0)) && wait

done
wait

echo "Output in $OUTDIR" 


