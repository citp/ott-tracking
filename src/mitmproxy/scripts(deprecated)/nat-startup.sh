#!/bin/sh

### BEGIN INIT INFO
# Provides:          nat-startup
# Required-Start:    $local_fs $network
# Required-Stop:     $local_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: nat-startup
# Description:       ip-tables NAT startup script
### END INIT INFO

iptables-restore /etc/iptables.ipv4.nat
service dnsmasq restart

