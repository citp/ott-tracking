#!/bin/bash
sudo -E iptables -t nat -D PREROUTING -i $WLANIF -s $TV_IP_ADDR -p tcp --dport 80 -j REDIRECT --to-port ${MITMPROXY_PORT_NO} 2> /dev/null
sudo -E iptables -t nat -D PREROUTING -i $WLANIF -s $TV_IP_ADDR -p tcp --dport 443 -j REDIRECT --to-port ${MITMPROXY_PORT_NO} 2> /dev/null

sudo -E ip6tables -t nat -D PREROUTING -i $WLANIF -s $TV_IP_ADDR -p tcp --dport 80 -j REDIRECT --to-port ${MITMPROXY_PORT_NO} 2> /dev/null
sudo -E ip6tables -t nat -D PREROUTING -i $WLANIF -s $TV_IP_ADDR -p tcp --dport 443 -j REDIRECT --to-port ${MITMPROXY_PORT_NO} 2> /dev/null
