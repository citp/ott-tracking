"""
Continuously pulls newly installed APKs to local disk.

"""
from remote_control import AmazonRemoteControl
import subprocess
import os
import time
import datetime
import sys


def main():

    try:
        fire_stick_ip = sys.argv[1]
    except Exception:
        print 'Enter the IP address of the Fire Stick in the argument.'
        return

    rc = AmazonRemoteControl(fire_stick_ip)

    subprocess.call(['mkdir', '-p', 'apk_cache'])

    # Pulls APKs that are installed but not yet pulled.
    process_apk(rc, rc.get_installed_channels())

    apk_dict = None
    while True:
        try:
            apk_dict = monitor_apk_changes(rc, apk_dict)
            time.sleep(2)
        except KeyboardInterrupt:
            return


def monitor_apk_changes(rc, old_apk_dict=None):
    """
    Monitors list of all APKs installed every few seconds. Pulls APKs that are
    recently installed but not yet pulled.

    """
    new_apk_dict = rc.get_installed_channels(check_all_channels=True)

    if old_apk_dict is None:
        return new_apk_dict

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

        log('Pulling APK:', apk_id)
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

    log_str = '[{}] '.format(datetime.datetime.today())
    log_str += ' '.join([str(v) for v in args])

    with open('pull_apks.log', 'a') as fp:
        print >>fp, log_str

    print log_str


if __name__ == '__main__':
    main()
