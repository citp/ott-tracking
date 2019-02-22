#!/bin/bash

rm ${LogDir}/adb.log 2> /dev/null
adb logcat *:D  >  ${LogDir}/adb.log
