#!/bin/bash

echo "# Packages on Amazon Fire Cube when you first start it (without installing additional packages." > base_packages.txt
adb shell pm list packages -f >> base_packages.txt
