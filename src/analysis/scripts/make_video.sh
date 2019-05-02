#!/usr/bin/env bash
DATA_DIR=`realpath $1`
OUT_DIR=$DATA_DIR/post-process
IMG_DIR=$DATA_DIR/screenshots
CRAWLNAME=$(basename "$1")
FPS=15
echo "Output file: "$OUT_DIR/slide_show_${CRAWLNAME}_${FPS}_fps.mp4
ffmpeg -framerate $FPS -pattern_type glob -i $IMG_DIR/'*.png' -c:v libx264 -pix_fmt yuv420p $OUT_DIR/slide_show_${CRAWLNAME}_${FPS}_fps.mp4
