#!/usr/bin/env bash
AUDIO_ROOT_DIR=${DATA_DIR}/audio
DETECTION_WINDOW=5
CURRENT_CHANNEL=/tmp/OTT_CURRENT_CHANNEL

echo "HOSTNAME".$HOSTNAME
# set the audio HW name for arecord
# http://www.voxforge.org/home/docs/faq/faq/linux-how-to-determine-your-audio-cards-or-usb-mics-maximum-sampling-rate
if [ "$HOSTNAME" = "miyav" ]; then
  AUDIO_HW="hw:0,0"
elif [ "$HOSTNAME" = "torro" ]; then
  AUDIO_HW="hw:2,0"
else
  echo "I don't know about this machine. Please update this script"
  exit 1
fi


while true
do
    if [ ! -f ${CURRENT_CHANNEL} ]; then
      echo "Cannot find ${CURRENT_CHANNEL}. Will quit."
      break
    fi

    if ! pgrep  "starter.sh" > /dev/null
    then
        echo "Crawl finished. Will stop capturing audio."
        exit 0
    fi
    CHANNEL_ID=$(<${CURRENT_CHANNEL})
    CH_AUDIO_DIR=${AUDIO_ROOT_DIR}/${CHANNEL_ID}
    # echo "Continuous audio capturing to ${CH_AUDIO_DIR}"

    arecord -q -t wav -c 2 -f S16_LE -r44100 -d 1 -D $AUDIO_HW --use-strftime ${CH_AUDIO_DIR}/${CHANNEL_ID}_"%Y%m%d-%H%M%S.wav"  >> /tmp/${CHANNEL_ID}_arecord.out 2>&1
    sox $(ls ${CH_AUDIO_DIR}/${CHANNEL_ID}_*-*.wav | sort -n | tail -n ${DETECTION_WINDOW}) ${CH_AUDIO_DIR}/${CHANNEL_ID}_most_recent.wav   >> /tmp/${CHANNEL_ID}_sox.out 2>&1
done

sox $(ls ${CH_AUDIO_DIR}/${CHANNEL_ID}_*-*.wav) ${CH_AUDIO_DIR}/${CHANNEL_ID}_combined.wav
rm ${CH_AUDIO_DIR}/${CHANNEL_ID}_*-*.wav
echo "Continuous audio capturing stopped."
exit 0