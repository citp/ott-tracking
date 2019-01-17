"""
Installs a single channel. Interacts with it. Uninstalls it.

Captures packets at every stage.

"""
import time
import subprocess
import datetime
import sys
import typing
import asyncio
import os
import signal  # noqa
import argparse  # noqa
import shutil

from mitmproxy.tools import cmdline  # noqa
from mitmproxy import exceptions, master  # noqa
from mitmproxy import options  # noqa
from mitmproxy import optmanager  # noqa
from mitmproxy import proxy  # noqa
from mitmproxy.utils import debug, arg_check  # noqa
from mitmproxy.tools.main import assert_utf8_env, process_options

import multiprocessing
from threading import Thread

OPTIONS_FILE_NAME = "config.yaml"
MITMPROXY_PORT_NO=str(8080)
SSLKEY_PREFIX="keys/"
LOG_FILE = 'mitmproxy_runner.log'
MITMPRXY_CMD="mitmdump --showhost --mode transparent -s ~/.mitmproxy/scripts/smart-strip.py --ssl-insecure -w %s --set channel_id=%s --set data_dir=%s"
ADDN_DIR='../src/mitmproxy/scripts/smart-strip.py'
MITM_CONST_ARGS=['--showhost', '--mode', 'transparent', '-p', MITMPROXY_PORT_NO, '-s', ADDN_DIR, '--ssl-insecure', '--flow-detail' , '3']


class MITMRunnerAborted(Exception):
    """Raised when we encounter an error while running this instance."""
    pass


def prepare_master(master_cls: typing.Type[master.Master]):
    opts = options.Options()
    master = master_cls(opts)
    return master, opts


def mitmdump_run(master, opts, event_handler, args=None) -> typing.Optional[int]:  # pragma: no cover
    def extra(args):
        if args.filter_args:
            v = " ".join(args.filter_args)
            return dict(
                save_stream_filter=v,
                readfile_filter=v,
                dumper_filter=v,
            )
        return {}

    Thread(target=shutdown_master, args=(master,event_handler,)).start()
    m = my_run(master, opts, cmdline.mitmdump, args, extra)
    if m and m.errorcheck.has_errored:  # type: ignore
        return 1
    return None


def move_keylog_file(src, dest):
    src_full_path = os.path.abspath(src)
    dest_full_path = os.path.abspath(dest)
    print('Moving '+ src_full_path + " to " + dest_full_path)
    shutil.move(src_full_path, dest_full_path)

def shutdown_master(master, event_handler):
    event_handler.wait()
    print("Shutting down DumpMaster!")
    master.addons.get("save").done()

    time.sleep(2)
    master.shutdown()
    print("DumpMaster was successfully shut down!")


def my_run(
    master,
    opts,
    make_parser: typing.Callable[[options.Options], argparse.ArgumentParser],
    arguments: typing.Sequence[str],
    extra: typing.Callable[[typing.Any], dict] = None
) -> master.Master:  # pragma: no cover
    """
        extra: Extra argument processing callable which returns a dict of
        options.
    """
    debug.register_info_dumpers()

    parser = make_parser(opts)

    # To make migration from 2.x to 3.0 bearable.
    if "-R" in sys.argv and sys.argv[sys.argv.index("-R") + 1].startswith("http"):
        print("-R is used for specifying replacements.\n"
              "To use mitmproxy in reverse mode please use --mode reverse:SPEC instead")

    try:
        args = parser.parse_args(arguments)
    except SystemExit:
        arg_check.check()
        sys.exit(1)
    try:
        opts.confdir = args.confdir
        optmanager.load_paths(
            opts,
            os.path.join(opts.confdir, OPTIONS_FILE_NAME),
        )

        pconf = process_options(parser, opts, args)
        #server: typing.Any = None
        if pconf.options.server:
            try:
                server = proxy.server.ProxyServer(pconf)
            except exceptions.ServerException as v:
                print(str(v), file=sys.stderr)
                sys.exit(1)
        else:
            server = proxy.server.DummyServer(pconf)
        master.server = server
        if args.options:
            print(optmanager.dump_defaults(opts))
            sys.exit(0)
        if args.commands:
            master.commands.dump()
            sys.exit(0)
        opts.set(*args.setoptions, defer=True)
        if extra:
            opts.update(**extra(args))
        loop = asyncio.get_event_loop()
        for signame in ('SIGINT', 'SIGTERM'):
            try:
                loop.add_signal_handler(getattr(signal, signame), master.shutdown)
            except NotImplementedError:
                # Not supported on Windows
                pass

        # Make sure that we catch KeyboardInterrupts on Windows.
        # https://stackoverflow.com/a/36925722/934719
        if os.name == "nt":
            async def wakeup():
                while True:
                    await asyncio.sleep(0.2)
            asyncio.ensure_future(wakeup())

        master.run()
    except exceptions.OptionsError as e:
        print("%s: %s" % (sys.argv[0], e), file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, RuntimeError) as e:
        pass
    return master

def set_event_handler(e):
    e.set()

class MITMRunner(object):

    def __init__(self, channel_id ,selector, data_dir, dump_prefix, global_keylog_file):
        self.channel_id = str(channel_id)
        self.selector = str(selector)
        self.data_dir = str(data_dir)
        self.dump_prefix = dump_prefix
        self.dump_dir = str(data_dir) + str(dump_prefix)
        self.event_handler = multiprocessing.Event()
        self.log('Initialized MITMRunner', channel_id ,selector)
        self.global_keylog_file = global_keylog_file
        self.keylog_file = self.data_dir + "/" + SSLKEY_PREFIX + "/"+ str(channel_id)+ ".txt"
        self.p = None

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

    def run_mitmproxy(self):
        self.clean_iptables()
        self.set_iptables()
        time.sleep(2)

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
        self.run_mitmdump(self.dump_filename, self.data_dir, self.channel_id, self.dump_prefix)
        self.log('Dumping MITMing flows to:', self.dump_filename)

    def run_mitmdump(self, dump_filename, data_dir, channel_id, dump_prefix):
        from mitmproxy.tools import dump
        self.master, self.opts = prepare_master(dump.DumpMaster)
        dump_dir = str(data_dir) + str(dump_prefix)
        ARGS = MITM_CONST_ARGS.copy()
        ARGS.append('-w')
        ARGS.append(str(data_dir) + '/' + str(dump_prefix) + '/' + str(dump_filename)) 
        ARGS.append('--set')
        ARGS.append('channel_id=' + str(channel_id))
        ARGS.append('--set')
        ARGS.append('data_dir=' + str(data_dir))
        #print(ARGS)
        #
        self.p = multiprocessing.Process(target=mitmdump_run, args=(self.master, self.opts, self.event_handler, ARGS,))
        self.p.start()

    def clean_iptables(self):
        self.log("Flushing iptables")
        subprocess.call('./iptables_flush.sh', shell=True)

    def set_iptables(self):
        self.log("Setting up iptables")
        subprocess.call('./iptables.sh', shell=True)

    def kill_existing_mitmproxy(self):
        command = "sudo kill -9 `sudo lsof -Pni  | grep \"\\*\\:"+ MITMPROXY_PORT_NO + "\" | awk '{print $2}'`"
        self.log("Killing existing mitmproxy")
        self.log(command)
        subprocess.call(command, shell=True, stderr=open(os.devnull, 'wb'))

    def kill_mitmproxy(self):
        self.log("Killing MITM proxy!!!")
        try:
            t = Thread(target=set_event_handler, args=(self.event_handler,))
            t.start()
        except Exception as e:
            self.log('Error in killing the proxy!')
            traceback.print_exc()
        
        self.log("Sleeping for 5 seconds before forcing manual termination!!!")
        time.sleep(5)
        self.log("Forcing manual termination!!!")
        self.p.terminate()
        time.sleep(2)
        subprocess.call('kill -9 -f ' + str(self.p.pid), shell=True, stderr=open(os.devnull, 'wb'))
        self.kill_existing_mitmproxy()
        self.clean_iptables()
        move_keylog_file(self.global_keylog_file, self.keylog_file)


