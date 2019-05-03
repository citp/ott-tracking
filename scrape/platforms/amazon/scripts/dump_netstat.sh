#!/usr/bin/python3
"""
Continously dumps output from netstat and dumpsys to find:

1. which process (user_id) makes what connections
2. which app corresponds to which user_id

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

    dumpsys_file_path = join(save_path, 'dumpsys_%s.txt' % date_prefix)
    print("Writing dumpsys to %s" % dumpsys_file_path)

    netstat_fp = open(netstat_file_path, 'w')
    dumpsys_fp = open(dumpsys_file_path, 'w')

    th = threading.Thread(target=dump_netstat_thread, args=(netstat_fp, ))
    th.daemon = True
    th.start()

    th = threading.Thread(
        target=dump_channel_user_ids_thread, args=(dumpsys_fp, )
    )
    th.daemon = True
    th.start()

    # Block forever until being killed
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        pass

    netstat_fp.close()
    dumpsys_fp.close()


def dump_netstat_thread(fp):

    while True:
        dump_netstat(fp)
        time.sleep(0.5)


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


def dump_channel_user_ids_thread(fp):

    while True:
        dump_channel_user_ids(fp)
        time.sleep(15)


def dump_channel_user_ids(fp):
    """
    Writes to file a json object of 'ts' (timestamp) and 'package_dict', where
    'package_dict' maps package_id to user_id.

    """
    # Maps package_id -> user_id
    package_dict = {}

    package_id = None
    user_id = None

    # Parse adb output
    cmd = 'adb shell dumpsys package | grep -B 1 userId'
    pobj = sp.Popen(cmd, shell=True, stdout=sp.PIPE)
    result = pobj.communicate()[0].decode("utf-8")
    ts = time.time()

    for line in result.split('\n'):

        # Look for lines that look like:
        #   Package [com.android.providers.calendar] (5337185):
        match = re.search(r'\[(.+)\]', line)
        if match:
            package_id = match.group(1)
            user_id = None

        # Look for lines that look like:
        #     userId=10006
        if package_id:
            match = re.search(r'userId=(\d+)', line)
            if match:
                user_id = match.group(1)

        if package_id and user_id:
            package_dict[package_id] = user_id
            package_id = None
            user_id = None

    # Write to file
    print(json.dumps({
        'ts': ts,
        'package_dict': package_dict
    }), file=fp)
    fp.flush()


if __name__ == '__main__':
    main(sys.argv[1])


