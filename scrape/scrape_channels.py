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
import glob
import signal


from smtplib import SMTP
from channel_surfer import ChannelSurfer ,SurferAborted
from mitmproxy_runner import MITMRunner
from dns_sniffer import dns_sniffer_call
from multiprocessing import Process, Event
from shutil import copyfile, copyfileobj
from os.path import join, isfile
from timeout import timeout
from time import sleep
if scrape_config.REC_AUD_BY_PYAUDIO:
    from audio_recorder import AudioRecorder

if scrape_config.REC_AUD_BY_ARECORD:
    from audio_recorder import audio_played_second

MITM_LEARNED_NEW_ENDPOINT = "/tmp/MITM_LEARNED_NEW_ENDPOINT"
OTT_CURRENT_CHANNEL_FILE = "/tmp/OTT_CURRENT_CHANNEL"

#repeat = {}
# To get this list use this command:
# ls -larSt /mnt/iot-house/keys |  awk '{print $9}' | tr '\n' ','
channels_done = {}

#This is a global env that needs to be set in bash
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
    dns_sniff_process = Process(target=dns_sniffer_call, args=(wlan_if_name, scrape_config.TV_IP_ADDR,))
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
    try:
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
    except:
        log('Error copying logs and writing result for channel % ', channel_id)
        log(traceback.format_exc())


def main(channel_list=None):
    output_file_desc = open(scrape_config.LOG_FILE_PATH_NAME)
    dns_sniffer_run()
    remove_file(OTT_CURRENT_CHANNEL_FILE)
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

        if isinstance(channels, dict):
            for channel_l in channels.values():
                if channel_l:
                    next_channels.append(channel_l.pop(0))
        elif isinstance(channels, list):
            for channel in channels:
                next_channels.append(channel)
                channels.remove(channel)

        if not next_channels:
            if scrape_config.REC_AUD_BY_PYAUDIO:
                recorder.complete_audio_recording()
            dns_sniffer_stop()
            log("Scrapping finished. Terminating the crawl")
            break

        cntr = 0
        failure_count = 0
        reboot_device = False
        for channel in next_channels:
            if failure_count > scrape_config.FAILURE_CUTOFF:
                if scrape_config.SEND_EMAIL_AFTER_CRAWL:
                    log('Sending notification email for failures.')
                    email_msg = "Crawl %s had %s failures in a row. " \
                                "Stopping the crawl!!\r\n" %\
                                (scrape_config.DATA_DIR, str(failure_count))
                    send_alert_email("[Crawl Failure - Stopping!!]", email_msg)
                channels = []
                break
            if failure_count > 0 and failure_count % 5 == 0:
                reboot_device = True
                if scrape_config.SEND_EMAIL_AFTER_CRAWL:
                    log('Sending notification email for failures.')
                    email_msg = "Crawl %s had %s failures in a row. Rebooting the device if possible.\r\n" %\
                                (scrape_config.DATA_DIR, str(failure_count))
                    send_alert_email("[Crawl Failure]", email_msg)

            if cntr == scrape_config.CUTOFF_TRESHOLD:
                break
            cntr += 1

            if channel['id'] in scraped_channel_ids:
                log('Skipping', channel['id'])
                continue

            channel_res_file = join(scrape_config.DATA_DIR, scrape_config.FIN_CHL_PREFIX,
                                     str(channel['id'])) + ".txt"
            if os.path.isfile(channel_res_file):
                log('Skipping', channel['id'], ' due to:', channel_res_file)
                continue

            scrape_success = pre_auto_scrape(channel, output_file_desc, channel_res_file, date_prefix, reboot_device)
            if scrape_success:
                failure_count = 0
            else:
                failure_count += 1

    if scrape_config.MOVE_TO_NFS:
        subprocess.call('./tools/move-to-nfs/move.sh ' + scrape_config.DATA_DIR + " ~/csportal-mnt/crawl-data/",
                        shell=True)
    if scrape_config.SEND_EMAIL_AFTER_CRAWL:
        log('Sending notification email.')
        email_msg = "Crawl %s finished.\r\n" % (scrape_config.DATA_DIR)
        if scrape_config.MOVE_TO_NFS:
            email_msg += "Crawl results will be moved to NFS."
        send_alert_email("[Crawl Finished]", email_msg)


@timeout(scrape_config.SCRAPE_TO)
def pre_auto_scrape(channel, output_file_desc, channel_res_file, date_prefix, reboot_device):
    log('Scraping', channel['_category'], '-', channel['id'])
    channel_state = CrawlState.STARTING
    try:
        scrape_success = False
        if scrape_config.THREADED_SCRAPE:
            que = queue.Queue()
            t = PropagatingThread(target=lambda q, arg1, arg2, arg3: q.put(automatic_scrape(arg1, arg2, arg3)),
                                  args=(que, channel['id'], date_prefix, reboot_device, ))

            t.start()
            t.join(timeout=scrape_config.SCRAPE_TO)
            channel_state = que.get()
        else:
            channel_state = automatic_scrape(channel['id'], date_prefix, reboot_device)
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
    return scrape_success

def log(*args):

    s = '[{}] '.format(datetime.today())
    s += ' '.join([str(v) for v in args])

    print(s)
    with open(os.path.join(scrape_config.LOCAL_LOG_DIR , scrape_config.LOG_FILE), 'a') as fp:
        print(s, file=fp)

if scrape_config.REC_AUD_BY_PYAUDIO:
    # Create recorder object
    try:
        recorder = AudioRecorder(log)
        recorder.start()  # Starting audio thread
    except Exception as e:
        log(e)
        log('Error while creating the recorder. Perhaps the device doesn\'t have an audio output cable connected?')
        scrape_config.REC_AUD_BY_PYAUDIO = False


def check_folders():
    for f in scrape_config.folders:
        fullpath = join(scrape_config.DATA_DIR , str(f))
        if not os.path.exists(fullpath):
            print (fullpath + " doesn't exist! Creating it!")
            os.makedirs(fullpath)


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


def detect_playback_using_audio(seconds, surfer):
    if scrape_config.REC_AUD_BY_PYAUDIO:
        return recorder.is_audio_playing(seconds)
    elif scrape_config.REC_AUD_BY_ARECORD:
        # surfer.channel_id
        recent_audio_filename = "%s_most_recent.wav" % surfer.channel_id
        recent_audio_path = join(
            scrape_config.DATA_DIR, scrape_config.AUDIO_PREFIX,
            str(surfer.channel_id), recent_audio_filename)
        return -1 != audio_played_second(recent_audio_path, 5)


def is_video_playing(surfer, seconds=5):
    """Return True if playback is detected by either audio or screenshots.

    `seconds` must be an odd integer, since the audio detection use
    majority voting.
    """
    return detect_playback_using_audio(seconds, surfer) or \
        detect_playback_using_screenshots(surfer)


KEY_SEQUENCES = {
    "ROKU": [
        ["Select", "Select", "Select"],
        ["Down", "Select", "Select"],
        ["Select", "Select", "Down", "Select", "Down", "Select"]
    ],
    "AMAZON": [
        ["Select", "Select", "Select"],
        ["Down", "Select", "Select"],
        ["Select", "Select", "Down", "Select", "Down", "Select"]
    ]
}


def play_key_sequence(surfer, key_sequence, key_seq_idx, launch_idx):
    n_keys = len(key_sequence)
    for idx, key in enumerate(key_sequence, 1):
        surfer.timestamp_event("smartlaunch-%02d-key-seq-%02d-key-%02d" % (launch_idx, key_seq_idx, idx))
        log("SMART_CRAWLER: will press %s (%d of %d)" % (key, idx, n_keys))
        surfer.press_key(key)
        if key == "Select":  # check for playback only after Select
            surfer.capture_screenshots(10)
            if is_video_playing(surfer):
                return True
        elif key == "Down":  # pause for 1s after Down
            surfer.capture_screenshots(1)
    else:
        return False


def fast_forward(surfer):
    """Press FWD to trigger more ads"""
    log("SMART_CRAWLER: will fast forward on channel %s" % surfer.channel_id)
    surfer.press_key('Fwd')
    surfer.capture_screenshots(1)
    surfer.press_key('Fwd')
    surfer.capture_screenshots(1)
    surfer.press_key('Fwd')
    surfer.capture_screenshots(1)
    sleep(scrape_config.FWD_SLEEP_TO)
    log("SMART_CRAWLER: will press Play after fast forwarding on channel %s"
        % surfer.channel_id)
    surfer.press_key('Play')
    surfer.capture_screenshots(30)
    # sleep(30)


def launch_channel_for_mitm_warmup(surfer, retry_count):
    no_new_endpoint_counter = 0
    for launch_idx in range(1, retry_count+1):
        surfer.timestamp_event("launch-" + str(launch_idx).zfill(2))

        if scrape_config.MITM_STOP_NO_NEW_ENDPOINT and launch_idx > 1:
            if isfile(MITM_LEARNED_NEW_ENDPOINT):
                no_new_endpoint_counter = 0
                # we recently learned about a domain, continue
                log("WARMUP_LAUNCH: Found new uninterceptable endpoints! Continuing...")
                remove_file(MITM_LEARNED_NEW_ENDPOINT)
            else:
                no_new_endpoint_counter += 1
                log("WARMUP_LAUNCH: Found no new endpoints in last"
                    " %d rounds!" % no_new_endpoint_counter)
                if no_new_endpoint_counter > 1:
                    # no new domain found recently, stop crawling
                    log("WARMUP_LAUNCH: Found no new endpoints "
                        "twice! Stopping warmup launches!")
                    remove_file(MITM_LEARNED_NEW_ENDPOINT)
                    break
        surfer.launch_channel()
        time.sleep(4)

SCREENSHOT_PROCESS = None
def start_screenshot():
    # On Roku: Start a background process that continuously captures screenshots to
    # the same file: ${LogDir}/continuous_screenshot.png
    if scrape_config.PLAT == "ROKU" or scrape_config.AMAZON_HDMI_SCREENSHOT:
        global SCREENSHOT_PROCESS
        if SCREENSHOT_PROCESS is None:
            cmd = join('./scripts') + '/capture_screenshot.sh'
            log('Starting screenshot process with %s ' % cmd)
            SCREENSHOT_PROCESS = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)

def stop_screenshot():
    if scrape_config.PLAT == "ROKU" or scrape_config.AMAZON_HDMI_SCREENSHOT:
        global SCREENSHOT_PROCESS
        if SCREENSHOT_PROCESS is not None:
            log('Terminating screenshot process with PID %s ' % str(SCREENSHOT_PROCESS))
            os.killpg(os.getpgid(SCREENSHOT_PROCESS.pid), signal.SIGTERM)

NETSTAT_PROCESS = None
def start_netstat(data_dir):
    if scrape_config.PLAT == "AMAZON":
        global NETSTAT_PROCESS
        cmd = join(scrape_config.PLATFORM_DIR, 'scripts') + '/dump_netstat.sh'
        log('Starting netstat process with %s  %s' % (cmd, data_dir))
        NETSTAT_PROCESS = subprocess.Popen(cmd + " " + data_dir, shell=True, preexec_fn=os.setsid)

def stop_netstat():
    if scrape_config.PLAT == "AMAZON":
        global NETSTAT_PROCESS
        if NETSTAT_PROCESS is not None:
            log('Terminating netstat process with PID %s ' % str(NETSTAT_PROCESS))
            os.killpg(os.getpgid(NETSTAT_PROCESS.pid), signal.SIGTERM)
        sleep(1)
        subprocess.call('pkill -2 -f dump_netstat.sh', shell=True, stderr=open(os.devnull, 'wb'))


def setup_channel(channel_id, date_prefix, reboot_device=False):
    log('Setting up channel %s' % str(channel_id))
    err_occurred = False
    surfer = None
    try:
        cleanup_data_folder(scrape_config.DATA_DIR, channel_id)
        check_folders()

        surfer = ChannelSurfer(scrape_config.PLAT,
                               scrape_config.TV_IP_ADDR,
                               scrape_config.TV_SERIAL_NO,
                               channel_id, str(scrape_config.DATA_DIR),
                               str(scrape_config.LOG_PREFIX),
                               str(scrape_config.PCAP_PREFIX), date_prefix,
                               str(scrape_config.SCREENSHOT_PREFIX))
        if reboot_device:
            surfer.reboot_device()
        if scrape_config.MITMPROXY_ENABLED:
            mitmrunner = MITMRunner(channel_id, str(scrape_config.DATA_DIR),
                                    str(scrape_config.DUMP_PREFIX), global_keylog_file,
                                    scrape_config.SSL_STRIP, scrape_config.TLS_INTERCEPT)

        timestamp = int(time.time())
        surfer.capture_packets(timestamp)
        with open(OTT_CURRENT_CHANNEL_FILE, 'w') as f:
            f.write("%s" % channel_id)

        subprocess.call('./scripts/capture_audio.sh&', shell=True)

        if scrape_config.MITMPROXY_ENABLED:
            mitmrunner.clean_iptables()
            mitmrunner.kill_existing_mitmproxy()
    except TimeoutError:
        log('Timeout for crawl expired in setup_channel!')
        raise
    except Exception:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    ret = [err_occurred, surfer]
    if scrape_config.MITMPROXY_ENABLED:
        ret.append(mitmrunner)
    return ret


def install_channel(surfer):
    log('Installing channel %s' % str(surfer.channel_id))
    err_occurred = False
    surfer.timestamp_event("install_channel")
    try:

        surfer.install_channel()
    except SurferAborted as e:
        err_occurred = True
        log('Channel not installed! Aborting scarping of channel')
        if scrape_config.REC_AUD_BY_PYAUDIO:
            audio_file_addr = '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time()))
            recorder.dump(join(scrape_config.DATA_DIR,
                                         str(scrape_config.AUDIO_PREFIX), audio_file_addr))
        elif scrape_config.REC_AUD_BY_ARECORD:
            remove_file(OTT_CURRENT_CHANNEL_FILE)

        surfer.uninstall_channel()
        surfer.kill_all_tcpdump()
    except TimeoutError:
        log('Timeout for crawl expired in install_channel!')
        raise
    except Exception:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    return err_occurred


def launch_mitm(mitmrunner):
    mitmrunner.run_mitmproxy()

def manual_crawl_screenshot(surfer, terminateEvent):
    log("Capturing screenshots every 5 seconds")
    while not terminateEvent.is_set():
        log("Capturing next screenshot")
        surfer.capture_screenshots(1)
        time.sleep(4)


def remove_file(file_path):
    try:
        os.remove(file_path)
    except OSError:
        pass

def smart_crawl(surfer):
    if scrape_config.MITM_STOP_NO_NEW_ENDPOINT:
        no_new_endpoint_counter = 0
        remove_file(MITM_LEARNED_NEW_ENDPOINT)
    playback_detected = False
    n_key_seqs = len(KEY_SEQUENCES[scrape_config.PLAT])
    for launch_idx in range(1, scrape_config.SMART_CRAWLS_CNT + 1):
        if launch_idx > 1 and scrape_config.MITM_STOP_NO_NEW_ENDPOINT:
            if isfile(MITM_LEARNED_NEW_ENDPOINT):
                no_new_endpoint_counter = 0
                # we recently learned about a domain, continue
                log("SMART_CRAWLER: Found new uninterceptable endpoints! Continuing...")
                remove_file(MITM_LEARNED_NEW_ENDPOINT)
            else:
                no_new_endpoint_counter += 1
                log("SMART_CRAWLER: Found no new endpoints in last"
                    " %d rounds!" % no_new_endpoint_counter)
                if no_new_endpoint_counter > 1:
                    # no new domain found recently, stop crawling
                    log("SMART_CRAWLER: Found no new endpoints "
                        "twice! Stopping smart crawl!")
                    remove_file(MITM_LEARNED_NEW_ENDPOINT)
                    break

        for key_seq_idx, key_sequence in enumerate(KEY_SEQUENCES[scrape_config.PLAT], 1):
            surfer.timestamp_event('smartlaunch-%02d-key-seq-%02d' % (launch_idx, key_seq_idx))
            surfer.launch_channel()  # make sure we start from the homepage
            log("SMART_CRAWLER: Launch: %d Will play key seq (%d of %d) for channel:"
                " %s %s" % (launch_idx, key_seq_idx, n_key_seqs, surfer.channel_id,
                            "-".join(key_sequence)))
            playback_detected = play_key_sequence(surfer, key_sequence, key_seq_idx, launch_idx)
            if playback_detected:
                log('SMART_CRAWLER: Playback detected on channel: %s' %
                    surfer.channel_id)
                fast_forward(surfer)
                break

            time.sleep(4)
        else:
            log('SMART_CRAWLER: Cannot detect playback on channel: %s' %
                surfer.channel_id)

def crawl_channel(surfer, mitmrunner, manual_crawl=False):
    log('Launching channel %s' % surfer.channel_id)
    if manual_crawl:
        if scrape_config.MITMPROXY_ENABLED:
            launch_mitm(mitmrunner)

        time.sleep(5)
        surfer.launch_channel()
        terminateEvent = Event()
        p = Process(target=manual_crawl_screenshot, args=(surfer, terminateEvent,))
        p.start()
        return terminateEvent, p
    else:
        err_occurred = False
        try:
            if scrape_config.REC_AUD_BY_PYAUDIO:
                recorder.start_recording(scrape_config.SCRAPE_TO, surfer.channel_id)

            if scrape_config.MITMABLE_DOMAINS_WARM_UP_CRAWL:
                launch_channel_for_mitm_warmup(surfer, scrape_config.LAUNCH_RETRY_CNT)
            else:
                surfer.timestamp_event("launch")

            time.sleep(scrape_config.SLEEP_TIMER)
            if scrape_config.ENABLE_SMART_CRAWLER:
                smart_crawl(surfer)
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

            if scrape_config.REC_AUD_BY_PYAUDIO:
                audio_file_addr = '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time()))
                recorder.dump(join(scrape_config.DATA_DIR, str(scrape_config.AUDIO_PREFIX), audio_file_addr))
            elif scrape_config.REC_AUD_BY_ARECORD:
                remove_file(OTT_CURRENT_CHANNEL_FILE)

            surfer.uninstall_channel()
            surfer.kill_all_tcpdump()
        except TimeoutError:
            log('Timeout for crawl expired in launch_channel!')
            raise
        except Exception:
            err_occurred = True
            log('Error!')
            traceback.print_exc()
        return err_occurred

def cleanup_data_folder(data_dir, channel_id):
    for filename in glob.iglob(data_dir + '/**/' + str(channel_id) + '-*', recursive=True):
        log('Removing existing file %s for channel %s.' % (filename, channel_id))
        os.remove(filename)


def terminate_and_collect_data(surfer, mitmrunner, date_prefix):
    log('Collecting data for channel %s' % str(surfer.channel_id))
    surfer.timestamp_event("terminate")

    err_occurred = False
    try:
        if scrape_config.MITMPROXY_ENABLED:
            try:
                mitmrunner.kill_mitmproxy()
            except Exception as e:
                log('Error killing MTIM!')
                traceback.print_exc()

        if scrape_config.REC_AUD_BY_PYAUDIO:
            audio_file_addr = '%s.wav' % '{}-{}'.format(surfer.channel_id, int(time.time()))
            err_occurred = recorder.dump(join(scrape_config.DATA_DIR,
                                              str(scrape_config.AUDIO_PREFIX), audio_file_addr))
            if err_occurred:
                log('Audio returned error!')
        elif scrape_config.REC_AUD_BY_ARECORD:
            remove_file(OTT_CURRENT_CHANNEL_FILE)

        surfer.kill_all_tcpdump()
        time.sleep(3)
        surfer.go_home()
        surfer.uninstall_channel()
        surfer.deduplicate_screenshots()
        surfer.terminate_rrc()
        dump_redis(join(scrape_config.DATA_DIR, scrape_config.DB_PREFIX), date_prefix)
        surfer.write_timestamps()
        #dump_as_json(timestampsn(scrape_config.DATA_DIR, scrape_config.LOG_PREFIX,
        #                              "%s_timestamps.json" % channel_id))
    except TimeoutError:
        log('Timeout for crawl expired in collect_data!')
        raise
    except Exception:
        err_occurred = True
        log('Error!')
        traceback.print_exc()
    return err_occurred

def automatic_scrape(channel_id, date_prefix, reboot_device):
    try:
        channel_state = CrawlState.PREINSTALL
        if reboot_device:
            ret = setup_channel(channel_id, date_prefix, reboot_device)
        else:
            ret = setup_channel(channel_id, date_prefix)
        err_occurred = ret[0]
        if not err_occurred:
            surfer = ret[1]
            if scrape_config.MITMPROXY_ENABLED:
                mitmrunner = ret[2]
            else:
                mitmrunner = None
            channel_state = CrawlState.INSTALLING
            err_occurred = install_channel(surfer)
            if not err_occurred:
                channel_state = CrawlState.LAUNCHING
                if scrape_config.MITMPROXY_ENABLED:
                    launch_mitm(mitmrunner)
                err_occurred = crawl_channel(surfer, mitmrunner)
                if not err_occurred:
                    channel_state = CrawlState.TERMINATING
                    err_occurred = terminate_and_collect_data(surfer, mitmrunner, date_prefix)
                    if not err_occurred:
                        channel_state = CrawlState.TERMINATED
    except TimeoutError:
        log('Timeout for crawl expired! Ending scrape for channel %s' % channel_id)
    except:
        log('Error!')
        traceback.print_exc()
    if err_occurred:
        log('Error occured during scraping channel %s' % channel_id)
    return channel_state


def flushall_iptables():
    log("Flushing all iptables")
    subprocess.call('./scripts/iptables_flush_all.sh', shell=True)


def send_alert_email(subject, msg):
    fromaddr = 'abbbbbba23@gmail.com'
    toaddrs = ['hoomanm@princeton.edu', 'gunes@princeton.edu', 'yuxingh@cs.princeton.edu']
    msg = 'Subject: %s\n\n%s' % (subject, msg)
    # Credentials (if needed)
    username = 'abbbbbba23@gmail.com'
    password = 'Abbbbbba1'  # TODO change it

    # The actual mail send
    server = SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username, password)
    log('Sending notification email to ' + str(toaddrs))
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

if __name__ == '__main__':
    start_screenshot()
    flushall_iptables()
    start_netstat(scrape_config.DATA_DIR)
    if len(sys.argv) > 1:
        if isfile(os.path.abspath(sys.argv[1])):
            main(sys.argv[1])
        else:
            channel_id = int(sys.argv[1])
            date_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")
            automatic_scrape(channel_id, date_prefix)
    else:

        main()
    #NOTE: This doesn't terminate child processes
    # executed with Popen! They remain running!
    stop_netstat()
    stop_screenshot()
    sys.exit(1)

