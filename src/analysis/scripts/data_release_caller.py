#!/usr/bin/python3
import subprocess
import sys
from os.path import abspath

crawl_dictionary={
    "Roku-Top1K-NoMITM" : "roku-data-20190508-013650",
    "Roku-Top1K-MITM": "roku-data-20190524-202541",
    "Roku-CategoriesTop100-MITM": "roku-data-20190503-120644",
    "Roku-CategoriesTop100-LimitAdTracking": "roku-data-20190505-165349",
    "Roku-Top30-Manual-MITM": "roku_manual_v2",
    "FireTV-Top1K-NoMITM": "amazon-data-20190510-205355",
    "FireTV-Top1K-MITM": "amazon-data-20190509-133243",
    "FireTV-CategoriesTop100-MITM": "amazon-data-20190510-185732",
    "FireTV-CategoriesTop100-DisableInterestAds": "amazon-data-20190512-092528",
    "FireTV-Top30-Manual-MITM": "amazon_manual_v2"
}

if __name__ == '__main__':
    crawl_base_dir = sys.argv[1]
    release_base_dir = sys.argv[2]

    print("Creating release files for crawl dir: %s" % crawl_base_dir)
    print("Output dir: %s" % release_base_dir)

    for crawl in crawl_dictionary:
        crawl_dir = abspath(crawl_base_dir + "/" + crawl_dictionary[crawl])
        release_dir = abspath(release_base_dir) + "/" + crawl
        command = './data_release.sh %s %s' %(crawl_dir, release_dir)
        print(command)
        subprocess.call(command, shell=True)