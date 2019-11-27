#!/usr/bin/env bash
AUDIO_ROOT_DIR=${DATA_DIR}/audio
DETECTION_WINDOW=5
CURRENT_CHANNEL=/tmp/OTT_CURRENT_CHANNEL
CRAWL_FINISHED_FILE="/tmp/CRAWL_FINISHED.txt"
EXTERN_FAIL_PREFIX='/tmp/extern_fail'
#kill existing arecords
pkill -9 arecord

# echo "HOSTNAME".$HOSTNAME
# set the audio HW name for arecord
# http://www.voxforge.org/home/docs/faq/faq/linux-how-to-determine-your-audio-cards-or-usb-mics-maximum-sampling-rate
AUDIO_HW="hw:0,0"


CHANNEL_ID=$(<${CURRENT_CHANNEL})
CH_AUDIO_DIR=${AUDIO_ROOT_DIR}/${CHANNEL_ID}
EXTERN_FAIL_FILE=${EXTERN_FAIL_PREFIX}_${CHANNEL_ID}
errNO=0
mkdir -p ${CH_AUDIO_DIR}
echo "Starting continuous audio capturing to ${CH_AUDIO_DIR}"

while true
do
    if [[ ! -f ${CURRENT_CHANNEL} ]]; then
      echo "Cannot find ${CURRENT_CHANNEL}. Will quit."
      break
    fi

    if [[ -f "${CRAWL_FINISHED_FILE}" ]]; then
        echo "Crawl finished. Will stop capturing audio."
        #remove this later!
        exit 0
    fi


    arecord -N -v -q -t wav -c 2 -f S16_LE -r44100 -d 1 -D $AUDIO_HW --use-strftime ${CH_AUDIO_DIR}/${CHANNEL_ID}_"%Y%m%d-%H%M%S.wav"  >> ${CH_AUDIO_DIR}/${CHANNEL_ID}_arecord.out 2>&1
    if [[ $? -eq 0 ]]; then
      sox $(ls ${CH_AUDIO_DIR}/${CHANNEL_ID}_*-*.wav | sort -n | tail -n ${DETECTION_WINDOW}) ${CH_AUDIO_DIR}/${CHANNEL_ID}_most_recent.wav   >> ${CH_AUDIO_DIR}/${CHANNEL_ID}_sox.out 2>&1
      errNO=0
    else
      #echo `date +"%Y-%m-%d %H:%M:%S"`" arecord error. Will sleep for 1 sec"
      echo "arecord error! "
      errNO=$((errNO+1))
      pkill -9 arecord
      sleep 5
      if [[ "$errNO" -gt "5" ]]; then
          echo "After 5 tries Stopping audio capturing stopped for channel ${CHANNEL_ID}"
          touch $EXTERN_FAIL_FILE
          rm -rf ${CH_AUDIO_DIR}
          exit 1
      fi
    fi
done


echo "Writing combined audio file to ${CH_AUDIO_DIR} for channle ${CHANNEL_ID}"
sox $(ls ${CH_AUDIO_DIR}/${CHANNEL_ID}_*-*.wav) ${CH_AUDIO_DIR}/${CHANNEL_ID}_combined.wav
# rm ${CH_AUDIO_DIR}/${CHANNEL_ID}_*-*.wav
echo "Continuous audio capturing stopped for channel ${CHANNEL_ID}"
exit 0
