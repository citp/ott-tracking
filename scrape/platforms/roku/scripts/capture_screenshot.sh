#!/bin/bash

# Terminate existing ffmpeg captures
pkill -2 -f ffmpeg

# Capture screenshot continuously and write to same file
ffmpeg -loglevel quiet -i /dev/video0 -vf scale=1280:720,fps=1,eq=brightness=-0.1 -r 1 -hide_banner -updatefirst 1 -y ${LogDir}/continuous_screenshot.png &
