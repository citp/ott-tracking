#!/bin/bash

sudo -E sysctl -w net.ipv4.ip_forward=1
sudo -E sysctl -w net.ipv6.conf.all.forwarding=1
sudo -E sysctl -w net.ipv4.conf.all.send_redirects=0

sudo -E iptables -t nat -A PREROUTING -i $WLANIF -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo -E iptables -t nat -A PREROUTING -i $WLANIF -p tcp --dport 443 -j REDIRECT --to-port 8080

sudo -E ip6tables -t nat -A PREROUTING -i $WLANIF -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo -E ip6tables -t nat -A PREROUTING -i $WLANIF -p tcp --dport 443 -j REDIRECT --to-port 8080

