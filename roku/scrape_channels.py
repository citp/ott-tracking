"""
Goes through channel list. Scrapes all of them.

TODO:

 - Do not scrape paid channels. Free ones only.
 - Need to capture screen.
 - Need to do OK click stream.
 - Need to start scraping after going home.
 - Need to investigate a bug where the same channel is opened twice.

"""
from channel_surfer import ChannelSurfer ,SurferAborted
from mitmproxy_runner import MITMRunner
import json
import datetime
import traceback
import time
import os
import subprocess

LAUNCH_RETRY_CNT = 6
TV_IP_ADDR = '172.24.1.135'
#TV_IP_ADDR = '172.24.1.97'
SLEEP_TIMER = 20
remove_dup = False
DATA_DIR="data/"
PCAP_PREFIX="pcaps/"
DUMP_PREFIX="mitmdumps/"
LOG_PREFIX="mitmlog/"
SCREENSHOT_PREFIX="screenshots/"
CUTOFF_TRESHOLD=200

#repeat = {96637,93374,7767,76936,74519,70275,7019,59997,59643,50118,50025,47643,44665,252241,252210,252143,250636,245889,241827,239827,237128,235963,234709,232422,23048,230440,223608,223597,220798,219384,216910,210892,210205,207814,205592,205385,196549,196460,196276,195482,195316,188555,179080,177305,175461,170744,160252,154157,153241,152032,151908,151483,149840,146731,146559,14654,144475,143105,14295,140474,122409,121999,12,118762,104764}



def dns_sniffer_run():
    time.sleep(2)
    p = subprocess.Popen(
        'sudo python2 ./dns_sniffer.py ',
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )


def main():
    dns_sniffer_run()
    prep_folders()

    # Maps category to a list of channels
    channel_dict = {}

    with open('channel_list.txt') as fp:
        for line in fp:
            record = json.loads(line)
            channel_dict.setdefault(record['_category'], []).append(record)

    # Check what channels we have already scraped
    scraped_channel_ids = set()
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

    print 'Skipping channels:', scraped_channel_ids
        
    # Scrape from the top channels of each category

    while True:

        next_channels = []

        for channel_list in channel_dict.itervalues():
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
                scrape(channel)

            except Exception:
                log('Crashed:', channel['id'])
                log(traceback.format_exc())


def log(*args):

    s = '[{}] '.format(datetime.datetime.today())
    s += ' '.join([str(v) for v in args])

    print s
    with open('scrape_channels.log', 'a') as fp:
        print >> fp, s



def prep_folders():
    folders = [PCAP_PREFIX, DUMP_PREFIX, LOG_PREFIX, SCREENSHOT_PREFIX]
    for f in folders:
        fullpath = str(DATA_DIR) + str(f)
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)

def check_folders():
    all_exist = True
    folders = [PCAP_PREFIX, DUMP_PREFIX, LOG_PREFIX, SCREENSHOT_PREFIX]
    for f in folders:
        fullpath = str(DATA_DIR) + str(f)
        if not os.path.exists(fullpath):
            all_exist = False
            print (fullpath + " doesn't exist.")
    return all_exist

def scrape(channel):
    if not check_folders():
        exit(-1)

    surfer = ChannelSurfer(TV_IP_ADDR, channel['id'], str(DATA_DIR), str(PCAP_PREFIX))
    mitmrunner = MITMRunner(channel['id'], 0, str(DATA_DIR), str(DUMP_PREFIX))


    try:
        mitmrunner.kill_mitmproxy()
        surfer.install_channel()

        mitmrunner.run_mitmproxy()
        surfer.capture_packets('launch')


        iter = 0
        while iter < LAUNCH_RETRY_CNT:
            surfer.launch_channel()
            time.sleep(4)
            iter += 1

        time.sleep(SLEEP_TIMER)

        surfer.kill_all_tcpdump()

        for okay_ix in range(0, 3):
            if not surfer.channel_is_active():
                surfer.launch_channel()
            surfer.capture_packets('select-{}'.format(okay_ix))
            surfer.press_select()
            surfer.capture_screenshots(20)
            surfer.kill_all_tcpdump()
        surfer.go_home()
    except SurferAborted, e:
        print 'Error!'
        traceback.print_exc()
    finally:
        mitmrunner.kill_mitmproxy()
        surfer.uninstall_channel()
        surfer.rsync()


if __name__ == '__main__':
    main()

