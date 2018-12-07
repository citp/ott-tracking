#!/bin/bash
# Recommended for allowing non-root users to run tcpdump:
# https://askubuntu.com/questions/530920/tcpdump-permissions-problem
#tcpdump -v -w "$1".pcap -i wlan0 host $TV_IP_ADDR and not arp

ETH_MAC_ADDRESS="b8:27:eb:a2:f4:10"
tcpdump -v -w "$1".pcap -i eth0 ether host $ETH_MAC_ADDRESS and not arp

