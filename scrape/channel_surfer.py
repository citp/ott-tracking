"""
Installs a single channel. Interacts with it. Uninstalls it.

Captures packets at every stage.

"""
from __future__ import print_function
from platforms.roku.roku_remote import RokuRemoteControl
from platforms.amazon.remote_control import AmazonRemoteControl
import time
import subprocess
import datetime
import os
import binascii
import threading
from shutil import copy2
from os.path import join
from shlex import split
import wave
import pyaudio

LOG_DIR = os.getenv("LogDir")
LOG_FILE = 'channel_surfer.log'
INSTALL_RETRY_CNT = 4
LOG_CRC_EN = False
LOG_AUD_EN = True

CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

PLATFORM_DIR = os.getenv("PLATFORM_DIR")

class SurferAborted(Exception):
    """Raised when we encounter an error while surfing this channel."""
    pass


class ChannelSurfer(object):

    def __init__(self, roku_ip, channel_id, data_dir, pcap_prefix, date_prefix, screenshot_folder, audio_prefix):

        self.pcap_filename = None
        self.rrc = RokuRemoteControl(roku_ip)
        #self.rrc = AmazonRemoteControl(roku_ip)
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
        self.tcpdump_proc = None

        # Start a background process that continuously captures screenshots to
        # the same file: ${LogDir}/continuous_screenshot.png
        subprocess.call(join(PLATFORM_DIR, 'scripts') + '/capture_screenshot.sh', shell=True)

    def log(self, *args):

        current_time = '[{}]'.format(datetime.datetime.today())

        with open(os.path.join(LOG_DIR , LOG_FILE), 'a') as fp:
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

            for _ in range(12):
                time.sleep(5)
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

        self.pcap_filename = '{}-{}.pcap'.format(
            self.channel_id,
            int(timestamp)
        )
        eth_mac = os.environ['ETH_MAC_ADDRESS']
        lan_if_name = os.environ['LANIF']

        pcap_path = join(str(self.pcap_dir), str(self.pcap_filename))
        # tcpdump -v -w "$1".pcap -i ${LANIF} ether host $ETH_MAC_ADDRESS and not arp and port not ssh
        self.tcpdump_proc = subprocess.Popen(
            ['tcpdump', '-w', pcap_path, '-i', lan_if_name, 'ether',  'host',
            eth_mac] + split('and not arp and port not ssh'),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        #self.log('./start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename))
        #subprocess.Popen(
        #    './start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename),
        #    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.log('Capturing packets:', self.pcap_filename)

    def capture_screenshots(self, timeout):

        start_time = time.time()
        FFMPEG_SCREENSHOT_NAME = os.path.join(LOG_DIR, 'continuous_screenshot.png')
        while time.time() - start_time <= timeout:
            t0 = time.time()
            screenshot_filename = join(
                self.screenshot_folder,
                '{}-{}.png'.format(self.channel_id, int(t0)))
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
                self.log('Opening audio stream.')

            p = None
            stream = None
            frames = None

            try:
                p = pyaudio.PyAudio()
                SPEAKERS = p.get_default_output_device_info()['hostApi']
                stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, input_host_api_specific_stream_info=SPEAKERS)
            except:
                self.log('Exception while opening audio stream.')
                return

            if LOG_AUD_EN:
                self.log('Successfully opened audio stream.')

            try:
                frames = []

                for i in range(0, int(RATE / CHUNK * seconds)):
                    stream.get_output_latency() #No-op but please do not remove this
                    data = stream.read(CHUNK)
                    frames.append(data)

                if LOG_AUD_EN:
                    self.log('Completed reading audio data.')

                stream.stop_stream()
                stream.close()
                p.terminate()

                if LOG_AUD_EN:
                    self.log('Successfully closed audio stream.')

            except:
                self.log('Exception while reading the audio stream.')
                return

            audio_name = '%s.wav' % '{}-{}'.format(self.channel_id, int(time.time()))

            if LOG_AUD_EN:
                self.log('Writing audio file to:', audio_name)

            try:
                wf = wave.open(self.audio_dir + audio_name, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
            except:
                self.log('Exception while writing audio recording to file.')
                return

            if LOG_AUD_EN:
                self.log('Finished writing audio file: ', audio_name)

        thread = threading.Thread(target=record, args=[seconds])
        thread.start()

    def kill_all_tcpdump(self):
        if not self.tcpdump_proc:
            return
        self.tcpdump_proc.terminate()
        try:
            self.tcpdump_proc.wait(60)
        except Exception as exc:
            self.log("Error while waiting to terminate tcpdump %s" % exc)
            self.tcpdump_proc.kill()
        else:
            self.log("Successfully terminated tcpdump")

        # subprocess.call('pkill -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))
        # time.sleep(5)
        # subprocess.call('pkill -9 -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))
        # time.sleep(5)
