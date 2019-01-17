#!/bin/bash

sudo -E fswebcam -d /dev/video0 -r 1280x720 --no-banner -F 5 --png --save $1
