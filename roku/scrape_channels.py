"""
Goes through channel list. Scrapes all of them.

TODO:

 - Do not scrape paid channels. Free ones only.
 - Need to capture screen.
 - Need to do OK click stream.
 - Need to start scraping after going home.
 - Need to investigate a bug where the same channel is opened twice.

"""
from channel_surfer import ChannelSurfer
import json
import datetime
import traceback
import time
import os
import subprocess


def main():

    # Maps category to a list of channels
    channel_dict = {}

    with open('channel_list.txt') as fp:
        for line in fp:
            record = json.loads(line)
            channel_dict.setdefault(record['_category'], []).append(record)

    # Check what channels we have already scraped
    scraped_channel_ids = set()
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

        for channel in next_channels:

            if channel['id'] in scraped_channel_ids:
                log('Skipping', channel['id'])
                continue
            
            log('Scraping', channel['_category'], '-', channel['id'])

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


def scrape(channel):

    surfer = ChannelSurfer('172.24.1.239', channel['id'])

    surfer.install_channel()

    surfer.capture_packets('launch')
    surfer.launch_channel()
    surfer.capture_screenshots(20)    
    surfer.kill_all_tcpdump()

    for okay_ix in range(0, 3):
        surfer.capture_packets('select-{}'.format(okay_ix))
        surfer.press_select()
        surfer.capture_screenshots(20)
        surfer.kill_all_tcpdump()

    surfer.uninstall_channel()


if __name__ == '__main__':
    main()

