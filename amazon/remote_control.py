"""
Amazon Remote Control emulator.

Prerequisites:

 - Install adb
 - Test adb connection to your Amazon device:
     adb connect [ip_addr]
     adb devices
 - Run this script!

"""


import subprocess as sp
import sys
import time
import requests
import os


class AmazonRemoteControl(object):

    def __init__(self, ip_address):
        """Connects to Fire TV via ADB."""

        # Test whether prerequisite software has been installed
        assert sp.call(['which', 'adb']) == 0

        # Connect to device
        ret = self.adb('connect', ip_address)[1]
        assert ret.startswith('connected') or \
            ret.startswith('already connected')

        print 'Initialized:', ret.strip()

    def press_key(self, key_name):
        """Sends a key to Fire TV via ADB. May not be reliable."""

        if key_name == 'Select':
            key_number = 66
        elif key_name == 'Home':
            key_number = 3
        elif key_name == 'Up':
            key_number = 19
        elif key_name == 'Down':
            key_number = 20
        elif key_name == 'Left':
            key_number = 21
        elif key_name == 'Right':
            key_number = 22
        elif key_name == 'Back':
            key_number = 4
        else:
            raise RuntimeError('Invalid key_name')

        time.sleep(1)
        self.adb('shell', 'input', 'keyevent', str(key_number))
        time.sleep(1)

    def get_channel_list(self):
        """Returns a dictionary of all available channels for install."""

        channel_list = {}

        apk_list = requests.get(
            'https://iot-inspector.princeton.edu/fire-tv/apk_list.txt'
        ).text

        for apk_id in apk_list.split():
            channel_list[apk_id] = {
                'id': apk_id,
                'type': 'Unknown',
                'subtype': 'Unknown',
                'version': 'Unknown',
                'name': apk_id
            }

        return channel_list

    def _download_apk(self, apk_id):
        """Downloads APK to ./apk_cache/ if already not so."""

        sp.call(['mkdir', '-p', 'apk_cache'])

        target_path = os.path.join('apk_cache', apk_id + '.apk')
        if os.path.isfile(target_path):
            return

        sp.call([
            'curl',
            'https://iot-inspector.princeton.edu/fire-tv/apks/' + apk_id,
            '--output',
            target_path
        ])

    def install_channel(self, apk_id):
        """
        Installs channel by APK ID.

        Please run is_installed(apk_id) to confirm the channel is installed.

        """
        self._download_apk(apk_id)

        if not self.is_installed(apk_id):
            self.adb(
                'install', '-r', os.path.join('apk_cache', apk_id + '.apk')
            )

    def is_installed(self, apk_id):
        """Checks if a particular APK is installed."""

        return apk_id in self.get_installed_channels()

    def launch_channel(self, apk_id):
        """
        Launches a channel.

        May not be reliable. Check with get_current_window to make sure that
        the channel is open.

        """
        self.adb(
            'shell', 'monkey', '-p', apk_id,
            '-c', 'android.intent.category.LAUNCHER', '1'
        )

    def uninstall_channel(self, apk_id):
        """
        Uninstalls channel.

        Please run is_installed(apk_id) to confirm the channel is uninstalled.

        """
        self.adb('uninstall', apk_id)

    def get_installed_channels(self, check_all_channels=False):
        """Returns a dictionary that maps APK ID to the APK's path."""

        ret = self.adb('shell', 'pm', 'list', 'packages', '-f')[1]

        apk_dict = {}

        for line in ret.split('\n'):
            line = line.strip()
            if not line:
                continue
            if not check_all_channels:
                if not line.startswith('package:/data/app/'):
                    continue
                if line.startswith('package:/data/app/com.amazon'):
                    continue
            line = line.replace('package:', '')
            apk_path, apk_id = line.split('=')
            apk_dict[apk_id] = apk_path

        return apk_dict

    def get_current_window(self):
        """
        Returns (active_apk_id, activity_name), or None if unknown.

        """
        while True:

            ret = self._get_current_window_helper()
            if ret is None:
                time.sleep(1)
            else:
                return ret

    def _get_current_window_helper(self):

        _, ret = self.adb('shell', 'dumpsys', 'window', 'windows')
        for line in ret.split('\n'):
            if 'mCurrentFocus' in line:
                try:
                    tokens = line.strip().split()
                    apk_id_and_activity = tokens[-1].replace('}', '')
                    apk_id, activity = apk_id_and_activity.split('/')
                    return (apk_id, activity)
                except (IndexError, ValueError):
                    return None

        return None

    def adb(self, *command_list):
        """Returns (ret_code, stdout)."""

        cmd = ['adb'] + list(command_list)
        proc = sp.Popen(cmd, stdout=sp.PIPE)
        stdout = proc.communicate()[0]

        return (proc.returncode, stdout)

    def take_screenshot(self, filename):

        sp.call(['mkdir', '-p', 'screenshots'])

        filename = os.path.join('screenshots', filename)

        cmd = "adb shell screencap -p | sed 's/\r$//' > %s" % filename
        sp.call(cmd, shell=True)


def test():

    try:
        fire_stick_ip = sys.argv[1]
    except Exception:
        print 'Enter the IP address of the Fire Stick in the argument.'
        return

    rc = AmazonRemoteControl(fire_stick_ip)

    rc.press_key('Home')
    print rc.get_current_window()

    print 'All available channels:'
    print rc.get_channel_list().keys()

    for apk_id in rc.get_channel_list():

        print 'Installing channel:', apk_id
        rc.install_channel(apk_id)

        while not rc.is_installed(apk_id):
            time.sleep(1)
            print 'Waiting for installation to complete.'

        rc.launch_channel(apk_id)

        while rc.get_current_window()[0] != apk_id:
            time.sleep(1)
            print 'Waiting for channel to open.'

        print 'Channel is open.'
        time.sleep(2)

        print 'Taking screenshot'
        rc.take_screenshot(apk_id + '.png')

        print 'Uninstalling.'

        rc.uninstall_channel(apk_id)
        while rc.is_installed(apk_id):
            time.sleep(1)
            print 'Waiting for uninstallation to complete.'

        print 'Done.'


if __name__ == '__main__':
    test()
