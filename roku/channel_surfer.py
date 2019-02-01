"""
Installs a single channel. Interacts with it. Uninstalls it.

Captures packets at every stage.

"""
from __future__ import print_function
from roku_remote import RokuRemoteControl
import time
import subprocess
import datetime
import os
import binascii
import sounddevice as sd
import soundfile as sf
import threading
from shutil import copy2

LOG_FILE = 'channel_surfer.log'
INSTALL_RETRY_CNT = 4
RECORD_FS = 44100
LOG_CRC_EN = False
LOG_AUD_EN = True

class SurferAborted(Exception):
    """Raised when we encounter an error while surfing this channel."""
    pass


class ChannelSurfer(object):

    def __init__(self, roku_ip, channel_id, data_dir, pcap_prefix, date_prefix, screenshot_folder, audio_prefix):

        self.pcap_filename = None
        self.rrc = RokuRemoteControl(roku_ip)
        self.channel_id = str(channel_id)
        self.data_dir = data_dir + "/"
        self.pcap_dir = self.data_dir  + str(pcap_prefix)
        self.screenshot_folder = self.data_dir + str(screenshot_folder)
        self.go_home()
        self.log('Initialized', channel_id)
        self.date_prefix = date_prefix
        self.audio_dir = self.data_dir + str(audio_prefix)
        self.launch_iter = 1
        self.last_screenshot_crc = 0

        # Start a background process that continuously captures screenshots to
        # the same file: continuous_screenshot.png
        subprocess.call('./capture_screenshot.sh', shell=True)

    def log(self, *args):

        current_time = '[{}]'.format(datetime.datetime.today())

        with open(LOG_FILE, 'a') as fp:
            print(current_time, end=' ', file=fp)
            print(current_time, end=' ')
            for arg in args:
                print(arg, end=' ', file=fp)
                print(arg, end=' ')
            print('', file=fp)
            print('')

    def go_home(self):

        time.sleep(2)
        self.rrc.press_key('Home')
        time.sleep(2)

    def channel_is_installed(self):

        channel_dict = self.rrc.get_channel_list()
        if channel_dict == None:
            print("Channel list did not return!")
            return False
        return self.channel_id in channel_dict

    def channel_is_active(self):
        active_channel = self.rrc.get_active_channel()
        if active_channel == None:
            print("Active channel did not return!")
            return False
        print("Active Channel is " + str(active_channel))
        return self.channel_id == str(active_channel)

    def install_channel(self):

        if self.channel_is_installed():
            self.log('Not installing channel as it already exists.')
            return

        self.log('Installing channel.')

        iter = 0
        while iter < INSTALL_RETRY_CNT:
            self.log('Installing channel. Attempt %s' % str(iter+1))
            if self.channel_is_installed():
                break
            self.go_home()
            self.rrc.install_channel(self.channel_id)

            for _ in range(60):
                time.sleep(1)
                if self.channel_is_installed():
                    break

            self.go_home()
            iter += 1

        if self.channel_is_installed():
            self.log('Channel successfully installed.')
        else:
            self.log('Unable to install channel. Aborted.')
            raise SurferAborted

    def uninstall_channel(self):

        self.log('Uninstalling channel.')

        if not self.channel_is_installed():
            self.log('Uninstalling a non-existent channel. Aborted.')
            return
            #raise SurferAborted

        self.go_home()

        self.rrc.uninstall_channel(self.channel_id)

        for _ in range(60):
            time.sleep(1)
            if not self.channel_is_installed():
                break

        self.go_home()

        if not self.channel_is_installed():
            self.log('Channel successfully uninstalled.')
        else:
            self.log('Unable to uninstall channel. Aborted.')
            #raise SurferAborted

    def launch_channel(self):

        if not self.channel_is_installed():
            self.log('Cannot launch a non-existent channel.')
            raise SurferAborted

        self.log('Launching channel. Attempt %s' % self.launch_iter)

        self.go_home()

        self.rrc.launch_channel(self.channel_id)

        self.launch_iter += 1
        time.sleep(1)

    def press_select(self):

        self.log('Pressing the Select button.')

        self.rrc.press_key('Select')

    def capture_packets(self, timestamp):

        self.kill_all_tcpdump()

        time.sleep(3)

        self.pcap_filename = '{}-{}'.format(
            self.channel_id,
            int(timestamp)
        )

        #self.log('./start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename))
        subprocess.Popen(
            './start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )

        self.log('Capturing packets:', self.pcap_filename)

    def capture_screenshots(self, timeout):

        start_time = time.time()
        FFMPEG_SCREENSHOT_NAME = 'continuous_screenshot.png'
        while time.time() - start_time <= timeout:
            t0 = time.time()
            screenshot_filename = self.screenshot_folder + '{}-{}'.format(self.pcap_filename, int(time.time()))
            #self.log('Taking screenshot to:', screenshot_filename)

            # capture_screenshot.sh continuously writes the latest screenshot
            # images to continuous_screenshot
            copy2(FFMPEG_SCREENSHOT_NAME, screenshot_filename)
            self.deduplicate_screenshots(screenshot_filename)
            time.sleep(max([0, 1-(time.time() - t0)]))  # try to spend 1s on each loop

    def deduplicate_screenshots(self, screenshot_filename):
        if os.path.exists(screenshot_filename):
            screenshot_crc = binascii.crc32(open(screenshot_filename, 'rb').read())
            if screenshot_crc == self.last_screenshot_crc:
                if LOG_CRC_EN:
                    self.log('Will remove duplicate screenshot:', screenshot_filename)
                os.remove(screenshot_filename)

            self.last_screenshot_crc = screenshot_crc

    def start_audio_recording(self, seconds):
        def record(seconds):
            if LOG_AUD_EN:
                self.log('Starting audio recording!')

            try:
                recording = sd.rec(int(seconds * RECORD_FS), samplerate=RECORD_FS, channels=2)
            except:
                self.log('Exception while beginning audio recording.')
                return

            if LOG_AUD_EN:
                self.log('Audio recording started with value', str(recording))

            try:
                sd.wait()
            except:
                self.log('Exception while waiting for audio recording.')
                return

            audio_name = '%s.wav' % '{}-{}'.format(self.channel_id, int(time.time()))

            if LOG_AUD_EN:
                self.log('Writing audio file to:', audio_name)

            try:
                sf.write(self.audio_dir + audio_name, recording, RECORD_FS)
            except:
                self.log('Exception while writing audio recording to file.')
                return

            if LOG_AUD_EN:
                self.log('Finished writing audio file: ', audio_name)

        thread = threading.Thread(target=record, args=[seconds])
        thread.start()

    def kill_all_tcpdump(self):

        subprocess.call('pkill -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))
        time.sleep(5)
        subprocess.call('pkill -9 -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))
        time.sleep(5)

