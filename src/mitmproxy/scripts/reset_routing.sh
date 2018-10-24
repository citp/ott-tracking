#!/bin/bash

iptables -F

/etc/init.d/nat-startup.sh
