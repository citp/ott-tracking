import re
from six.moves import urllib

from __future__ import absolute_import, print_function, division
import collections
import random

import sys
from enum import Enum

import mitmproxy
from mitmproxy.exceptions import TlsProtocolException
from mitmproxy.protocol import TlsLayer, RawTCPLayer


class InterceptionResult(Enum):
    success = True
    failure = False
    skipped = None


class _TlsStrategy(object):
    """
    Abstract base class for interception strategies.
    """

    def __init__(self):
        # A server_address -> interception results mapping
        self.history = collections.defaultdict(lambda: collections.deque(maxlen=200))

    def should_intercept(self, server_address):
        """
        Returns:
            True, if we should attempt to intercept the connection.
            False, if we want to employ pass-through instead.
        """
        raise NotImplementedError()

    def record_success(self, server_address):
        self.history[server_address].append(InterceptionResult.success)

    def record_failure(self, server_address):
        self.history[server_address].append(InterceptionResult.failure)

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
            super(TlsFeedback, self)._establish_tls_with_client()
        except TlsProtocolException as e:
            tls_strategy.record_failure(server_address)
            raise e
        else:
            tls_strategy.record_success(server_address)


# inline script hooks below.

tls_strategy = None


def start():
    global tls_strategy
    tls_strategy = ConservativeStrategy()


def next_layer(next_layer):
    """
    This hook does the actual magic - if the next layer is planned to be a TLS layer,
    we check if we want to enter pass-through mode instead.
    """
    if isinstance(next_layer, TlsLayer) and next_layer._client_tls:
        server_address = next_layer.server_conn.address

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

# set of SSL/TLS capable hosts
secure_hosts = set()


def request(flow):
    flow.request.headers.pop('If-Modified-Since', None)
    flow.request.headers.pop('Cache-Control', None)

    # do not force https redirection
    flow.request.headers.pop('Upgrade-Insecure-Requests', None)

    # proxy connections to SSL-enabled hosts
    if flow.request.pretty_host in secure_hosts:
        flow.request.scheme = 'https'
        flow.request.port = 443


def response(flow):
    flow.response.headers.pop('Strict-Transport-Security', None)
    flow.response.headers.pop('Public-Key-Pins', None)

    # strip links in response body
    flow.response.content = flow.response.content.replace('https://', 'http://')

    # strip meta tag upgrade-insecure-requests in response body
    csp_meta_tag_pattern = b'<meta.*http-equiv=["\']Content-Security-Policy[\'"].*upgrade-insecure-requests.*?>'
    flow.response.content = re.sub(csp_meta_tag_pattern, b'', flow.response.content, flags=re.IGNORECASE)

    # strip links in 'Location' header
    if flow.response.headers.get('Location', '').startswith('https://'):
        location = flow.response.headers['Location']
        hostname = urllib.parse.urlparse(location).hostname
        if hostname:
            secure_hosts.add(hostname)
        flow.response.headers['Location'] = location.replace('https://', 'http://', 1)

    # strip upgrade-insecure-requests in Content-Security-Policy header
    if re.search('upgrade-insecure-requests', flow.response.headers.get('Content-Security-Policy', ''), flags=re.IGNORECASE):
        csp = flow.response.headers['Content-Security-Policy']
        flow.response.headers['Content-Security-Policy'] = re.sub('upgrade-insecure-requests[;\s]*', '', csp, flags=re.IGNORECASE)

    # strip secure flag from 'Set-Cookie' headers
    cookies = flow.response.headers.get_all('Set-Cookie')
    cookies = [re.sub(r';\s*secure\s*', '', s) for s in cookies]
    flow.response.headers.set_all('Set-Cookie', cookies)
