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
import scrape_config


from channel_surfer import ChannelSurfer ,SurferAborted
from mitmproxy_runner import MITMRunner
from dns_sniffer import dns_sniffer_call
from multiprocessing import Process
from shutil import copyfile, copyfileobj
from os.path import join, isfile
if scrape_config.REC_AUD:
    from audio_recorder import AudioRecorder

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
    #time.sleep(2)
    #p = subprocess.Popen(
    #    'sudo -E python3 ./dns_sniffer.py ',
    #    stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    #)
    global dns_sniff_process
    wlan_if_name = os.environ['WLANIF']
    log("Starting DNS Sniff")
    dns_sniff_process = Process(target=dns_sniffer_call, args=(wlan_if_name,))
    dns_sniff_process.start()

def dns_sniffer_stop():
    global dns_sniff_process
    if dns_sniff_process is not None:
        dns_sniff_process.terminate()
    else:
        log("Error stopping DNS sniffer! Process not found")



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
                        str(scrape_config.DATA_DIR) +
                        scrape_config.RSYNC_DIR +
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

    if scrape_config.RSYNC_EN:
        rsync()
        if output_file_desc is not None:
            copy_log_file(channel_id, output_file_desc, True)

    # Write result to file
    log('Writing result of crawl to ', channel_res_file)
    with open(channel_res_file, "w") as tfile:
        print(str(scrape_success), file=tfile)


def main(channel_list=None):
    output_file_desc = open(scrape_config.LOG_FILE_PATH_NAME)
    dns_sniffer_run()
    date_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Maps category to a list of channels

    if scrape_config.PLAT == "ROKU":
        log("Importing Roku channels")
        from platforms.roku.get_all_channels import get_channel_list
    elif scrape_config.PLAT == "AMAZON":
        log("Importing Amazon channels")
        from platforms.amazon.get_all_channels import get_channel_list

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

        if scrape_config.PLAT == "ROKU":
            for channel_l in channels.values():
                if channel_l:
                    next_channels.append(channel_l.pop(0))
        elif scrape_config.PLAT == "AMAZON":
            for channel in channels:
                next_channels.append(channel)
                channels.remove(channel)

        if not next_channels:
            if scrape_config.REC_AUD:
                recorder.complete_audio_recording()
            dns_sniffer_stop()
            log("Scrapping finished. Terminating the crawl")
            break

        cntr = 0
        for channel in next_channels:

            if cntr == scrape_config.CUTOFF_TRESHOLD:
                break
            cntr += 1

            if channel['id'] in scraped_channel_ids:
                log('Skipping', channel['id'])
                continue
            channel_state = CrawlState.STARTING

            channel_res_file  = join(scrape_config.DATA_DIR, scrape_config.FIN_CHL_PREFIX,
                                     str(channel['id'])) + ".txt"
            if os.path.isfile(channel_res_file) :
                log('Skipping', channel['id'], ' due to:', channel_res_file)
                continue

            log('Scraping', channel['_category'], '-', channel['id'])

            #if channel['id'] not in repeat:
            #    continue
            try:
                scrape_success = False
                if scrape_config.THREADED_SCRAPE:
                    que = queue.Queue()
                    t = PropagatingThread(target=lambda q, arg1, arg2: q.put(scrape(arg1, arg2)),
                                         args=(que, channel['id'], date_prefix,))

                    t.start()
                    t.join(timeout=scrape_config.SCRAPE_TO)
                    channel_state = que.get()
                else:
                    channel_state = scrape(channel['id'], date_prefix)
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
    with open(os.path.join(scrape_config.LOCAL_LOG_DIR , scrape_config.LOG_FILE), 'a') as fp:
        print(s, file=fp)

if scrape_config.REC_AUD:
    # Create recorder object
    try:
        recorder = AudioRecorder(log)
    except Exception as e:
        log(e)
        log('Error while creating the recorder. Perhaps the device doesn\'t have an audio output cable connected?')
        scrape_config.REC_AUD = False

if scrape_config.REC_AUD:
    # Starting audio thread
    recorder.start()

def check_folders():
    for f in scrape_config.folders:
        fullpath = join(scrape_config.DATA_DIR , str(f))
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
        output_path = str(scrape_config.DATA_DIR) + "/" + \
                      scrape_config.LOG_PREFIX +"/" + str(filename) + ".log"
    else:
        output_path = str(scrape_config.DATA_DIR) + "/" + \
                      scrape_config.LOG_PREFIX +"/" + str(filename) + ".rsync.log"

    #copy dest file for copying
    to_file = open(output_path,mode="w")
    copyfileobj(output_file_desc, to_file)
    #move the read file descriptor to the end of the file
    output_file_desc.seek(0,2)

    if scrape_config.PLAT == "AMAZON":
        copy_adb_logs(channel_id)


def copy_adb_logs(channel_id):
    filename = '{}-{}'.format(
        channel_id,
        int(time.time())
    )

    output_path = join(str(scrape_config.DATA_DIR),
                       scrape_config.LOG_PREFIX , str(filename) + ".adblog")
    input_path = os.path.join(scrape_config.LOCAL_LOG_DIR , "adb.log")
    print("Copying ADB log from " + input_path + " to " + str(output_path))

    copyfile(input_path, output_path)

def detect_playback_using_screenshots(surfer):
    """TODO: process screenshots to detect video playback
       return True if playback is detected, False otherwise
    """
    return False


def detect_playback_using_audio(seconds):
    if scrape_config.REC_AUD:
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
            surfer.capture_screenshots(10)
            if is_video_playing(surfer):
                return True
    else:
        return False


def fast_forward(surfer):
    """Press FWD to trigger more ads"""
    pass


def launch_channel_for_mitm_warmup(surfer, retry_count):
    iter = 1
    for _ in range(retry_count):
        surfer.timestamp_event("launch-" + str(iter))
        surfer.launch_channel()
        time.sleep(4)
        iter += 1


def setup_channel(channel_id, date_prefix):
    err_occurred = False
    try:
        if scrape_config.REC_AUD:
            recorder.start_recording(scrape_config.SCRAPE_TO, channel_id)

        check_folders()

        surfer = ChannelSurfer(scrape_config.TV_IP_ADDR,
                               channel_id, str(scrape_config.DATA_DIR),
                               str(scrape_config.LOG_PREFIX),
                               str(scrape_config.PCAP_PREFIX), date_prefix,
                               str(scrape_config.SCREENSHOT_PREFIX))
        if scrape_config.MITMPROXY_ENABLED:
            mitmrunner = MITMRunner(channel_id, str(scrape_config.DATA_DIR),
                                    str(scrape_config.DUMP_PREFIX), global_keylog_file, scrape_config.SSL_STRIP)
        timestamps = {}  # TODO: will become obsolete after we move to smart crawl, remove

        timestamp = int(time.time())
        surfer.capture_packets(timestamp)
        if scrape_config.MITMPROXY_ENABLED:
            mitmrunner.clean_iptables()
            mitmrunner.kill_existing_mitmproxy()
    except Exception as e:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    ret = [err_occurred, surfer, timestamps]
    if scrape_config.MITMPROXY_ENABLED:
        ret.append(mitmrunner)
    return ret


def install_channel(surfer, timestamps):
    err_occurred = False
    surfer.timestamp_event("install_channel")
    try:

        surfer.install_channel()
    except SurferAborted as e:
        err_occurred = True
        log('Channel not installed! Aborting scarping of channel')
        if scrape_config.REC_AUD:
            recorder.dump(str(scrape_config.DATA_DIR) + str(scrape_config.AUDIO_PREFIX)
                          + '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time())))

        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
    except Exception as e:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    return err_occurred


def launch_mitm(mitmrunner):
    mitmrunner.run_mitmproxy()


def launch_channel(surfer, mitmrunner, timestamps):
    err_occurred = False
    timestamps_arr = []  # list of tuples in the form of (key, timestamp)
    try:
        surfer.timestamp_event("launch")

        if scrape_config.MITMABLE_DOMAINS_WARM_UP_CRAWL:
            launch_channel_for_mitm_warmup(surfer, scrape_config.LAUNCH_RETRY_CNT)

        time.sleep(scrape_config.SLEEP_TIMER)
        if scrape_config.ENABLE_SMART_CRAWLER:
            playback_detected = False
            surfer.launch_channel()  # make sure we start from the homepage
            for key_sequence in KEY_SEQUENCES[scrape_config.PLAT]:
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
                surfer.timestamp_event('select-{}'.format(okay_ix))
                surfer.press_select()
                surfer.capture_screenshots(20)
    except SurferAborted as e:
        err_occurred = True
        log('Channel failed during launch! Aborting scarping of channel')
        if scrape_config.MITMPROXY_ENABLED:
            try:
                mitmrunner.kill_mitmproxy()
            except Exception as e:
                log('Error killing MTIM!')
                traceback.print_exc()

        if scrape_config.REC_AUD:
            recorder.dump(str(scrape_config.DATA_DIR) + str(scrape_config.AUDIO_PREFIX)
                          + '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time())))

        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
    except Exception as e:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    return err_occurred


def collect_data(surfer, mitmrunner, timestamps, date_prefix, channel_id):
    err_occurred = False
    try:
        surfer.go_home()
        if scrape_config.MITMPROXY_ENABLED:
            try:
                mitmrunner.kill_mitmproxy()
            except Exception as e:
                log('Error killing MTIM!')
                traceback.print_exc()

        if scrape_config.REC_AUD:
            recorder.dump(str(scrape_config.DATA_DIR) + str(scrape_config.AUDIO_PREFIX)
                          + '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time())))

        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
        surfer.terminate_rrc()
        dump_redis(join(scrape_config.DATA_DIR, scrape_config.DB_PREFIX), date_prefix)
        surfer.write_timestamps()
        #dump_as_json(timestamps, join(scrape_config.DATA_DIR, scrape_config.LOG_PREFIX,
        #                              "%s_timestamps.json" % channel_id))
    except Exception as e:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    return err_occurred


def scrape(channel_id, date_prefix):
    channel_state = CrawlState.PREINSTALL
    ret = setup_channel(channel_id, date_prefix)
    err_occurred = ret[0]
    if not err_occurred:
        surfer = ret[1]
        timestamps = ret[2]
        if scrape_config.MITMPROXY_ENABLED:
            mitmrunner = ret[3]
        else:
            mitmrunner = None
        channel_state = CrawlState.INSTALLING
        err_occurred = install_channel(surfer, timestamps)
        if not err_occurred:
            channel_state = CrawlState.LAUNCHING
            if scrape_config.MITMPROXY_ENABLED:
                launch_mitm(mitmrunner)
            err_occurred = launch_channel(surfer, mitmrunner, timestamps)
            if not err_occurred:
                channel_state = CrawlState.TERMINATING
                err_occurred = collect_data(surfer, mitmrunner, timestamps, date_prefix, channel_id)
                if not err_occurred:
                    channel_state = CrawlState.TERMINATED
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
