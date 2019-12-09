"""
Amazon Remote Control emulator.

Prerequisites:

 - Install adb
 - Run this script!

"""
import subprocess as sp
import sys
import time
import os


ADB_DEBUG = False
INSTALL_LIST_DEBUG = False
LOCAL_LOG_DIR = os.getenv("LogDir")
PLATFORM_DIR = os.getenv("PLATFORM_DIR")
LOCAL_LAUNCH_RETYR_COUNT = 3 #this is to avoid internal failures

class AmazonRemoteControl(object):

    def __init__(self, ip_address, serial_number, apk_id):
        """Connects to Fire TV via ADB."""

        # Test whether prerequisite software has been installed
        assert sp.call(['which', 'adb']) == 0

        self._fire_tv_ip_address = ip_address
        self._fire_tv_serial_no = serial_number
        self.apk_id = apk_id
        self.connect()
        self.start_ADB_logcat()
        self.main_activity = ""

    def killall_ADB_logcat(self):
        cmd = "sudo kill -9 `ps aux | grep \"adb logcat\" | awk '{print $2}'`"
        print("Killing existing adb logcat")
        print(cmd)
        sp.call(cmd, shell=True, stderr=open(os.devnull, 'wb'))
        time.sleep(2)

    def start_ADB_logcat(self):
        self.killall_ADB_logcat()
        print("Starting a new adb logcat")
        sp.Popen(os.path.join(PLATFORM_DIR, 'scripts') + '/adb_logcat.sh', shell=True)

    def is_connected(self):
        """Check if we're connected to the Fire device."""
        device_list = self.adb('devices', check_is_connected=False)[1]
        if ADB_DEBUG:
            print(device_list)

        device_ip_connected = self._fire_tv_serial_no in device_list
        device_usb_exist = self._fire_tv_serial_no in device_list

        if device_ip_connected and device_usb_exist:
            self.disconnect_ip()

        # If device is offline, we need to reconnect
        device_usb_connected = device_usb_exist and ("offline" not in device_list)
        return device_ip_connected or device_usb_connected

    def connect(self, max_attempt=10):
        """
        Should be called frequently to make sure we're still connected to the
        Fire TV, which has a tendancy to break off connection once in a while.

        """
        if self.is_connected():
            return
        for _ in range(max_attempt):

            if self.is_connected():
                return

            # Kill adb server and connect
            self.adb('kill-server', check_is_connected=False)
            self.adb('connect', self._fire_tv_ip_address, check_is_connected=False)

            time.sleep(5)

        raise RuntimeError('Unable to connect to Fire TV. Restart Fire TV!')

    def disconnect_ip(self):
        self.adb('disconnect', self._fire_tv_ip_address, check_is_connected=False)

    def press_key(self, key_name):
        """Sends a key to Fire TV via ADB. May not be reliable."""

        # Maintain connection
        self.connect()

        # See also: https://github.com/happyleavesaoc/python-firetv/blob/3dd953376c0d5af502e775ae14ed0afe03224781/firetv/__init__.py#L46
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
        elif key_name == 'Fwd':
            key_number = 87
        elif key_name == 'Play':
            key_number = 85
        elif key_name == 'Power':
            key_number = 26
        else:
            raise RuntimeError('Invalid key_name')

        time.sleep(1)
        self.adb('shell', 'input', 'keyevent', str(key_number))
        time.sleep(1)

    def send_string(self, string):
        self.adb('shell', 'input', 'string', str(string))
        time.sleep(1)

    def _download_apk(self):
        """Downloads APK to ./apk_cache/ if already not so."""
        apk_dir = os.path.join(PLATFORM_DIR, 'apk_cache')

        sp.call(['mkdir', '-p', apk_dir])

        target_path = os.path.join(apk_dir, self.apk_id + '.apk')
        if os.path.isfile(target_path):
            return

        sp.call([
            'curl',
            'https://remote-server-hosting-apks/' + self.apk_id,
            '--output',
            target_path
        ])

    def install_channel(self):
        """
        Installs channel by APK ID.

        Please run is_installed(apk_id) to confirm the channel is installed.

        """
        self._download_apk()

        if not self.is_installed():
            # Maintain connection
            self.connect()
            apk_dir = os.path.join(PLATFORM_DIR, 'apk_cache')

            self.adb(
                'install', '-r', os.path.join(apk_dir, self.apk_id + '.apk')
            )

    def is_installed(self):
        """Checks if a particular APK is installed."""

        return self.apk_id in self.get_installed_channels()

    def identify_main_activity(self):
        activity_str = self.adb(
            'shell', 'pm', 'dump', self.apk_id
        )[1]

        lines = activity_str.splitlines()
        found_main_intent_header = False
        main_activity_list = []
        for l in lines:
            if 'android.intent.action.MAIN:' in l:
                found_main_intent_header = True
                print("Printing activities")
            elif found_main_intent_header and len(l.split()) <= 1:
                break
            elif found_main_intent_header:
                activity_name = l.split()[1]
                print(activity_name)
                main_activity_list.append(activity_name)

        if len(main_activity_list) < 1:
            print('Unable to get main activity for %s' % self.apk_id)
        else:
            print("Total of %s activities found." % str(len(main_activity_list)))

        for main_activity in main_activity_list:
            self.adb(
                'shell', 'am', 'start', '-n', main_activity,
                '-a', 'android.intent.action.MAIN',
                '-c', 'android.intent.category.LAUNCHER'
            )
            time.sleep(2)
            if self.get_active_channel() == self.apk_id:
                self.main_activity = main_activity
                print("Main activity %s results in correct active channel." % main_activity)
                return True
        return False

## Alternative approach:
# Get the MAIN activity either by reading the manifest or through adb:
# adb shell pm dump firetv.bigstartv.love | grep -A 1 MAIN
# Then run the main activity
# adb shell am start  -n firetv.bigstartv.love/com.bigstar.tv.SplashActivity
    def launch_channel(self):
        """
        Launches a channel.

        May not be reliable. Check with get_current_window to make sure that
        the channel is open.

        """
        # Maintain connection
        self.connect()
        #Press power to wake up from sleep
        self.press_key('Power')
        if self.main_activity != "":
            self.adb(
                'shell', 'am', 'start', '-n', self.main_activity,
                '-a', 'android.intent.action.MAIN',
                '-c', 'android.intent.category.LAUNCHER'
            )
        elif not self.identify_main_activity():
            print("Didn't find the Main activity correctly. Trying monkey!")
            self.adb(
                'shell', 'monkey', '-p', self.apk_id,
                '-c', 'android.intent.category.LAUNCHER', '1'
            )
            time.sleep(2)
            if self.get_active_channel() == self.apk_id:
                print('Error launching the channel! Couldn\'t launch the activity!')

    def uninstall_channel(self):
        """
        Uninstalls channel.

        Please run is_installed(apk_id) to confirm the channel is uninstalled.

        """
        # Maintain connection
        self.connect()

        self.adb('uninstall', self.apk_id)

    def get_installed_channels(self, check_all_channels=False):
        """Returns a dictionary that maps APK ID to the APK's path."""

        # Maintain connection
        self.connect()

        ret = self.adb('shell', 'pm', 'list', 'packages', '-f')[1]
        if INSTALL_LIST_DEBUG:
            print(ret)

        apk_dict = {}

        for line in ret.split('\n'):
            line = line.strip()
            if not line:
                continue
            if not check_all_channels:
                if not line.startswith('package:/data/app/'):
                    continue
                if line.startswith('package:/data/app/com.amazon'):
                    if 'com.amazon.rialto' not in line:
                        continue
            line = line.replace('package:', '')
            apk_path, apk_id = line.split('=')
            apk_dict[apk_id] = apk_path

        return apk_dict

    def get_active_channel(self):
        active_channel = self.get_current_window()[0]
        print("Active channel is %s" % active_channel)
        return active_channel

    def is_showing_home(self):
        current_window = self._get_current_window_helper()
        app_name = "com.amazon.tv.launcher"
        activity_name = "HomeActivity"
        if app_name in current_window and activity_name in current_window:
            return True
        else:
            return False

    def reboot(self):
        print('Rebooting device over ADB...')
        self.adb('reboot')
        while not self.is_connected():
            print('Device not connected, waiting 5 seconds to reconnect!')
            time.sleep(5)
            self.connect()
        print('Device connected, waiting 20 seconds for reboot to complete!')
        time.sleep(20)


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

        # Maintain connection
        self.connect()

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

    def adb(self, *command_list, check_is_connected=True):
        """Returns (ret_code, stdout)."""
        if check_is_connected:
            while not self.is_connected():
                print('Device not connected, waiting 5 seconds to reconnect!')
                time.sleep(5)
                self.connect()

        cmd = ['adb'] + list(command_list)
        if ADB_DEBUG:
            print(cmd)
        proc = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        stdout = proc.communicate()[0]

        return (proc.returncode, stdout.decode("utf-8"))

    def take_screenshot(self, filename):

        # Maintain connection
        self.connect()

        #print("In capture screenshot! Creating the folder!")
        sp.call(['mkdir', '-p', os.path.join(LOCAL_LOG_DIR, 'screenshots')])

#        if 'Ubuntu-18' in platform.platform():
#            cmd = "adb shell screencap -p > %s" % filename
#        else:
#            cmd = "adb shell screencap -p | sed 's/\r$//' > %s" % filename
        #print("Taking picture to %s!" % filename)
        cmd = "adb shell screencap -p | sed 's/\r$//' > %s" % filename
        sp.call(cmd, shell=True)

    def terminate(self):
        self.killall_ADB_logcat()
