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
import json
import glob
from shutil import copy2
from os.path import join
import fcntl, socket, struct
import scrape_config


LOCAL_LOG_DIR = os.getenv("LogDir")
LOG_FILE = 'channel_surfer.log'
INSTALL_RETRY_CNT = 4
LOG_CRC_EN = True

#PLAT = os.getenv("PLATFORM")
ADB_PORT_NO = "5555"


def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', bytes(ifname[:15], 'utf-8')))
    return ''.join(['%02x:' % b for b in info[18:24]])[:-1]

def dump_as_json(obj, json_path):
    with open(json_path, 'w') as f:
        json.dump(obj, f, indent=2)

class SurferAborted(Exception):
    """Raised when we encounter an error while surfing this channel."""
    pass

class ChannelSurfer(object):

    def __init__(self, platform, tv_ip, channel_id, data_dir, log_prefix ,pcap_prefix,
                 date_prefix, screenshot_folder):

        self.pcap_filename = None
        self.platform = platform
        if self.platform == "ROKU":
            self.rrc = RokuRemoteControl(tv_ip)
        elif self.platform == "AMAZON":
            self.rrc = AmazonRemoteControl(tv_ip)
        self.tv_ip = tv_ip
        self.channel_id = str(channel_id)
        self.data_dir = data_dir + "/"
        self.pcap_dir = self.data_dir  + str(pcap_prefix)
        self.log_dir = join(self.data_dir  + str(log_prefix))
        self.screenshot_folder = self.data_dir + str(screenshot_folder)
        self.go_home()
        self.log('Initialized', channel_id)
        self.date_prefix = date_prefix
        self.launch_iter = 1
        self.last_screenshot_crc = 0
        self.tcpdump_proc = None
        self.event_timestamps = []


    def log(self, *args):

        current_time = '[{}]'.format(datetime.datetime.today())

        with open(os.path.join(LOCAL_LOG_DIR , LOG_FILE), 'a') as fp:
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

        mac_filter = ' ether host ' +  wlan_eth_mac
        protocol_filter = ' and not arp and port not ssh'
        if self.platform == "ROKU":
            host_filter = ' and host ' + self.tv_ip
        elif self.platform == "AMAZON":
            #Filter out ADB packets
            host_filter = ' and (' +\
                          '(src ' + self.tv_ip + ' and not src port ' + ADB_PORT_NO +')'+\
                          ' or '+\
                          '(dst '  + self.tv_ip + ' and not dst port ' + ADB_PORT_NO +')' +\
                          ')'

        command = ['tcpdump', '-w', pcap_path, '-i', wlan_if_name] +\
                     mac_filter.split() + protocol_filter.split() + host_filter.split()

        self.tcpdump_proc = subprocess.Popen(command,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        self.log("tcpdump command executed: "+ " ".join(command))
        self.log("tcpdump >> " + self.tcpdump_proc.stdout.readline().decode("utf-8").rstrip())

        #self.log('./start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename))
        #subprocess.Popen(
        #    './start_pcap.sh ' + str(self.pcap_dir) + "/" + str(self.pcap_filename),
        #    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.log('Capturing packets:', self.pcap_filename)

    def timestamp_event(self, event_name):
        self.event_timestamps.append((event_name, time.time()))

    def write_timestamps(self):
        timestamp_file_path = join(self.log_dir,
             "%s-timestamps.txt" % self.channel_id)
        self.log("Writing timestamps to %s" %  timestamp_file_path)
        with open(timestamp_file_path, "w") as f:
            for event, timestamp in self.event_timestamps:
                f.write("%s,%s\n" % (event, timestamp))


    def capture_screenshots(self, timeout):

        start_time = time.time()
        err_reported = False

        while time.time() - start_time <= timeout:
            t_loop_begin = time.time()
            if self.platform == "ROKU" or scrape_config.AMAZON_HDMI_SCREENSHOT:
                # Find all the screenshots, sorted by creation time
                screenshot_list = []
                for screenshot_raw_file in os.listdir(LOCAL_LOG_DIR):
                    if screenshot_raw_file.startswith('continuous_screenshot-') and screenshot_raw_file.endswith(
                            '.png'):
                        screenshot_list.append(screenshot_raw_file)
                screenshot_list.sort()

                # Wait till we have at least two screenshot files
                if len(screenshot_list) < 2:
                    time.sleep(0.5)
                    continue

                # The screenshot we need is the 2nd latest file
                second_latest_file = screenshot_list[-2]
                FFMPEG_SCREENSHOT_NAME = os.path.join(LOCAL_LOG_DIR, second_latest_file)

                # Extract the unix timestamp from the screenshot's filename (assuming that we're on Eastern Time)
                human_timestamp = second_latest_file.replace('continuous_screenshot-', '').replace('.png', '')
                t0 = int((datetime.datetime.strptime(human_timestamp, '%Y-%m-%d_%H-%M-%S') - datetime.datetime(1969, 12,
                                                                                                               31, 20,
                                                                                                               0)).total_seconds())
                screenshot_filename = join(
                    self.screenshot_folder,
                    '{}-{}.png'.format(self.channel_id, int(t0)))
                # self.log('Taking screenshot to:', screenshot_filename)

                # capture_screenshot.sh continuously writes the latest screenshot
                # images to continuous_screenshot
                if os.path.exists(FFMPEG_SCREENSHOT_NAME):
                    copy2(FFMPEG_SCREENSHOT_NAME, screenshot_filename)
                else:
                    if not err_reported:
                        self.log("Error! Screenshot file %s is missing." % FFMPEG_SCREENSHOT_NAME)
                        err_reported = True
            elif self.platform == "AMAZON":
                screenshot_filename = join(
                    self.screenshot_folder,
                    '{}-{}.png'.format(self.channel_id, int(t0)))
                # self.log('Taking screenshot to:', screenshot_filename)
                self.rrc.take_screenshot(screenshot_filename)

            time.sleep(max([0, 1-(time.time() - t_loop_begin)]))  # try to spend 1s on each loop


    def deduplicate_screenshots(self, screenshot_filename):
        if scrape_config.DEDUPLICATE_SCREENSHOTS:
            self.log("Deduplicating screenshots!")
            for screenshot_filename in sorted(glob.iglob(join(self.data_dir, self.screenshot_folder) +
                                       "/" + str(self.channel_id) + '*.png', recursive=True)):
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
        time.sleep(5)
        subprocess.call('pkill -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))
        # time.sleep(5)
        subprocess.call('pkill -9 -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))
        # time.sleep(5)

    def terminate_rrc(self):
        self.rrc.terminate()

