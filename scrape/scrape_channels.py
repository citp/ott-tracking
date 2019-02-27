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
import enum
from shutil import copyfile, copyfileobj
from os.path import join, isfile
import wave
import pyaudio
import numpy as np

'''
Crawl settings
'''

ENABLE_SMART_CRAWLER = False  # remove after testing
MITMPROXY_ENABLED = int(os.environ['MITMPROXY_ENABLED'])
remove_dup = False
RSYNC_EN = False
REC_AUD = True


MITMABLE_DOMAINS_WARM_UP_CRAWL = int(os.environ['MITMABLE_DOMAINS_WARM_UP_CRAWL'])


if MITMABLE_DOMAINS_WARM_UP_CRAWL and MITMPROXY_ENABLED:
    LAUNCH_RETRY_CNT = 5  # detect and store unmitmable domains and IPs
else:
    LAUNCH_RETRY_CNT = 1  # load unmitmable domains and IPs from files

TV_IP_ADDR = os.environ['TV_IP_ADDR']
SLEEP_TIMER = 20
DATA_DIR = os.getenv("DATA_DIR")
PCAP_PREFIX = "pcaps/"
DUMP_PREFIX = "mitmdumps/"
LOG_PREFIX = "mitmlog/"
LOG_FOLDER = "logs/"
LOG_FILE = 'scrape_channels.log'
LOG_DIR = os.getenv("LogDir")
LOG_FILE_PATH_NAME = os.getenv("LOG_OUT_FILE")
SCREENSHOT_PREFIX = "screenshots/"
AUDIO_PREFIX="audio/"
SSLKEY_PREFIX = "keys/"
DB_PREFIX = "db/"
#Each channel will have a file with the result of crawl of that channel in this folder
FIN_CHL_PREFIX = "finished/"
folders = [PCAP_PREFIX, DUMP_PREFIX, LOG_PREFIX, SCREENSHOT_PREFIX, SSLKEY_PREFIX, LOG_FOLDER, AUDIO_PREFIX, FIN_CHL_PREFIX, DB_PREFIX]


RSYNC_DIR = ' hoomanm@portal.cs.princeton.edu:/n/fs/iot-house/hooman/crawl-data/'


CUTOFF_TRESHOLD=100000
SCRAPE_TO = 900

PLAT = os.getenv("PLATFORM")

if PLAT == "ROKU":
    from platforms.roku.get_all_channels import get_channel_list
elif PLAT == "AMAZON":
    from platforms.amazon.get_all_channels import get_channel_list


#repeat = {}
# To get this list use this command:
# ls -larSt /mnt/iot-house/keys |  awk '{print $9}' | tr '\n' ','
channels_done = {}

global_keylog_file = os.getenv("MITMPROXY_SSLKEYLOGFILE") or os.getenv("SSLKEYLOGFILE")



class CrawlState(enum.Enum):
    STARTING = 1
    PREINSTALL = 2
    INSTALLING = 3
    LAUNCHING = 4
    TERMINATING = 5
    TERMINATED = 6

    def __new__(cls, value):
        member = object.__new__(cls)
        member._value_ = value
        return member

    def __int__(self):
        return self.value

    def __str__(self):
        return self.name


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
    with open(rName2IPDB_path, 'w') as f:
        redisdl.dump(f, host='localhost', port=6379, db=0)


    rIP2NameDB_path =  join(full_path, date_prefix + '-rIP2NameDB.json')
    log("writing to " + rIP2NameDB_path)
    with open(rIP2NameDB_path, 'w') as f:
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

def main(channel_list=None):
    output_file_desc = open(LOG_FILE_PATH_NAME)
    dns_sniffer_run()
    date_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Maps category to a list of channels
    if channel_list is not None:
        channels = get_channel_list(channel_list)
    else:
        channels = get_channel_list()



    # Check what channels we have already scraped
    scraped_channel_ids = set()
    scraped_channel_ids.update(channels_done)

    log('Skipping channels:', scraped_channel_ids)

    # Scrape from the top channels of each category

    while True:

        next_channels = []

        if PLAT == "ROKU":
            for channel_l in channels.values():
                if channel_l:
                    next_channels.append(channel_l.pop(0))
        elif PLAT == "AMAZON":
            for channel in channels:
                next_channels.append(channel)
                channels.remove(channel)

        if not next_channels:
            if REC_AUD:
                recorder.complete_audio_recording()
            break

        cntr = 0
        for channel in next_channels:

            if cntr == CUTOFF_TRESHOLD:
                break
            cntr += 1

            if channel['id'] in scraped_channel_ids:
                log('Skipping', channel['id'])
                continue
            channel_state = CrawlState.STARTING

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
                t = PropagatingThread(target=lambda q, arg1, arg2: q.put(scrape(arg1, arg2)),
                                     args=(que, channel['id'], date_prefix,))

                t.start()
                t.join(timeout=SCRAPE_TO)
                channel_state = que.get()
                log("Crawl result: " + str(channel_state))
                if channel_state == channel_state.TERMINATED:
                    scrape_success = True
                if scrape_success:
                    log('Scraping of channel %s successful!' % str(channel['id']))
                else:
                    log('Error!! Scraping of channel %s unsuccessful!!!' % str(channel['id']))
            except Exception as e:
                log('Crawl crashed for channel:', str(channel['id']))
                log(traceback.format_exc())
            finally:
                write_log_files(output_file_desc, str(channel['id']), channel_res_file, channel_state)

def log(*args):

    s = '[{}] '.format(datetime.today())
    s += ' '.join([str(v) for v in args])

    print(s)
    with open(os.path.join(LOG_DIR , LOG_FILE), 'a') as fp:
        print(s, file=fp)


class AudioRecorder(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.pyaudio = pyaudio.PyAudio()
        self.speaker_device = self.pyaudio.get_default_output_device_info()['hostApi']
        self.recorded_message = []
        self.record = False
        self.seconds = 0
        self.active = True
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        log('Audio: Opening audio stream.')
        self.stream = self.pyaudio.open(format=self.format, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk, input_host_api_specific_stream_info=self.speaker_device)
        log('Audio: Audio stream opened.')

    def run(self):
        log('Audio: Starting audio thread.')
        while True:
            # Recording has been asked to stop completely
            if not self.active:
                break

            # Asked to record
            if self.record:
                # Read from the stream
                for i in range(0, int(self.rate / self.chunk * self.seconds)):
                    # Stop recording immediately if flag switches
                    if self.record:
                        data = self.stream.read(self.chunk, exception_on_overflow=False)
                        self.recorded_message.append(data)
                    else:
                        break

                # Done recording for time seconds so end recording
                self.record = False

        log('Audio: Exiting audio thread.')
        return

    def start_recording(self, seconds, channel_id):
        log('Audio: Started audio recording for channel %s' % str(channel_id))
        # Stop the current recording immediately
        self.record = False
        # Make the current recording empty, adn set the seconds to record
        self.recorded_message = []
        self.seconds = seconds
        # Start recording
        self.record = True
        return


    def dump(self, filename_path):
        self.record = False
        wf = wave.open(filename_path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.pyaudio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.recorded_message))
        wf.close()
        log('Audio: Dumped audio to file %s' % filename_path)
        self.recorded_message = []

    def complete_audio_recording(self):
        self.recorded_message = []
        self.record = False
        self.active = False
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio.terminate()
        log('Audio: Exited audio thread.')

        return

    def is_audio_playing(self, seconds):
        if len(self.recorded_message) < seconds:
            return False

        '''data = self.recorded_message[-int(seconds):]
        frames = []
        for d in data:
            frames.append(np.fromstring(d, dtype=np.int16))

        npdata = np.hstack(frames)
        mat = npdata.reshape(npdata.shape[0]//2, self.channels)
        print(mat.shape)

        baseline = np.zeros(shape=(mat.shape[0], self.channels))
        print(baseline.shape)
        for i in range(0, seconds):
            second = mat[self.rate*i:self.rate*(i+1), :]
            dist = np.sqrt(np.sum((second - baseline)**2, axis=1))
            print(i, np.mean(dist), np.max(dist))'''

        return False

if REC_AUD:
    # Starting audio thread
    recorder = AudioRecorder()
    recorder.start()

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

    if PLAT == "AMAZON":
        copy_adb_logs(channel_id)


def copy_adb_logs(channel_id):
    filename = '{}-{}'.format(
        channel_id,
        int(time.time())
    )

    output_path = join(str(DATA_DIR), LOG_FOLDER , str(filename) + ".adblog")
    input_path = os.path.join(LOG_DIR , "adb.log")
    print("Copying ADB log from " + input_path + " to " + str(output_path))

    copyfile(input_path, output_path)

def concat(src, dst):
    with open(src) as src:
        with open(dst, 'a') as dst:
            for l in src:
                dst.write(l)

def truncate_file(path):
    #Clear the original log file
    open(path, 'w').close()


def detect_playback_using_screenshots(surfer):
    """TODO: process screenshots to detect video playback
       return True if playback is detected, False otherwise
    """
    return False


def detect_playback_using_audio(seconds):
    if REC_AUD:
        return recorder.is_audio_playing(seconds)
    else:
        return False


def is_video_playing(surfer, seconds=5):
    """Return True if playback is detected by either audio or screenshots"""
    return detect_playback_using_audio(seconds) or \
        detect_playback_using_screenshots(surfer)


KEY_SEQUENCES = {
    "ROKU": [
        ["Select", "Select", "Select"],
        ["Down", "Down", "Select"]],
    "AMAZON": [
        ["Select", "Select", "Select"],
        ["Down", "Down", "Select"]]
}



def play_key_sequence(surfer, key_sequence, timestamps_arr):
    for key in key_sequence:
        timestamps_arr.append((key, int(time.time())))
        surfer.press_key(key)
        if key == "Select":  # check for playback only after Select
            surfer.capture_screenshots(20)
            if is_video_playing(surfer):
                return True
    else:
        return False


def fast_forward(surfer):
    """Press FWD to trigger more ads"""
    pass


def launch_channel_for_mitm_warmup(surfer, retry_count):
    for _ in range(retry_count):
        surfer.launch_channel()
        time.sleep(4)


def scrape(channel_id, date_prefix):
    if REC_AUD:
        recorder.start_recording(SCRAPE_TO, channel_id)

    channel_state = CrawlState.PREINSTALL
    err_occurred = False
    check_folders()

    surfer = ChannelSurfer(TV_IP_ADDR, channel_id, str(DATA_DIR), str(PCAP_PREFIX), date_prefix, str(SCREENSHOT_PREFIX))
    if MITMPROXY_ENABLED:
        mitmrunner = MITMRunner(channel_id, str(DATA_DIR), str(DUMP_PREFIX), global_keylog_file)
    timestamps = {}  # TODO: will become obsolete after we move to smart crawl, remove
    timestamps_arr = []  # list of tuples in the form of (key, timestamp)

    try:
        if MITMPROXY_ENABLED:
            mitmrunner.clean_iptables()
            mitmrunner.kill_existing_mitmproxy()
        timestamps["install_channel"] = int(time.time())
        channel_state = CrawlState.INSTALLING
        surfer.install_channel()

        if MITMPROXY_ENABLED:
            mitmrunner.run_mitmproxy()
        timestamp = int(time.time())
        surfer.capture_packets(timestamp)
        timestamps["launch"] = timestamp

        channel_state = CrawlState.LAUNCHING

        if MITMABLE_DOMAINS_WARM_UP_CRAWL:
            launch_channel_for_mitm_warmup(surfer, LAUNCH_RETRY_CNT)

        time.sleep(SLEEP_TIMER)
        if ENABLE_SMART_CRAWLER:
            playback_detected = False
            surfer.launch_channel()   # make sure we start from the homepage
            for key_sequence in KEY_SEQUENCES[PLAT]:
                playback_detected = play_key_sequence(
                    surfer, key_sequence, timestamps_arr)
                if playback_detected:
                    log('Playback detected on channel: %s' % channel_id)
                    fast_forward(surfer)
                    break

                time.sleep(4)
                # TODO: should we restart audio recording here?
            else:
                log('Cannot detect playback on channel: %s' % channel_id)


        else:
            for okay_ix in range(0, 3):
                if not surfer.channel_is_active():
                    surfer.launch_channel()
                timestamps['select-{}'.format(okay_ix)] = int(time.time())
                surfer.press_select()
                surfer.capture_screenshots(20)

        channel_state = CrawlState.TERMINATING
        surfer.go_home()
    except SurferAborted as e:
        err_occurred = True
        log('Channel not installed! Aborting scarping of channel')
        if MITMPROXY_ENABLED:
            try:
                mitmrunner.kill_mitmproxy()
            except Exception as e:
                log('Error killing MTIM!')
                traceback.print_exc()

        if REC_AUD:
            recorder.dump(str(DATA_DIR) + str(AUDIO_PREFIX) + '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time())))

        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
    except Exception as e:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    finally:
        try:
            if MITMPROXY_ENABLED:
                try:
                    mitmrunner.kill_mitmproxy()
                except Exception as e:
                    log('Error killing MTIM!')
                    traceback.print_exc()

            if REC_AUD:
                recorder.dump(str(DATA_DIR) + str(AUDIO_PREFIX) + '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time())))

            surfer.uninstall_channel()
            surfer.kill_all_tcpdump()
            surfer.terminate_rrc()
            dump_redis(join(DATA_DIR, DB_PREFIX), date_prefix)
            dump_as_json(timestamps, join(DATA_DIR, LOG_FOLDER,
                                          "%s_timestamps.json" % channel_id))
            if not err_occurred:
                channel_state = CrawlState.TERMINATED
        except Exception as e:
            log('Error!')
            traceback.print_exc()

    return channel_state


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if isfile(os.path.abspath(sys.argv[1])):
            main(sys.argv[1])
        else:
            channel_id = int(sys.argv[1])
            scrape(channel_id, "/tmp/scrape-crawl")
    else:
        main()
