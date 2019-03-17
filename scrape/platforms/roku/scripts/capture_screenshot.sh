#!/bin/bash

# Terminate existing ffmpeg captures
pkill -2 -f ffmpeg

# Capture screenshot continuously and write to same file
ScreenshotFile=${LogDir}/continuous_screenshot.png
ScreenshotLogFile=${LogDir}/continuous_screenshot.log

while true
do
    echo "Continuous screenshot capturing to ${ScreenshotFile}"
    ffmpeg -i /dev/video0 -vf scale=1280:720,fps=1,eq=brightness=-0.1 -r 1 -hide_banner -updatefirst 1 -y $ScreenshotFile >> $ScreenshotLogFile 2>&1
    echo "Screenshot script stopped!"
    echo "Retrying in 2 seconds"
    sleep 2s
done

echo "Screenshot script terminating! If your crawl is ongoing this might mean that the FFMPEG returned with error!"
echo "Check ffmpeg command output for more detail!!"
