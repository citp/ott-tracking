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


LOG_FILE = 'channel_surfer.log'
INSTALL_RETRY_CNT = 10


class SurferAborted(Exception):
    """Raised when we encounter an error while surfing this channel."""
    pass


class ChannelSurfer(object):

    def __init__(self, roku_ip, channel_id, data_dir, pcap_prefix, crawl_folder, screenshot_folder):

        self.pcap_filename = None
        self.rrc = RokuRemoteControl(roku_ip)
        self.channel_id = str(channel_id)
        self.data_dir = data_dir + "/"
        self.pcap_dir = self.data_dir  + str(pcap_prefix)
        self.screenshot_folder = self.data_dir + str(screenshot_folder)
        self.go_home()
        self.log('Initialized', channel_id)
        self.crawl_folder = crawl_folder
        self.launch_iter = 1
        self.last_screenshot_crc = 0

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
        return self.channel_id in channel_dict

    def channel_is_active(self):
        active_channel = self.rrc.get_active_channel()
        print("Active Channel is " + str(active_channel)) 
        return self.channel_id == str(active_channel)

    def install_channel(self):

        if self.channel_is_installed():
            self.log('Not installing channel as it already exists.')
            return

        self.log('Installing channel.')

        iter = 0
        while iter < INSTALL_RETRY_CNT:
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

        while time.time() - start_time <= timeout:
            screenshot_filename = self.screenshot_folder + '{}-{}'.format(self.pcap_filename, int(time.time()))
            #self.log('Taking screenshot to:', screenshot_filename)
            subprocess.call(
                './capture_screenshot.sh {}'.format(screenshot_filename),
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.deduplicate_screenshots(screenshot_filename)

    def deduplicate_screenshots(self, screenshot_filename):
        if os.path.exists(screenshot_filename):
            screenshot_crc = binascii.crc32(open(screenshot_filename, 'rb').read())
            if screenshot_crc == self.last_screenshot_crc:
                self.log('Will remove duplicate screenshot:', screenshot_filename)
                os.remove(screenshot_filename)

            self.last_screenshot_crc = screenshot_crc

    def kill_all_tcpdump(self):

        subprocess.call('pkill -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))
        time.sleep(5)
        subprocess.call('pkill -9 -f tcpdump', shell=True, stderr=open(os.devnull, 'wb'))

    def rsync(self):
        time.sleep(3)

        rsync_command = str('rsync -rlptDv --remove-source-files ' +
                            str(self.data_dir) +
                            ' hoomanm@portal.cs.princeton.edu:/n/fs/iot-house/hooman/crawl-data/' +
                            self.crawl_folder)
        print (rsync_command)
        #p = subprocess.Popen(
        p = subprocess.run(
            rsync_command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        self.log("rsync return code: " + str(p.returncode))
