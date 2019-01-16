#!/bin/bash
sudo -E iptables -t nat -D PREROUTING -i $WLANIF -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo -E iptables -t nat -D PREROUTING -i $WLANIF -p tcp --dport 443 -j REDIRECT --to-port 8080

sudo -E ip6tables -t nat -D PREROUTING -i $WLANIF -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo -E ip6tables -t nat -D PREROUTING -i $WLANIF -p tcp --dport 443 -j REDIRECT --to-port 8080
