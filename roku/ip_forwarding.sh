#!/bin/bash

sudo -E sysctl -w net.ipv4.ip_forward=1
sudo -E sysctl -w net.ipv6.conf.all.forwarding=1
sudo -E sysctl -w net.ipv4.conf.all.send_redirects=0