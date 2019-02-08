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
import threading
import queue
from shutil import copyfile, copyfileobj
from os.path import join, isfile

WARM_UP_CRAWL = False

if WARM_UP_CRAWL:
    LAUNCH_RETRY_CNT = 5  # detect  and store unmitmable domains and IPs
else:
    LAUNCH_RETRY_CNT = 1  # load unmitmable domains and IPs from files
LAUNCH_RETRY_CNT = 5
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
AUDIO_PREFIX="audio/"
SSLKEY_PREFIX = "keys/"
DB_PREFIX = "db/"
#Each channel will have a file with the result of crawl of that channel in this folder
FIN_CHL_PREFIX = "finished/"
folders = [PCAP_PREFIX, DUMP_PREFIX, LOG_PREFIX, SCREENSHOT_PREFIX, SSLKEY_PREFIX, LOG_FOLDER, AUDIO_PREFIX, FIN_CHL_PREFIX, DB_PREFIX]

MITMPROXY_ENABLED = True
RSYNC_EN = False
RSYNC_DIR = ' hoomanm@portal.cs.princeton.edu:/n/fs/iot-house/hooman/crawl-data/'


CUTOFF_TRESHOLD=100000
SCRAPE_TO = 900

#repeat = {}
# To get this list use this command:
# ls -larSt /mnt/iot-house/keys |  awk '{print $9}' | tr '\n' ','
channels_done = {}

global_keylog_file = os.getenv("MITMPROXY_SSLKEYLOGFILE") or os.getenv("SSLKEYLOGFILE")



class PropagatingThread(threading.Thread):
    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        if self.ret:
            return self.ret
        else:
            return None



def dns_sniffer_run():
    time.sleep(2)
    p = subprocess.Popen(
        'sudo -E python3 ./dns_sniffer.py ',
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )


def dump_as_json(obj, json_path):
    with open(json_path, 'w') as f:
        json.dump(obj, f, indent=2)


def dump_redis(PREFIX, date_prefix):
    full_path = os.path.abspath(PREFIX)
    log("Dumping Redis DBs in " + full_path)

    rName2IPDB_path = join(full_path , date_prefix + '-rName2IPDB.json')
    log("writing to " + rName2IPDB_path)
    with open(rName2IPDB_path, 'a') as f:
        redisdl.dump(f, host='localhost', port=6379, db=0)


    rIP2NameDB_path =  join(full_path, date_prefix + '-rIP2NameDB.json')
    log("writing to " + rIP2NameDB_path)
    with open(rIP2NameDB_path, 'a') as f:
        redisdl.dump(f, host='localhost', port=6379, db=1)

def rsync(date_prefix):
    time.sleep(3)

    rsync_command = str('rsync -rlptDv --remove-source-files ' +
                        str(DATA_DIR) +
                        RSYNC_DIR +
                        date_prefix)
    log(rsync_command)
    p = subprocess.run(
        rsync_command,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    log("rsync return code: " + str(p.returncode))
    if p.returncode != 0:
        log("rsync failed!")

ALL_CHANNELS_TXT = 'platforms/roku/channel_list.txt'  # file that includes all channel details


def write_log_files(output_file_desc, channel_id, channel_res_file, scrape_success):
    # Write logs
    if output_file_desc is not None:
        log('Writing logs for channel ', channel_id)
        copy_log_file(channel_id, output_file_desc, False)

    if RSYNC_EN:
        rsync()
        if output_file_desc is not None:
            copy_log_file(channel_id, output_file_desc, True)

    # Write result to file
    log('Writing result of crawl to ', channel_res_file)
    with open(channel_res_file, "w") as tfile:
        print(str(scrape_success), file=tfile)

def main(channel_list=ALL_CHANNELS_TXT):
    output_file_desc = open(LOG_FILE_PATH_NAME)
    dns_sniffer_run()
    date_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Maps category to a list of channels
    channel_dict = {}

    with open(channel_list) as fp:
        for line in fp:
            record = json.loads(line)
            channel_dict.setdefault(record['_category'], []).append(record)

    # Check what channels we have already scraped
    scraped_channel_ids = set()
    scraped_channel_ids.update(channels_done)

    log('Skipping channels:', scraped_channel_ids)

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

            channel_res_file  = join(DATA_DIR, FIN_CHL_PREFIX, str(channel['id'])) + ".txt"
            if os.path.isfile(channel_res_file) :
                log('Skipping', channel['id'], ' due to:', channel_res_file)
                continue

            log('Scraping', channel['_category'], '-', channel['id'])

            #if channel['id'] not in repeat:
            #    continue
            try:
                que = queue.Queue()
                scrape_success = False
                t = PropagatingThread(target=lambda q, arg1, arg2, arg3: q.put(scrape(arg1, arg2, arg3)),
                                     args=(que, channel['id'], date_prefix, output_file_desc,))

                t.start()
                t.join(timeout=SCRAPE_TO)
                scrape_success= que.get()
                if scrape_success:
                    log('Scraping of channel %s successful!' % str(channel['id']))
                else:
                    log('Error!! Scraping of channel %s unsuccessful!!!' % str(channel['id']))
            except Exception as e:
                log('Crawl crashed for channel:', str(channel['id']))
                log(traceback.format_exc())
            finally:
                write_log_files(output_file_desc, str(channel['id']), channel_res_file, scrape_success)


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


def scrape(channel_id, date_prefix, output_file_desc):
    check_folders()

    surfer = ChannelSurfer(TV_IP_ADDR, channel_id, str(DATA_DIR), str(PCAP_PREFIX), date_prefix, str(SCREENSHOT_PREFIX), str(AUDIO_PREFIX))
    if MITMPROXY_ENABLED:
        mitmrunner = MITMRunner(channel_id, str(DATA_DIR), str(DUMP_PREFIX), global_keylog_file)
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

        surfer.start_audio_recording(60)
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
        if MITMPROXY_ENABLED:
            try:
                mitmrunner.kill_mitmproxy()
            except Exception as e:
                log('Error killing MTIM!')
                traceback.print_exc()
        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
        return False
    except Exception as e:
        log('Error!')
        traceback.print_exc()
        return False
    finally:
        if MITMPROXY_ENABLED:
            try:
                mitmrunner.kill_mitmproxy()
            except Exception as e:
                log('Error killing MTIM!')
                traceback.print_exc()
        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
        dump_redis(join(DATA_DIR, DB_PREFIX), date_prefix)
        dump_as_json(timestamps, join(DATA_DIR, LOG_FOLDER,
                                      "%s_timestamps.json" % channel_id))
        return True


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if isfile(sys.argv[1]):
            main(sys.argv[1])
        else:
            channel_id = sys.argv[1]
            scrape(channel_id, "/tmp/scrape-crawl", None)
    else:
        main()

