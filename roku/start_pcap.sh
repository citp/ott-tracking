#!/bin/bash
# Recommended for allowing non-root users to run tcpdump:
# https://askubuntu.com/questions/530920/tcpdump-permissions-problem
#tcpdump -v -w "$1".pcap -i wlan0 host $TV_IP_ADDR and not arp
tcpdump -v -w "$1".pcap -i any not arp

