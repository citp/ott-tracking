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
from shutil import copy2
from os.path import join
from shlex import split
import fcntl, socket, struct

LOG_DIR = os.getenv("LogDir")
LOG_FILE = 'channel_surfer.log'
INSTALL_RETRY_CNT = 4
LOG_CRC_EN = False

PLAT = os.getenv("PLATFORM")
PLATFORM_DIR = os.getenv("PLATFORM_DIR")


def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', bytes(ifname[:15], 'utf-8')))
    return ''.join(['%02x:' % b for b in info[18:24]])[:-1]

class SurferAborted(Exception):
    """Raised when we encounter an error while surfing this channel."""
    pass

class ChannelSurfer(object):

    def __init__(self, tv_ip, channel_id, data_dir, pcap_prefix, date_prefix, screenshot_folder):

        self.pcap_filename = None
        if PLAT == "ROKU":
            self.rrc = RokuRemoteControl(tv_ip)
        elif PLAT == "AMAZON":
            self.rrc = AmazonRemoteControl(tv_ip)
        self.channel_id = str(channel_id)
        self.data_dir = data_dir + "/"
        self.pcap_dir = self.data_dir  + str(pcap_prefix)
        self.screenshot_folder = self.data_dir + str(screenshot_folder)
        self.go_home()
        self.log('Initialized', channel_id)
        self.date_prefix = date_prefix
        self.launch_iter = 1
        self.last_screenshot_crc = 0
        self.tcpdump_proc = None

        # On Roku: Start a background process that continuously captures screenshots to
        # the same file: ${LogDir}/continuous_screenshot.png
        if PLAT == "ROKU":
            subprocess.Popen(join(PLATFORM_DIR, 'scripts') + '/capture_screenshot.sh', shell=True)

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
        for i in range(3):
            self.rrc.press_key('Home')
        time.sleep(2)

    def channel_is_installed(self):

        channel_dict = self.rrc.get_installed_channels()
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

    def press_key(self, key):
        self.log('Pressing %s' % key)
        self.rrc.press_key(key)

    def capture_packets(self, timestamp):

        self.kill_all_tcpdump()

        time.sleep(3)

        self.pcap_filename = '{}-{}.pcap'.format(
            self.channel_id,
            int(timestamp)
        )
        #eth_mac = os.environ['ETH_MAC_ADDRESS']
        #lan_if_name = os.environ['LANIF']

        wlan_if_name = os.environ['WLANIF']
        try:
            wlan_eth_mac = getHwAddr(wlan_if_name)
        except:
            self.log("Error! Getting MAC Addr failed for interface " + str(wlan_if_name))
            wlan_if_name = ""

        pcap_path = join(str(self.pcap_dir), str(self.pcap_filename))
        # tcpdump -v -w "$1".pcap -i ${LANIF} ether host $ETH_MAC_ADDRESS and not arp and port not ssh

        command = ['tcpdump', '-w', pcap_path, '-i', wlan_if_name, 'ether',  'host',
                   wlan_eth_mac] + split(' and not arp and port not ssh')
        self.tcpdump_proc = subprocess.Popen(command,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        self.log("tcpdump command executed: "+ " ".join(command))
        self.log("tcpdump >> " + self.tcpdump_proc.stdout.readline().decode("utf-8").rstrip())

        #self.log('./start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename))
        #subprocess.Popen(
        #    './start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename),
        #    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.log('Capturing packets:', self.pcap_filename)

    def capture_screenshots(self, timeout):

        start_time = time.time()
        err_reported = False
        FFMPEG_SCREENSHOT_NAME = os.path.join(LOG_DIR, 'continuous_screenshot.png')
        while time.time() - start_time <= timeout:
            t0 = time.time()
            screenshot_filename = join(
                self.screenshot_folder,
                '{}-{}.png'.format(self.channel_id, int(t0)))
            #self.log('Taking screenshot to:', screenshot_filename)

            # capture_screenshot.sh continuously writes the latest screenshot
            # images to continuous_screenshot
            if PLAT == "ROKU":
                if os.path.exists(FFMPEG_SCREENSHOT_NAME):
                    copy2(FFMPEG_SCREENSHOT_NAME, screenshot_filename)
                else:
                    if not err_reported:
                        self.log("Error! Screenshot file %s is missing." % FFMPEG_SCREENSHOT_NAME)
                        err_reported = True
            elif PLAT == "AMAZON":
                self.rrc.take_screenshot(screenshot_filename)

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

    def terminate_rrc(self):
        self.rrc.terminate()

