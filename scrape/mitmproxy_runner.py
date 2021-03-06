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
import traceback


from mitmproxy.tools import cmdline, dump  # noqa
from mitmproxy import exceptions, master  # noqa
from mitmproxy import options  # noqa
from mitmproxy import optmanager  # noqa
from mitmproxy import proxy  # noqa
from mitmproxy.utils import debug, arg_check  # noqa
from mitmproxy.tools.main import assert_utf8_env, process_options

import multiprocessing
from threading import Thread
from os.path import join


RUN_MITM_IN_SUBPROCESS = False
DUMP_HAR = False
HAR_EXPORT_ADDON = '../src/mitmproxy/scripts/har_dump.py'
MITMPROXY_NET_SET = False

LOCAL_LOG_DIR = os.path.abspath(os.getenv("LogDir"))
OPTIONS_FILE_NAME = "config.yaml"
MITMPROXY_PORT_NO = os.getenv("MITMPROXY_PORT_NO")
SSLKEY_PREFIX = "keys/"
LOG_FILE = 'mitmproxy_runner.log'
ADDN_DIR = './scripts/mitmproxy/smart-strip.py'
# MITM_CONST_ARGS=['--showhost', '--mode', 'transparent', '-p', MITMPROXY_PORT_NO, '-s', ADDN_DIR, '--ssl-insecure', '--flow-detail' , '3']
MITM_CONST_ARGS = [
    '--showhost', '--mode', 'transparent', '-p', MITMPROXY_PORT_NO,
    '-s', ADDN_DIR, '--ssl-insecure'
    , '--flow-detail', '1'
    ]



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
    print('Moving ' + src_full_path + " to " + dest_full_path)
    if os.path.exists(src_full_path):
        shutil.move(src_full_path, dest_full_path)
    else:
        print(src_full_path + " doesn't exist!")


def shutdown_master(master, event_handler):
    event_handler.wait()
    print("Shutting down DumpMaster!")
    try:
        master.addons.get("save").done()
    except Exception:
        print('Error in saving MITM flows before exit!')
        traceback.print_exc()

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

    def __init__(self, channel_id, data_dir, dump_prefix, global_keylog_file,
                 ssl_strip, tls_intercept, tls_intercept_cert):
        self.channel_id = str(channel_id)
        self.data_dir = str(data_dir)
        self.dump_prefix = dump_prefix
        self.dump_dir = str(data_dir) + str(dump_prefix)
        self.ssl_strip = ssl_strip
        self.tls_intercept = tls_intercept
        self.tls_intercept_cert = tls_intercept_cert
        self.event_handler = multiprocessing.Event()
        self.log('Initialized MITMRunner', channel_id)
        self.global_keylog_file = global_keylog_file
        self.keylog_file = self.data_dir + "/" + SSLKEY_PREFIX + "/"+ str(channel_id)+ ".txt"
        self.p = None
        self.mitm_proc = None

        global MITMPROXY_NET_SET
        if not MITMPROXY_NET_SET:
            self.set_global_net_settings()
            MITMPROXY_NET_SET = True

    def set_global_net_settings(self):
        self.log("Setting global network settings")
        cmd = "sudo -E ./scripts/ip_forwarding.sh"

        self.log(cmd)
        subprocess.call(cmd, shell=True, stderr=open(os.devnull, 'wb'))

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

    def run_mitmproxy(self):
        self.clean_iptables()
        self.set_iptables()
        time.sleep(2)

        self.dump_filename = '{}-{}.flow'.format(
            self.channel_id,
            int(time.time())
        )

        #CMD = str(MITMPRXY_CMD % ( str(str(self.dump_dir) + str(self.dump_filename)) , str(self.channel_id), str(self.data_dir)))
        #print(CMD)
        #subprocess.Popen(
        #    CMD,
        #    stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        #)
        self.run_mitmdump(self.dump_filename, self.data_dir,
                          self.channel_id, self.dump_prefix)
        self.log('Dumping MITMing flows to:', self.dump_filename)

    def run_mitmdump(self, dump_filename, data_dir, channel_id, dump_prefix):
        self.clean_global_keylog_file()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.master, self.opts = prepare_master(dump.DumpMaster)
        dump_dir = join(str(data_dir), str(dump_prefix))
        ARGS = MITM_CONST_ARGS.copy()
        ARGS.append('-w')
        ARGS.append(dump_dir + '/' + str(dump_filename))
        ARGS.append('--set')
        ARGS.append('channel_id=' + str(channel_id))
        ARGS.append('--set')
        ARGS.append('data_dir=' + str(data_dir))
        if DUMP_HAR:
            ARGS.append('-s')
            ARGS.append(HAR_EXPORT_ADDON)
            ARGS.append('--set hardump=' + dump_dir + str(channel_id) + '-' +
                        str(int(time.time())) + '.har')
        if not self.ssl_strip:
            ARGS.append('--set')
            ARGS.append('ssl_strip=0')
        if not self.tls_intercept:
            ARGS.append('--set')
            ARGS.append('tls_intercept=0')
        if self.tls_intercept_cert is not None:
            ARGS.append('--cert')
            ARGS.append(self.tls_intercept_cert)
        print(ARGS)
        mitm_stdout = join(dump_dir, "%s_mitm_std.out" % str(channel_id))
        mitm_stderr = join(dump_dir, "%s_mitm_std.err" % str(channel_id))
        if RUN_MITM_IN_SUBPROCESS:
            with open(mitm_stdout, "a") as fout, open(mitm_stderr, "a") as ferr:
                self.mitm_proc = subprocess.Popen(
                    ['mitmdump'] + ARGS,
                    stdout=fout, stderr=ferr)
        else:
            self.p = multiprocessing.Process(target=mitmdump_run, args=(self.master, self.opts, self.event_handler, ARGS,))
            self.p.start()

    def clean_global_keylog_file(self):
        #Clear the original log file
        self.log("Cleaning up global SSL_KEYLOG_FILE")
        open(self.global_keylog_file, 'w').close()

    def clean_iptables(self):
        self.log("Flushing iptables")
        subprocess.call('./scripts/iptables_flush_all.sh', shell=True)
        subprocess.call('./scripts/iptables_flush.sh', shell=True)

    def set_iptables(self):
        self.log("Setting up iptables")
        subprocess.call('./scripts/iptables.sh', shell=True)

    def kill_existing_mitmproxy(self):
        command = "sudo kill -9 `sudo lsof -Pni  | grep \"\\*\\:"+ MITMPROXY_PORT_NO + "\" | awk '{print $2}'`"
        self.log("Killing existing mitmproxy")
        self.log(command)
        subprocess.call(command, shell=True, stderr=open(os.devnull, 'wb'))

    def kill_mitmproxy(self):
        self.log("Killing MITM proxy!!!")
        if RUN_MITM_IN_SUBPROCESS:
            self.log("Will terminate MITM proxy!!!")
            self.mitm_proc.terminate()
            try:
                self.mitm_proc.wait(60)
            except Exception as exc:
                self.log("Error while  waiting to terminate mitmdump %s" % exc)
            # pgrp = os.getpgid(self.mitm_proc.pid)
            # os.killpg(pgrp, signal.SIGINT)
            # self.mitm_proc.send_signal(1)

            self.log("Successfully terminated MITM proxy!!!")
        else:
            try:
                t = Thread(target=set_event_handler, args=(self.event_handler,))
                t.start()
            except Exception as e:
                self.log('Error in killing the proxy!')
                traceback.print_tb(e.__traceback__)

            self.log("Sleeping for 5 seconds before forcing manual termination!!!")
            time.sleep(5)
            self.log("Forcing manual termination!!!")
            if self.p is not None:
                self.p.terminate()
                time.sleep(2)
                subprocess.call('kill -9 -f ' + str(self.p.pid), shell=True, stderr=open(os.devnull, 'wb'))
            time.sleep(2)
            self.kill_existing_mitmproxy()
        self.clean_iptables()
        move_keylog_file(self.global_keylog_file, self.keylog_file)
