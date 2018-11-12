"""
Installs a single channel. Interacts with it. Uninstalls it.

Captures packets at every stage.

"""
import time
import subprocess
import datetime
import sys


LOG_FILE = 'mitmproxy_runner.log'
MITMPRXY_CMD="mitmdump --showhost --mode transparent -s ~/.mitmproxy/scripts/smart-strip.py --ssl-insecure -w %s --set channel_id=%s --set data_dir=%s"



class MITMRunnerAborted(Exception):
    """Raised when we encounter an error while running this instance."""
    pass


class MITMRunner(object):

    def __init__(self, channel_id ,selector, data_dir, dump_prefix):
        self.channel_id = str(channel_id)
        self.selector = str(selector)
        self.data_dir = str(data_dir)
        self.dump_dir = str(data_dir) + str(dump_prefix)
        self.log('Initialized MITMRunner', channel_id ,selector)

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

    def run_mitmproxy(self):
        subprocess.call('./iptables_flush.sh', shell=True)
        subprocess.call('./iptables.sh', shell=True)
        time.sleep(3)

        self.dump_filename = '{}-{}-{}'.format(
            self.channel_id,
            int(time.time()),
            self.selector
        )

        #CMD = str(MITMPRXY_CMD % ( str(str(self.dump_dir) + str(self.dump_filename)) , str(self.channel_id), str(self.data_dir)))
        #print(CMD)
        #subprocess.Popen(
        #    CMD,
        #    stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        #)

        self.log('Dumping MITMing flows to:', self.dump_filename)

    def kill_mitmproxy(self):
        subprocess.call('./iptables_flush.sh', shell=True)
        time.sleep(2)
        subprocess.call('pkill -f mitmdump', shell=True)
        time.sleep(1)
        subprocess.call('pkill -9 -f mitmdump', shell=True)
