#!/bin/bash

sudo tcpdump -v -w pcaps/"$1".pcap host 10.0.0.13 and not arp and ether src b8:27:eb:63:ef:53
