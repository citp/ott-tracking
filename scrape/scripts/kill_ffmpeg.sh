#!/bin/bash
set -x
killall ffmpeg
touch /tmp/SMART_TV_KILL_SCREENSHOT
sleep 3
rm /tmp/SMART_TV_KILL_SCREENSHOT
