#!/bin/bash

sudo tcpdump -v -w pcaps/$1.pcap host 172.24.1.239 and not arp 

