#!/bin/bash

mitmproxy -T --host -s tls_passthrough.py -s mitmproxy-sslstrip.py --follow -w flows.out --cert *=/home/pi/.mitmproxy/cert.pem
