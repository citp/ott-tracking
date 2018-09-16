"""
Installs a single channel. Interacts with it. Uninstalls it.

Captures packets at every stage.

"""
from roku_remote import RokuRemoteControl
import time
import subprocess
import datetime


LOG_FILE = 'channel_surfer.log'


class SurferAborted(Exception):
    """Raised when we encounter an error while surfing this channel."""
    pass


class ChannelSurfer(object):

    def __init__(self, roku_ip, channel_id):

        self.rrc = RokuRemoteControl(roku_ip)
        self.channel_id = str(channel_id)
        self.go_home()

        self.log('Initialized', channel_id)

    def log(self, *args):

        current_time = '[{}]'.format(datetime.datetime.today())

        with open(LOG_FILE, 'a') as fp:
            print >> fp, current_time,
            print current_time,
            for arg in args:
                print >> fp, arg,
                print arg,
            print >> fp, ''
            print ''

    def go_home(self):

        time.sleep(2)
        self.rrc.press_key('Home')
        time.sleep(2)

    def channel_is_installed(self):

        channel_dict = self.rrc.get_channel_list()
        return self.channel_id in channel_dict

    def install_channel(self):

        if self.channel_is_installed():
            self.log('Not installing channel as it already exists.')
            return

        self.log('Installing channel.')

        self.go_home()
        self.rrc.install_channel(self.channel_id)

        for _ in range(60):
            time.sleep(1)
            if self.channel_is_installed():
                break

        self.go_home()

        if self.channel_is_installed():
            self.log('Channel successfully installed.')
        else:
            self.log('Unable to install channel. Aborted.')
            raise SurferAborted

    def uninstall_channel(self):

        self.log('Uninstalling channel.')

        if not self.channel_is_installed():
            self.log('Uninstalling a non-existent channel. Aborted.')
            raise SurferAborted

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
            raise SurferAborted

    def launch_channel(self):

        if not self.channel_is_installed():
            self.log('Cannot launch a non-existent channel.')
            raise SurferAborted

        self.log('Launching channel.')

        self.go_home()

        self.rrc.launch_channel(self.channel_id)

        time.sleep(1)

    def capture_packets(self, event_name):

        self.kill_all_tcpdump()

        time.sleep(3)

        pcap_filename = '{}-{}-{}'.format(
            self.channel_id,
            int(time.time()),
            event_name
        )

        subprocess.Popen(
            './start_pcap.sh {}'.format(pcap_filename),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )

        self.log('Capturing packets:', pcap_filename)

    def kill_all_tcpdump(self):

        subprocess.call('sudo pkill -f tcpdump', shell=True)
        time.sleep(1)
        subprocess.call('sudo pkill -9 -f tcpdump', shell=True)


def main():

    try:
        channel_id = sys.argv[1]
    except Exception:
        print 'Specify channel_id as the command line argument.'
        return
    
    surfer = ChannelSurfer('10.0.0.13', channel_id)

    surfer.install_channel()

    surfer.capture_packets('launch')

    surfer.launch_channel()

    time.sleep(20)

    surfer.kill_all_tcpdump()

    surfer.uninstall_channel()

    print 'Done'


if __name__ == '__main__':
    main()



