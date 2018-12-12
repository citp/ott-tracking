"""
Goes through channel list. Scrapes all of them.

TODO:

 - Do not scrape paid channels. Free ones only.
 - Need to capture screen.
 - Need to do OK click stream.
 - Need to start scraping after going home.
 - Need to investigate a bug where the same channel is opened twice.

"""
from __future__ import print_function
from channel_surfer import ChannelSurfer ,SurferAborted
from mitmproxy_runner import MITMRunner
import json
from datetime import datetime
import traceback
import time
import os
import subprocess
import sys
import redisdl
from shutil import copyfile
from os.path import join

LAUNCH_RETRY_CNT = 7
#TV_IP_ADDR = '172.24.1.135'
TV_IP_ADDR = os.environ['TV_IP_ADDR']
SLEEP_TIMER = 20
remove_dup = False
DATA_DIR="data/"
PCAP_PREFIX="pcaps/"
DUMP_PREFIX="mitmdumps/"
LOG_PREFIX="mitmlog/"
LOG_FOLDER="logs/"
LOG_FILE_PATH_NAME=os.getenv("LOG_OUT_FILE")
SCREENSHOT_PREFIX="screenshots/"
SSLKEY_PREFIX="keys/"
CUTOFF_TRESHOLD=200
MASTER_LOG = "master.log"


#repeat = {}
# To get this list use this command:
# ls -larSt /mnt/iot-house/keys |  awk '{print $9}' | tr '\n' ','
channels_done = {}

global_keylog_file = os.getenv("MITMPROXY_SSLKEYLOGFILE") or os.getenv("SSLKEYLOGFILE")


def dns_sniffer_run():
    time.sleep(2)
    p = subprocess.Popen(
        'sudo python2 ./dns_sniffer.py ',
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )


def dump_as_json(obj, json_path):
    with open(json_path, 'w') as f:
        json.dump(obj, f, indent=2)


def dump_redis(PREFIX):
    full_path = os.path.abspath(PREFIX)
    log("Dumping Redis DBs in " + full_path)

    rName2IPDB_path = full_path + '/rName2IPDB.json'
    #log("writing to " + rName2IPDB_path)
    with open(rName2IPDB_path, 'a') as f:
        redisdl.dump(f, host='localhost', port=6379, db=0)


    rIP2NameDB_path =  full_path + '/rIP2NameDB.json'
    #log("writing to " + rIP2NameDB_path)
    with open(rIP2NameDB_path, 'a') as f:
        redisdl.dump(f, host='localhost', port=6379, db=1)


def main():
    truncate_file(MASTER_LOG)
    dns_sniffer_run()
    crawl_folder = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Maps category to a list of channels
    channel_dict = {}

    with open('channel_list.txt') as fp:
        for line in fp:
            record = json.loads(line)
            channel_dict.setdefault(record['_category'], []).append(record)

    # Check what channels we have already scraped
    scraped_channel_ids = set()
    scraped_channel_ids.update(channels_done)
    if remove_dup:
        file_list = subprocess.check_output(
            'sudo ssh yuxingh@wash.cs.princeton.edu "ls ~/iot-house/public_html/pcaps/roku-channel-surfer/2018-09-27/pcaps"',
            shell=True
        ).split()
        for filename in file_list:
            if not filename.endswith('.pcap'):
                continue
            channel_id = filename.split('-', 1)[0]
            scraped_channel_ids.add(int(channel_id))

    print('Skipping channels:', scraped_channel_ids)

    # Scrape from the top channels of each category

    while True:

        next_channels = []

        for channel_list in channel_dict.values():
            if channel_list:
                next_channels.append(channel_list.pop(0))

        if not next_channels:
            break

        cntr = 0
        for channel in next_channels:

            if cntr == CUTOFF_TRESHOLD:
                break
            cntr += 1

            if channel['id'] in scraped_channel_ids:
                log('Skipping', channel['id'])
                continue

            log('Scraping', channel['_category'], '-', channel['id'])

            #if channel['id'] not in repeat:
            #    continue
            try:
                scrape(channel['id'], crawl_folder)

            except Exception:
                log('Crashed:', channel['id'])
                log(traceback.format_exc())


def log(*args):

    s = '[{}] '.format(datetime.today())
    s += ' '.join([str(v) for v in args])

    print(s)
    with open('scrape_channels.log', 'a') as fp:
        print(s, file=fp)



def check_folders():
    folders = [PCAP_PREFIX, DUMP_PREFIX, LOG_PREFIX, SCREENSHOT_PREFIX, SSLKEY_PREFIX, LOG_FOLDER]
    for f in folders:
        fullpath = str(DATA_DIR) + str(f)
        if not os.path.exists(fullpath):
            print (fullpath + " doesn't exist! Creating it!")
            os.makedirs(fullpath)

def cleanup_sslkey_file(fileAddr):
    log('Erasing content of file '+ fileAddr)
    open(fileAddr, 'w').close()

def copy_log_file(channel_id):
    filename = '{}-{}'.format(
        channel_id,
        int(time.time())
    )

    output_path = str(DATA_DIR) + "/" + LOG_FOLDER +"/" + str(filename) + ".log"

    copyfile(LOG_FILE_PATH_NAME, output_path)


def concat(src, dst):
    with open(src) as src:
        with open(dst, 'a') as dst:
            for l in src:
                dst.write(l)

def truncate_file(path):
    #Clear the original log file
    open(path, 'w').close()


def scrape(channel_id, crawl_folder):
    check_folders()

    surfer = ChannelSurfer(TV_IP_ADDR, channel_id, str(DATA_DIR), str(PCAP_PREFIX), crawl_folder)
    cleanup_sslkey_file(global_keylog_file)
    mitmrunner = MITMRunner(channel_id, 0, str(DATA_DIR), str(DUMP_PREFIX), global_keylog_file)
    timestamps = {}

    try:
        mitmrunner.clean_iptables()
        timestamps["install_channel"] = int(time.time())
        surfer.install_channel()

        mitmrunner.run_mitmproxy()
        timestamp = int(time.time())
        surfer.capture_packets(timestamp)
        timestamps["launch"] = timestamp

        iter = 0
        while iter < LAUNCH_RETRY_CNT:
            surfer.launch_channel()
            time.sleep(4)
            iter += 1

        time.sleep(SLEEP_TIMER)

        for okay_ix in range(0, 3):
            if not surfer.channel_is_active():
                surfer.launch_channel()
            timestamps['select-{}'.format(okay_ix)] = int(time.time())
            surfer.press_select()
            surfer.capture_screenshots(20)
        surfer.go_home()
    except SurferAborted as e:
        print('Error!')
        traceback.print_exc()
    except Exception as e:
        print('Error!')
        traceback.print_exc()
    finally:
        mitmrunner.kill_mitmproxy()
        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
        dump_redis(DATA_DIR)
        dump_as_json(timestamps, join(DATA_DIR, LOG_FOLDER,
                                      "%s_timestamps.json" % channel_id))
        copy_log_file(channel_id)
        surfer.rsync()
        concat(LOG_FILE_PATH_NAME, MASTER_LOG)
        truncate_file(LOG_FILE_PATH_NAME)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        channel_id = sys.argv[1]
        scrape(channel_id, "TEST")
    else:
        main()
