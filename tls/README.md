# TLS Fingerprinting

## Installation

1. `pip2 install ipaddress`
2. `pip2 install scapy-ssl_tls`

Note:

 * Must use Python 2, because `scapy-ssl_tls` does not work on Python 3.

Reference: [Scapy-SSL/TLS](https://github.com/tintinweb/scapy-ssl_tls)

## Usage

`python2 get_fingerprint.py [path_of_pcap]`

The result is printed on `stdout`. Each line of the result is a JSON object in the form of either...

 * `type`: `client_hello`
 * `fingerprint`: The client hello fingerprint
 * `device_ip` and `device_port`: IP and port of the device
 * `remote_ip` and `remote_port`: IP and port of the remote endpoint
 * `weak_ciphers`: A space-sparated list of weak ciphers being proposed by the client.
 * `client_version`: Max TLS version supported by client.
 * `sni`: SNI, if used.

or...

 * `type`: `server_hello` --- the response
 * `cipher_suite`: The cipher agreed by the server; only weak cipher is shown. If empty, no weak cipher is used by server.
 * `device_ip`, `device_port`, `remote_ip`, `remote_port`: These should match those of the corresponding client hello.

Note:

 * Must use Python 2.
 * If there are multiple pcap files, wrap `get_fingerprint.py` in a loop, e.g., `ls *.pcap | xargs -I XX python2 get_fingerprint.py XX`.
