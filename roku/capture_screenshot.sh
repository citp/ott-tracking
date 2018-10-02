#!/bin/bash

fswebcam -d /dev/video0 -r 1280x720 --no-banner -F 5 --png --save screenshots/$1.png
