#!/bin/bash
# Recommended for allowing non-root users to run tcpdump:
# https://askubuntu.com/questions/530920/tcpdump-permissions-problem
tcpdump -v -w "$1".pcap -i wlan0 host 172.24.1.97 and not arp

