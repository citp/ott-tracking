#!/bin/bash
# Recommended for allowing non-root users to run tcpdump:
# https://askubuntu.com/questions/530920/tcpdump-permissions-problem
sudo -E tcpdump -v -w "$1".pcap -i ${LANIF} ether host $ETH_MAC_ADDRESS and not arp and port not ssh

