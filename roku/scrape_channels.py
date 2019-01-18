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
import shutil
from shutil import copyfile, copyfileobj
from os.path import join

LAUNCH_RETRY_CNT = 7
#TV_IP_ADDR = '172.24.1.135'
TV_IP_ADDR = os.environ['TV_IP_ADDR']
SLEEP_TIMER = 20
remove_dup = False
DATA_DIR = os.getenv("DATA_DIR")
PCAP_PREFIX = "pcaps/"
DUMP_PREFIX = "mitmdumps/"
LOG_PREFIX = "mitmlog/"
LOG_FOLDER = "logs/"
LOG_FILE_PATH_NAME = os.getenv("LOG_OUT_FILE")
SCREENSHOT_PREFIX = "screenshots/"
SSLKEY_PREFIX = "keys/"
folders = [PCAP_PREFIX, DUMP_PREFIX, LOG_PREFIX, SCREENSHOT_PREFIX, SSLKEY_PREFIX, LOG_FOLDER]

MITMPROXY_ENABLED = True


CUTOFF_TRESHOLD=200

#repeat = {}
# To get this list use this command:
# ls -larSt /mnt/iot-house/keys |  awk '{print $9}' | tr '\n' ','
channels_done = {}

global_keylog_file = os.getenv("MITMPROXY_SSLKEYLOGFILE") or os.getenv("SSLKEYLOGFILE")


def dns_sniffer_run():
    time.sleep(2)
    p = subprocess.Popen(
        'sudo -E python3 ./dns_sniffer.py ',
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
    output_file_desc = open(LOG_FILE_PATH_NAME)
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
                scrape(channel['id'], crawl_folder, output_file_desc)

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
    for f in folders:
        fullpath = str(DATA_DIR) + "/" +str(f)
        if not os.path.exists(fullpath):
            print (fullpath + " doesn't exist! Creating it!")
            os.makedirs(fullpath)

def cleanup_sslkey_file(fileAddr):
    log('Erasing content of file '+ fileAddr)
    open(fileAddr, 'w').close()

def strip_null_chr(output_path):
    from_file = open(output_path)
    line = from_file.readline().replace('\x00', '')

    to_file = open(output_path,mode="w")
    to_file.write(line)
    copyfileobj(from_file, to_file)


def copy_log_file(channel_id, output_file_desc, is_rsync_res):
    filename = '{}-{}'.format(
        channel_id,
        int(time.time())
    )

    if not is_rsync_res:
        output_path = str(DATA_DIR) + "/" + LOG_FOLDER +"/" + str(filename) + ".log"
    else:
        output_path = str(DATA_DIR) + "/" + LOG_FOLDER +"/" + str(filename) + ".rsync.log"

    #copy dest file for copying
    to_file = open(output_path,mode="w")
    copyfileobj(output_file_desc, to_file)
    #move the read file descriptor to the end of the file
    output_file_desc.seek(0,2)


def concat(src, dst):
    with open(src) as src:
        with open(dst, 'a') as dst:
            for l in src:
                dst.write(l)

def truncate_file(path):
    #Clear the original log file
    open(path, 'w').close()


def scrape(channel_id, crawl_folder, output_file_desc):
    check_folders()

    surfer = ChannelSurfer(TV_IP_ADDR, channel_id, str(DATA_DIR), str(PCAP_PREFIX), crawl_folder, str(SCREENSHOT_PREFIX))
    if MITMPROXY_ENABLED:
        cleanup_sslkey_file(global_keylog_file)
        mitmrunner = MITMRunner(channel_id, 0, str(DATA_DIR), str(DUMP_PREFIX), global_keylog_file)
    timestamps = {}

    try:
        if MITMPROXY_ENABLED:
            mitmrunner.clean_iptables()
            mitmrunner.kill_existing_mitmproxy()
        timestamps["install_channel"] = int(time.time())
        surfer.install_channel()

        if MITMPROXY_ENABLED:
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
        log('Channel not installed! Aborting scarping of channel')
        #traceback.print_exc()
    except Exception as e:
        print('Error!')
        traceback.print_exc()
    finally:
        if MITMPROXY_ENABLED:
            mitmrunner.kill_mitmproxy()
        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
        dump_redis(DATA_DIR)
        dump_as_json(timestamps, join(DATA_DIR, LOG_FOLDER,
                                      "%s_timestamps.json" % channel_id))
        if output_file_desc is not None:
            copy_log_file(channel_id, output_file_desc, False)
        surfer.rsync()
        if output_file_desc is not None:
            copy_log_file(channel_id, output_file_desc, True)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        channel_id = sys.argv[1]
        scrape(channel_id, "/tmp/scrape-crawl", None)
    else:
        main()
