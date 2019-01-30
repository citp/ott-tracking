"""
Continuously pulls newly installed APKs to local disk.

When running this script, also run install_from_app_store.py to simultaneously
download the respective channels from the app store.


"""
from remote_control import AmazonRemoteControl
import subprocess
import os
import time
import datetime
import sys


base_apk_dict = {}


def main():

    try:
        fire_stick_ip = sys.argv[1]
    except Exception:
        print 'Enter the IP address of the Fire Stick in the argument.'
        return

    rc = AmazonRemoteControl(fire_stick_ip)

    subprocess.call(['mkdir', '-p', 'apk_cache'])

    # Load base channels (default, comes with Amazon Fire)
    with open('base_packages.txt') as fp:
        for line in fp:
            line = line.strip()
            if line.startswith('#'):
                continue
            line = line.replace('package:', '')
            apk_path, apk_id = line.split('=')
            base_apk_dict[apk_id] = apk_path

    # Remove any channels not in base
    cur_apk_dict = rc.get_installed_channels(check_all_channels=True)
    for apk_id in cur_apk_dict:
        if apk_id not in base_apk_dict:
            print 'Uninstalling', apk_id
            rc.uninstall_channel(apk_id)

    print 'Waiting for diffs.'

    # Install any new channels
    apk_dict = base_apk_dict
    while True:
        try:
            apk_dict = monitor_apk_changes(apk_dict, fire_stick_ip)
            time.sleep(2)
        except KeyboardInterrupt:
            return


def monitor_apk_changes(old_apk_dict, fire_stick_ip):
    """
    Monitors list of all APKs installed every few seconds. Pulls APKs that are
    recently installed but not yet pulled.

    """
    rc = AmazonRemoteControl(fire_stick_ip)
    new_apk_dict = rc.get_installed_channels(check_all_channels=True)

    # What are the new APKs between successive pull_apk calls
    update_dict = get_dict_update(old_apk_dict, new_apk_dict)

    process_apk(rc, update_dict)

    return new_apk_dict


def process_apk(rc, apk_dict):

    for (apk_id, remote_apk_path) in apk_dict.iteritems():

        local_apk_path = os.path.join('apk_cache/', apk_id)

        # Don't pull APK if it's already pulled before
        if os.path.isfile(local_apk_path):
            log('Already in apk_cache, so uninstalling APK:', apk_id)
            rc.uninstall_channel(apk_id)
            continue

        if apk_id in base_apk_dict:
            continue

        log('Pulling APK:', apk_id, 'from', remote_apk_path)
        rc.adb('pull', remote_apk_path, local_apk_path)

        log('Uninstalling APK:', apk_id)
        rc.uninstall_channel(apk_id)

        log('Done with', apk_id)


def get_dict_update(old_dict, new_dict):
    """
    Returns a dictionary that shows what's new in new_dict that is not in
    old_dict.

    """
    update_dict = {}

    for new_key in new_dict:
        if new_key not in old_dict:
            update_dict[new_key] = new_dict[new_key]

    return update_dict


def log(*args):
    """Write to local log."""

    log_str = '[{} @ {}] '.format(datetime.datetime.today(), int(time.time()))
    log_str += ' '.join([str(v) for v in args])

    with open('pull_apks.log', 'a') as fp:
        print >>fp, log_str

    print log_str


if __name__ == '__main__':
    main()
