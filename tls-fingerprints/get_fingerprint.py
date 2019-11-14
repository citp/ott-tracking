"""
Usage: python2 get_fingerprint.py [path_of_pcap]

Outputs: lines of jsons; see README

"""
import scapy_ssl_tls.ssl_tls as ssl_tls # noqa
import ipaddress
import scapy.all as sc
import sys
import re
import hashlib
import json


WEAK_CIPHERS = {"0x0005": "TLS_RSA_WITH_RC4_128_SHA", "0xc008": "TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA", "0xc007": "TLS_ECDHE_ECDSA_WITH_RC4_128_SHA", "0xc003": "TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA", "0xc002": "TLS_ECDH_ECDSA_WITH_RC4_128_SHA", "0xc00d": "TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA", "0x0025": "TLS_KRB5_WITH_IDEA_CBC_MD5", "0xc01a": "TLS_SRP_SHA_WITH_3DES_EDE_CBC_SHA", "0xc01b": "TLS_SRP_SHA_RSA_WITH_3DES_EDE_CBC_SHA", "0x000d": "TLS_DH_DSS_WITH_3DES_EDE_CBC_SHA", "0xc034": "TLS_ECDHE_PSK_WITH_3DES_EDE_CBC_SHA", "0x0027": "TLS_KRB5_EXPORT_WITH_RC2_CBC_40_SHA", "0xffe0": "SSL_RSA_FIPS_WITH_3DES_EDE_CBC_SHA", "0x008f": "TLS_DHE_PSK_WITH_3DES_EDE_CBC_SHA", "0x008e": "TLS_DHE_PSK_WITH_RC4_128_SHA", "0x0019": "_EXPORT_WITH_DES40_CBC_SHA", "0x0018": "_WITH_RC4_128_MD5", "0x008a": "TLS_PSK_WITH_RC4_128_SHA", "0x0015": "TLS_DHE_RSA_WITH_DES_CBC_SHA", "0x0014": "TLS_DHE_RSA_EXPORT_WITH_DES40_CBC_SHA", "0x0017": "_EXPORT_WITH_RC4_40_MD5", "0x0016": "TLS_DHE_RSA_WITH_3DES_EDE_CBC_SHA", "0x0011": "TLS_DHE_DSS_EXPORT_WITH_DES40_CBC_SHA", "0x0010": "TLS_DH_RSA_WITH_3DES_EDE_CBC_SHA", "0x0013": "TLS_DHE_DSS_WITH_3DES_EDE_CBC_SHA", "0x0012": "TLS_DHE_DSS_WITH_DES_CBC_SHA", "0xfeff": "SSL_RSA_FIPS_WITH_3DES_EDE_CBC_SHA", "0xfefe": "SSL_RSA_FIPS_WITH_DES_CBC_SHA", "0x0093": "TLS_RSA_PSK_WITH_3DES_EDE_CBC_SHA", "0x0092": "TLS_RSA_PSK_WITH_RC4_128_SHA", "0x000f": "TLS_DH_RSA_WITH_DES_CBC_SHA", "0x002a": "TLS_KRB5_EXPORT_WITH_RC2_CBC_40_MD5", "0x002b": "TLS_KRB5_EXPORT_WITH_RC4_40_MD5", "0x000e": "TLS_DH_RSA_EXPORT_WITH_DES40_CBC_SHA", "0x000b": "TLS_DH_DSS_EXPORT_WITH_DES40_CBC_SHA", "0x000c": "TLS_DH_DSS_WITH_DES_CBC_SHA", "0x000a": "TLS_RSA_WITH_3DES_EDE_CBC_SHA", "0xc011": "TLS_ECDHE_RSA_WITH_RC4_128_SHA", "0xc012": "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA", "0xffe1": "SSL_RSA_FIPS_WITH_DES_CBC_SHA", "0xc033": "TLS_ECDHE_PSK_WITH_RC4_128_SHA", "0xc016": "_WITH_RC4_128_SHA", "0xc017": "_WITH_3DES_EDE_CBC_SHA", "0xff82": "SSL_RSA_WITH_DES_CBC_MD5", "0xff83": "SSL_RSA_WITH_3DES_EDE_CBC_MD5", "0xff80": "SSL_RSA_WITH_RC2_CBC_MD5", "0xff81": "SSL_RSA_WITH_IDEA_CBC_MD5", "0x0064": "TLS_RSA_EXPORT1024_WITH_RC4_56_SHA", "0x0065": "TLS_DHE_DSS_EXPORT1024_WITH_RC4_56_SHA", "0x0066": "TLS_DHE_DSS_WITH_RC4_128_SHA", "0xc00c": "TLS_ECDH_RSA_WITH_RC4_128_SHA", "0x0060": "TLS_RSA_EXPORT1024_WITH_RC4_56_MD5", "0x0061": "TLS_RSA_EXPORT1024_WITH_RC2_CBC_56_MD5", "0x0062": "TLS_RSA_EXPORT1024_WITH_DES_CBC_SHA", "0x0063": "TLS_DHE_DSS_EXPORT1024_WITH_DES_CBC_SHA", "0x0028": "TLS_KRB5_EXPORT_WITH_RC4_40_SHA", "0x0029": "TLS_KRB5_EXPORT_WITH_DES_CBC_40_MD5", "0x001f": "TLS_KRB5_WITH_3DES_EDE_CBC_SHA", "0x0008": "TLS_RSA_EXPORT_WITH_DES40_CBC_SHA", "0x0009": "TLS_RSA_WITH_DES_CBC_SHA", "0x0006": "TLS_RSA_EXPORT_WITH_RC2_CBC_40_MD5", "0x008b": "TLS_PSK_WITH_3DES_EDE_CBC_SHA", "0x0004": "TLS_RSA_WITH_RC4_128_MD5", "0x0023": "TLS_KRB5_WITH_3DES_EDE_CBC_MD5", "0x0024": "TLS_KRB5_WITH_RC4_128_MD5", "0x0003": "TLS_RSA_EXPORT_WITH_RC4_40_MD5", "0x0026": "TLS_KRB5_EXPORT_WITH_DES_CBC_40_SHA", "0x0001": "TLS_RSA_WITH_NULL_MD5", "0x0020": "TLS_KRB5_WITH_RC4_128_SHA", "0xc01c": "TLS_SRP_SHA_DSS_WITH_3DES_EDE_CBC_SHA", "0x001e": "SSL_FORTEZZA_KEA_WITH_RC4_128_SHA", "0x001b": "_WITH_3DES_EDE_CBC_SHA", "0x001a": "_WITH_DES_CBC_SHA", "0x0022": "TLS_KRB5_WITH_DES_CBC_MD5", "0x5600": "TLS_FALLBACK_SCSV"} # noqa


def main():

    try:
        pcap_file = sys.argv[1]
    except Exception:
        return 'Argument: [pcap_file]'
        sys.exit(1)

    reader = sc.PcapReader(pcap_file)

    for pkt in reader:
        parsed = parse_packet(pkt)
        if parsed:
            print json.dumps(parsed)


def is_grease(int_value):
    """
    Returns if a value is GREASE.

    See https://tools.ietf.org/html/draft-ietf-tls-grease-01

    """
    hex_str = hex(int_value)[2:].lower()
    if len(hex_str) < 4:
        return False

    first_byte = hex_str[0:2]
    last_byte = hex_str[-2:]

    return (
        first_byte[1] == 'a' and
        last_byte[1] == 'a' and
        first_byte == last_byte
    )


def parse_packet(pkt):
    """
    Referenced papers:

     - https://tlsfingerprint.io/static/frolov2019.pdf
     - https://zakird.com/papers/https_interception.pdf
     - https://conferences.sigcomm.org/imc/2018/papers/imc18-final193.pdf

    """
    for ix in range(3, 100):

        try:
            layer = pkt[ix]
        except IndexError:
            return

        if layer.name == 'TLS Client Hello':
            tls_dict = get_fingerprint(get_client_hello(pkt, layer))
            tls_dict['type'] = 'client_hello'
            return tls_dict

        if layer.name == 'TLS Server Hello':
            tls_dict = get_server_hello(pkt, layer)
            tls_dict['type'] = 'server_hello'
            return tls_dict


def get_client_hello(pkt, layer):

    extensions = getattr(layer, 'extensions', [])
    extension_types = []
    sni = None

    # Remove GREASE values from cipher_suites
    cipher_suites = getattr(layer, 'cipher_suites', [])
    length_before_removing_grease = len(cipher_suites)
    cipher_suites = [v for v in cipher_suites if not is_grease(v)]
    length_after_removing_grease = len(cipher_suites)
    cipher_suite_uses_grease = \
        (length_before_removing_grease != length_after_removing_grease)

    # Extract SNI, per
    # https://www.iana.org/assignments/tls-extensiontype-values/tls-extensiontype-values.xhtml#tls-extensiontype-values-1
    extension_uses_grease = False
    for ex in extensions:
        try:
            # Remove grease values
            if is_grease(ex.type):
                extension_uses_grease = True
                continue
            extension_types.append(ex.type)
            if ex.type == 0:
                sni = str(ex.server_names[0].data)
        except Exception:
            pass

    version = getattr(layer, 'version', None)

    return {
        'type': 'client_hello',
        'version': version,
        'cipher_suites': cipher_suites,
        'cipher_suite_uses_grease': cipher_suite_uses_grease,
        'compression_methods':
            getattr(layer, 'compression_methods', None),
        'extension_types': extension_types,
        'extension_details': repr(extensions),
        'extension_uses_grease': extension_uses_grease,
        'sni': sni,
        'remote_ip': pkt[sc.IP].dst,
        'remote_port': pkt[sc.TCP].dport,
        'device_ip': pkt[sc.IP].src,
        'device_port': pkt[sc.TCP].sport,
    }


def get_fingerprint(pkt):

    # Basic fields

    fingerprint = str(pkt['cipher_suites']) + str(pkt['compression_methods'])
    fingerprint += str(pkt['extension_types']) + str(pkt['version'])
    fingerprint += str(pkt['cipher_suite_uses_grease'])
    fingerprint += str(pkt['extension_uses_grease'])

    meta = ''

    if pkt['cipher_suites']:
        meta += 'S'
    if pkt['compression_methods']:
        meta += 'C'
    if pkt['extension_types']:
        meta += 'T'
    if pkt['version']:
        meta += 'V'
    if pkt['cipher_suite_uses_grease']:
        meta += 'G'
    if pkt['extension_uses_grease']:
        meta += 'E'

    # Extension details

    details = pkt['extension_details']

    match = re.search(r'(ec_point_formats=\[[^\]]+\])', details)
    if match:
        fingerprint += match.group(0) + '\n'
        meta += 'F'

    match = re.search(r'(named_group_list=\[[^\]]+\])', details)
    if match:
        fingerprint += match.group(0) + '\n'
        meta += 'N'

    match = re.search(r'(algs=\[[^\]]+\])', details)
    if match:
        fingerprint += match.group(0) + '\n'
        meta += 'A'

    # Form hash
    fingerprint = get_hash(fingerprint)[0:10] + '.' + meta

    return {
        'remote_ip': pkt['remote_ip'],
        'remote_port': pkt['remote_port'],
        'device_ip': pkt['device_ip'],
        'device_port': pkt['device_port'],
        'sni': pkt['sni'],
        'client_version': hex(int(pkt['version'])),
        'weak_ciphers': get_weak_ciphers(pkt['cipher_suites']),
        'fingerprint': fingerprint,
    }


def get_server_hello(pkt, layer):

    if is_public_ip_address(pkt[sc.IP].src):
        device_ip = pkt[sc.IP].dst
        remote_ip = pkt[sc.IP].src
        device_port = pkt[sc.TCP].dport
        remote_port = pkt[sc.TCP].sport
    else:
        device_ip = pkt[sc.IP].src
        remote_ip = pkt[sc.IP].dst
        device_port = pkt[sc.TCP].sport
        remote_port = pkt[sc.TCP].dport

    server_cipher = getattr(layer, 'cipher_suite', None)

    if server_cipher:
        server_cipher = get_weak_ciphers([server_cipher])

    return {
        'type': 'server_hello',
        'version': getattr(layer, 'version', None),
        'cipher_suite': server_cipher,
        'device_ip': device_ip,
        'device_port': device_port,
        'remote_ip': remote_ip,
        'remote_port': remote_port,
    }


_cipher_cache = {}


def get_weak_ciphers(ciphers):

    cache_key = str(ciphers)
    try:
        return _cipher_cache[cache_key]
    except KeyError:
        pass

    out = []
    for c in [hex(int(v)) for v in ciphers]:
        try:
            out.append(WEAK_CIPHERS[c])
        except KeyError:
            pass

    out = ' '.join(out)
    _cipher_cache[cache_key] = out

    return out


def is_public_ip_address(ip_address):

    if not ip_address:
        return False

    try:
        ip = ipaddress.ip_address(unicode(ip_address))
    except Exception:
        return False

    if ip.is_multicast or ip.is_private or ip.is_unspecified or \
            ip.is_reserved or ip.is_loopback or ip.is_link_local:
        return False

    return True


def get_hash(v):
    return hashlib.sha256(str(v)).hexdigest()


if __name__ == '__main__':
    main()
