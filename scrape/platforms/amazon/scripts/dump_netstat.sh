#!/usr/bin/python3
"""
Continuously dumps output from netstat3 to find:

which app (apk_id) makes what connections

To terminate, do `pkill -2 -f dump_netstat.sh`.

"""
import subprocess as sp
import time
import re
import json
import threading
import sys
from datetime import datetime
from os.path import join


def main(save_path):
    date_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")

    netstat_file_path = join(save_path, 'netstat_%s.txt' % date_prefix)
    print("Writing netstat to %s" % netstat_file_path)

    netstat_fp = open(netstat_file_path, 'w')

    th = threading.Thread(target=dump_netstat_thread, args=(netstat_fp, ))
    th.daemon = True
    th.start()

    # Block forever until being killed
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        pass

    netstat_fp.close()


def dump_netstat_thread(fp):

    while True:
        dump_netstat(fp)
        time.sleep(0.2)


def dump_netstat(fp):
    """
    Writes to file a json object of 'ts' (timestamp) and 'netstat_output',
    where 'netstat_output' is simply the result of adb shell netstat -peanutW

    """
    # netstat on some Fire TVs does not display process/user IDs
    # We install netstat3 on Fire TVs we want to test:
    #####################################
    # netstat3 Installation instructions:
    #####################################
    # Download netstat3 binary from: https://github.com/LipiLee/netstat/raw/master/netstat3
    # chmod +x netstat3
    # adb push netstat3 /data/local/tmp
    # Test: adb shell /data/local/tmp/netstat3

    # Run netstat3
    cmd = 'adb shell /data/local/tmp/netstat3'
    pobj = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    netstat_output = pobj.communicate()[0].decode("utf-8").splitlines()
    ts = time.time()

    # Write to file
    print(json.dumps({
        'ts': ts,
        'netstat_output': netstat_output
    }), file=fp)


if __name__ == '__main__':
    main(sys.argv[1])
