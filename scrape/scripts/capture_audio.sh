#!/usr/bin/env bash
AUDIO_ROOT_DIR=${DATA_DIR}/audio
DETECTION_WINDOW=5
CURRENT_CHANNEL=/tmp/OTT_CURRENT_CHANNEL


while true
do
    if [ ! -f ${CURRENT_CHANNEL} ]; then
      echo "Cannot find ${CURRENT_CHANNEL}. Will quit."
      exit 0
    fi

    CHANNEL_ID=$(<${CURRENT_CHANNEL})
    CH_AUDIO_DIR=${AUDIO_ROOT_DIR}/${CHANNEL_ID}
    echo "Continuous audio capturing to ${CH_AUDIO_DIR}"

    arecord -t wav -c 2 -f S16_LE -r44100 -d 1 --use-strftime ${CH_AUDIO_DIR}/${CHANNEL_ID}_"%Y%m%d-%H%M%S.wav"
    sox $(ls ${CH_AUDIO_DIR}/${CHANNEL_ID}_*-*.wav | sort -n | tail -n ${DETECTION_WINDOW}) ${CH_AUDIO_DIR}/${CHANNEL_ID}_most_recent.wav
done

echo "Continuous audio capturing stopped."