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
 * `sni`: SNI, if used; otherwise, empty string.

or...

 * `type`: `server_hello` --- the response
 * `cipher_suite`: The cipher agreed by the server; only weak cipher is shown. If empty, no weak cipher is used by server.
 * `device_ip`, `device_port`, `remote_ip`, `remote_port`: These should match those of the corresponding client hello.

Note:

 * Must use Python 2.
 * If there are multiple pcap files, wrap `get_fingerprint.py` in a loop, e.g., `ls *.pcap | xargs -I XX python2 get_fingerprint.py XX`.

## Example

Analyze the `sample.pcap` file in this directory.

```
$ $ python get_fingerprint.py sample.pcap 2>/dev/null | head
{"fingerprint": "991305d10f.SCTVFNA", "device_port": 36394, "weak_ciphers": "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA", "sni": "api.roku.com", "remote_port": 443, "client_version": "0x303", "device_ip": "10.42.0.119", "type": "client_hello", "remote_ip": "23.22.241.63"}
{"remote_port": 443, "device_ip": "10.42.0.119", "device_port": 36394, "cipher_suite": "", "version": 771, "type": "server_hello", "remote_ip": "23.22.241.63"}
{"fingerprint": "991305d10f.SCTVFNA", "device_port": 45743, "weak_ciphers": "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA", "sni": "api.roku.com", "remote_port": 443, "client_version": "0x303", "device_ip": "10.42.0.119", "type": "client_hello", "remote_ip": "52.45.134.131"}
{"remote_port": 443, "device_ip": "10.42.0.119", "device_port": 45743, "cipher_suite": "", "version": 771, "type": "server_hello", "remote_ip": "52.45.134.131"}
{"fingerprint": "991305d10f.SCTVFNA", "device_port": 36398, "weak_ciphers": "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA", "sni": "api.roku.com", "remote_port": 443, "client_version": "0x303", "device_ip": "10.42.0.119", "type": "client_hello", "remote_ip": "23.22.241.63"}
{"fingerprint": "991305d10f.SCTVFNA", "device_port": 44674, "weak_ciphers": "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA", "sni": "api.roku.com", "remote_port": 443, "client_version": "0x303", "device_ip": "10.42.0.119", "type": "client_hello", "remote_ip": "34.193.43.251"}
{"remote_port": 443, "device_ip": "10.42.0.119", "device_port": 36398, "cipher_suite": "", "version": 771, "type": "server_hello", "remote_ip": "23.22.241.63"}
{"remote_port": 443, "device_ip": "10.42.0.119", "device_port": 44674, "cipher_suite": "", "version": 771, "type": "server_hello", "remote_ip": "34.193.43.251"}
{"fingerprint": "991305d10f.SCTVFNA", "device_port": 56177, "weak_ciphers": "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA", "sni": "api.roku.com", "remote_port": 443, "client_version": "0x303", "device_ip": "10.42.0.119", "type": "client_hello", "remote_ip": "54.173.104.173"}
````
