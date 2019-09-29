#!/bin/bash
# Terminate existing ffmpeg captures
touch /tmp/SMART_TV_KILL_SCREENSHOT
pkill -9 -f ffmpeg
sleep 2s
rm /tmp/SMART_TV_KILL_SCREENSHOT

# Capture screenshot continuously and write to same file
mkdir -p ${SCREENSHOT_FOLDER} 2> /dev/null
ScreenshotFile="${SCREENSHOT_FOLDER}/continuous_screenshot-%Y-%m-%d_%H-%M-%S.png"
ScreenshotLogFile=${SCREENSHOT_FOLDER}/continuous_screenshot.log

# Remove previous screenshot files
rm ${SCREENSHOT_FOLDER}/continuous_screenshot-*.png

set -x
while true
do
    echo "Continuous screenshot capturing to ${ScreenshotFile}"
    ffmpeg -nostdin -loglevel quiet -i /dev/video0 -vf scale=1280:720,fps=1,eq=brightness=-0.1 -r 1 -hide_banner -f image2 -strftime 1 "$ScreenshotFile" 
    if [ -f /tmp/SMART_TV_KILL_SCREENSHOT ]
    then
      exit 0
    fi
    if ! pgrep  "starter.sh" > /dev/null
    then
        echo "Crawl finished. Will stop capturing screenshots."
        exit 0
    fi
    echo "Screenshot script stopped!"
    echo "Retrying in 2 seconds"
    sleep 2s
done

echo "Screenshot script terminating! If your crawl is ongoing this might mean that the FFMPEG returned with error!"
echo "Check ffmpeg command output for more detail!!"
