#!/bin/bash
sudo -E iptables -t nat -A PREROUTING -i $WLANIF -s $TV_IP_ADDR -p tcp --dport 80 -j REDIRECT --to-port ${MITMPROXY_PORT_NO}
sudo -E iptables -t nat -A PREROUTING -i $WLANIF -s $TV_IP_ADDR -p tcp --dport 443 -j REDIRECT --to-port ${MITMPROXY_PORT_NO}

#sudo -E ip6tables -t nat -A PREROUTING -i $WLANIF -p tcp --dport 80 -j REDIRECT --to-port ${MITMPROXY_PORT_NO}
#sudo -E ip6tables -t nat -A PREROUTING -i $WLANIF -p tcp --dport 443 -j REDIRECT --to-port ${MITMPROXY_PORT_NO}

