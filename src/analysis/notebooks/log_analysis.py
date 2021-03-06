try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
import ujson
import numpy as np
import os
import sys
import pandas as pd
import json
import traceback
from datetime import datetime
from glob import glob
from os.path import join, sep, isfile, basename, dirname, realpath
from collections import defaultdict, Counter
from nb_utils import read_channel_details_df, get_crawl_data_path, replace_nan
from tld import get_fld
from trackingprotection_tools import DisconnectParser
# https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json"

try:
    from functools import lru_cache
except ImportError:
    from functools32 import lru_cache

DEBUG = False


def load_block_lists():
    nb_dir = dirname(realpath(__file__))
    bloc_dir = realpath(join(nb_dir, '../../../src/blocklistparser'))
    sys.path.insert(0, bloc_dir)
    os.chdir(bloc_dir)  # block list modules load list from relative path
    from BlockListParser import get_adblock_rules, get_disconnect_blocked_hosts, GhosteryListParser, is_blocked_by_disconnect
    from PiHoleListParser import PiHoleListParser
    easylist_rules, easyprivacy_rules = get_adblock_rules()
    # disconnect_blocklist = get_disconnect_blocked_hosts()
    ghostery_blocklist = GhosteryListParser("blocklists/ghostery.json")
    pihole_parser = PiHoleListParser()
    # switch back to notebook dir
    os.chdir(nb_dir)
    disconnect = DisconnectParser(blocklist="disconnect/services.json")
    return ghostery_blocklist, easylist_rules, easyprivacy_rules, pihole_parser, disconnect


import functools
@lru_cache(maxsize=100000)
def easylist_rules_should_block(easylist_rules, x):
    return easylist_rules.should_block("http://" + x, {'third-party': True})


@lru_cache(maxsize=100000)
def easyprivacy_rules_should_block(easyprivacy_rules, x):
    return easyprivacy_rules.should_block("http://" + x, {'third-party': True})


def add_scheme(hostname_or_url):
    if hostname_or_url.startswith("http://") or hostname_or_url.startswith("https://"):
        return hostname_or_url    
    else:
        return "http://" + hostname_or_url


def add_adblocked_status(df, check_by_url=False):
    ghostery_blocklist, easylist_rules, easyprivacy_rules, \
        pihole_parser, disconnect = load_block_lists()
    col = "host"
    df['disconnect_blocked'] = df[col].map(
            lambda x: disconnect.should_block(add_scheme(x)) if len(x) else False)
    df['ghostery_blocked'] = df[col].map(
        lambda x: ghostery_blocklist.check_host_in_list(add_scheme(x)))
    df['easylist_blocked'] = df[col].map(
        lambda x: easylist_rules_should_block(easylist_rules, x))
    df['easyprivacy_blocked'] = df[col].map(
        lambda x: easyprivacy_rules_should_block(easyprivacy_rules, x))
    df['pihole_blocked'] = df[col].map(
        lambda x: pihole_parser.is_blocked_by_pihole(x))
    df['adblocked'] = df.disconnect_blocked | df.ghostery_blocked | \
        df.easylist_blocked | df.easyprivacy_blocked | df.pihole_blocked

    if "url" not in df.columns or not check_by_url:
        return
    # check adblocked status by URL, for comparison
    col = "url"
    df['disconnect_blocked_by_url'] = df[col].map(
            lambda x: disconnect.should_block(add_scheme(x)) if len(x) else False)
    df['ghostery_blocked_by_url'] = df[col].map(
        lambda x: ghostery_blocklist.check_host_in_list(add_scheme(x)))
    df['easylist_blocked_by_url'] = df[col].map(
        lambda x: easylist_rules_should_block(easylist_rules, x))
    df['easyprivacy_blocked_by_url'] = df[col].map(
        lambda x: easyprivacy_rules_should_block(easyprivacy_rules, x))
    df['pihole_blocked_by_url'] = df[col].map(
        lambda x: pihole_parser.is_blocked_by_pihole(x))
    df['adblocked_by_url'] = df.disconnect_blocked_by_url | df.ghostery_blocked_by_url | \
        df.easylist_blocked_by_url | df.easyprivacy_blocked | df.pihole_blocked


def load_dns_data(root_dir):
    rIP2NameDB = {}
    rName2IPDB = {}
    db_folder_name = os.path.join(root_dir, "db")
    for file_name in glob(join(db_folder_name, "*.json")):
        try:
            with open(file_name) as f:
                if file_name.endswith("rIP2NameDB.json"):
                    data = json.load(f)
                    for IP in data:
                        if IP not in rIP2NameDB:
                            rIP2NameDB[IP] = []
                        rIP2NameDB[IP].append(data[IP]['value'])
                elif file_name.endswith("rName2IPDB.json"):
                    data = json.load(f)
                    for Domain in data:
                        if Domain not in rName2IPDB:
                            rName2IPDB[Domain] = []
                        rName2IPDB[Domain].extend(data[Domain]['value'])
        except Exception:
            print("Couldn't open %s" % file_name)
            traceback.print_exc()
    return (rIP2NameDB, rName2IPDB)


def load_timestamps_from_crawl_data(root_dir):
    # Load Timestamps
    timestamps = defaultdict(list)
    print("Loading timestamp data from %s" % root_dir)
    for txt_path in glob(root_dir + "/logs/*timestamps.txt", recursive=True):
        filename = txt_path.split(sep)[-1]
        channel_id = filename.split("-")[0]
        try:
            for l in open(txt_path):
                label, ts = l.split(",")
                timestamps[channel_id].append((label, float(ts)))
        except Exception:
            print("Couldn't open %s" % filename)
            traceback.print_exc()
    return timestamps


def get_http_hostnames(crawl_name, requests=None, value_type="host"):
    http_hostnames = dict()
    if requests is None:
        requests, _, _ = get_http_df(crawl_name)
    for _, row in requests.iterrows():
        http_hostnames[(row['channel_id'], row["tcp_stream"], row["ip_dst"], row["tcp_dstport"])] = row[value_type]
    return http_hostnames


def replace_in_column_names(df, search, replace):
    mapping = {col_name: col_name.replace(search, replace)
               for col_name in df.columns}
    df.rename(columns=mapping, inplace=True)


def get_unique_tcp_stream_ids(post_process_dir, suffix):
    unique_tcp_conn_ids = {}
    assert suffix in ["*.pcap.ssl_fail", "*.pcap.mitmproxy-attempt", "*.pcap.ssl_connections"]
    for txt_path in glob(join(post_process_dir, suffix)):
        filename = basename(txt_path)
        channel_id = filename.split("-")[0]

        if suffix.endswith("ssl_connections"):
            df = pd.read_csv(txt_path, sep='|', encoding='utf-8', index_col=None)
            # ssl_connections csv includes both handshakes and SSL payloads
            # select payloads only (ssl.record.content_type=23)
            # Some packets have multiple payloads which appear as 23,23
            # That's why we are using "str.contains" instead of equality (==23)
            df["ssl.record.content_type"] = df["ssl.record.content_type"].astype(str)
            # print(df["ssl.record.content_type"].value_counts())
            # print("before", len(df))
            df = df[df["ssl.record.content_type"].str.contains("23")]
            # print("after", len(df))
        else:
            df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
        unique_tcp_conn_ids[channel_id] = df['tcp.stream'].unique()
    return unique_tcp_conn_ids


def get_crawl_status(crawl_dir):
    status_dict = {}
    for f in glob(join(crawl_dir, "finished", "*.txt")):
        if "_questionnaire.txt" in f:
            continue
        channel_id = basename(f).rsplit(".", 1)[0]
        status = open(f).read().rstrip()
        status_dict[channel_id] = status
    return status_dict


def get_epoch(row, channel_timestamps):
    ch_timestamps = channel_timestamps[row["channel_id"]]
    packet_timestamp = row["frame_time_epoch"]
    ret_label = "unknown"
    for label, timestamp in ch_timestamps:
        # print(type(timestamp))
        if packet_timestamp > timestamp:
            ret_label = label
    # for backwards compatibility: we expect label of the smart crawl stage to start with smart
    # this makes plotting much easier since alphabetical order mirrors the temporal order.
    if "key-seq" in ret_label and not ret_label.startswith("smart"):
        return "smart%s" % ret_label
    else:
        return ret_label


def get_domain_by_ip(ip_address, ip2name_db):
    if ip_address in ip2name_db:
        return ip2name_db[ip_address][0].rstrip('.')
    else:
        return "unknown"


def get_ip_domain_mapping_from_dns_df(dns_df):
    ip_2_domains = defaultdict(dict)
    local_qrys = set()
    for idx, row in dns_df.iterrows():
        domain = row["dns_qry_name"]
        if not isinstance(domain, str):
            # nan
            # print("Not a string", domain)
            continue
        if domain.endswith("in-addr.arpa"):
            local_qrys.add(domain)
            continue
        channel_id = row["channel_id"]
        dns_answers = row["dns_a"]
        try:
            ips = dns_answers.split(",")
        except Exception:
            continue
        for ip in ips:
            ip_2_domains[channel_id][ip] = domain
    return ip_2_domains


def load_dns_data_from_pcap_csvs(crawl_data_dir):
    """Load IP address-to-domain mapping keyed by channel.

    Isolating DNS data by channel helps us avoid collisions.
    """
    dns_df = pd.DataFrame([])
    post_process_dir = join(crawl_data_dir, 'post-process')
    for dns_csv in glob(join(post_process_dir, "*dns.csv")):
        tmp_df = pd.read_csv(dns_csv, sep="|")
        channel_id = basename(dns_csv).split("-")[0]
        tmp_df['channel_id'] = channel_id
        dns_df = dns_df.append(tmp_df)
    replace_in_column_names(dns_df, ".", "_")
    dns_df.rename(columns={'frame_time_epoch': 'time'}, inplace=True)
    return dns_df, get_ip_domain_mapping_from_dns_df(dns_df)


def get_crawl_parameter(craw_dir, param_name):
    for crawl_config in glob(join(craw_dir, "crawl_info-*")):
        for line in open(crawl_config):
            if param_name in line:
                return line.rstrip().split("=")[-1]
    raise ValueError('Cannot find %s in %s' % (param_name, craw_dir))


def get_tv_ip_addr(craw_dir):
    return get_crawl_parameter(craw_dir, "TV_IP_ADDR")


def get_ott_device_mac(crawl_data_dir):
    """Return OTT device MAC adddress using the jsons.

    We use the MAC address to determine the set of IDs we use in
    the leak detection.
    """
    post_process_dir = join(crawl_data_dir, 'post-process')
    tv_ip = get_tv_ip_addr(crawl_data_dir)

    pattern = "*.http.json"
    for json_path in glob(join(post_process_dir, pattern)):
        tcp_payloads = load_json_file(json_path)
        for tcp_payload in tcp_payloads:
            payload = tcp_payload['_source']['layers']
            if payload["ip.src"][0] == tv_ip:
                return payload["eth.src"][0]
    else:
        raise Exception(
                "Cannot determine device MAC for leak detection."
                " Are post-process (http.json) files missing?")


# pip3 install ujson
def load_json_file(json_path):
    with open(json_path) as json_file:
        return ujson.load(json_file)


def decode_payload_data(tcp_data):
    try:
        return bytearray.fromhex(tcp_data).decode()
    except Exception:
        return tcp_data


def add_hostname_col_by_dns(df, ip_2_domains, ip_col_name):
    """Resolve server IP to domain using DNS packets from that channel.

    This should only be used when host header is not available. There may still
    be collisions (same IP used for multiple domains within a channel)
    """
    assert ip_col_name in ["ip_dst", "ip_src"]
    df["host_by_dns"] = df.apply(
        lambda x: ip_2_domains[x["channel_id"]].get(x[ip_col_name], ''), axis=1)
    df['domain_by_dns'] = df.host_by_dns.map(lambda x: get_fld("http://" + x, fail_silently=True))


def get_hostname_for_tcp_conn(row, http_domains, tls_snis, ip_2_domains_by_channel):
    """Return host for a TCP connection using HTTP, TLS SNI and DNS, in this order."""
    host = None
    conn_tuple = (row['channel_id'], row["tcp_stream"], row["ip_dst"], row["tcp_dstport"])
    host = http_domains.get(conn_tuple)
    # print("host by dns", host, row['tcp_stream'])
    if not host and row["tcp_dstport"] == 443:
        conn_tuple = (row['channel_id'], row["tcp_stream"], row["ip_dst"])
        host = tls_snis.get(conn_tuple)
        # print("host by SNI", host, row['tcp_stream'])

    if not host:
        # return ip_2_domains_by_channel[row["channel_id"]].get(row["ip_dst"], '')
        # print("Will return host by DNS", row['host_by_dns'], row['tcp_stream'])
        return row['host_by_dns']
    else:
        # print("Will return", host, row['tcp_stream'])
        return host


# Create global_df, containing all SSL/TCP streams SYN packets
def get_distinct_tcp_conns(crawl_name, name_resolution=True,
                           drop_from_unfinished=True, http_requests=None, adBlockStat=True):
    df = pd.DataFrame([])
    crawl_data_dir = get_crawl_data_path(crawl_name)
    tv_ip = get_tv_ip_addr(crawl_data_dir)
    post_process_dir = join(crawl_data_dir, 'post-process')
    print("Loading distinct TCP connections from %s " % post_process_dir)
    if name_resolution:
        # rIP2NameDB, _ = load_dns_data(crawl_data_dir)
        _, ip_2_domains_by_channel = load_dns_data_from_pcap_csvs(crawl_data_dir)

    pattern = "*.tcp_streams"
    if DEBUG:
        pattern = "com.w*.tcp_streams"
    #DEBUG com.amazon.rialto.cordova.webapp.webappb656e57
    for txt_path in glob(join(post_process_dir, pattern)):
        filename = basename(txt_path)
        channel_id = filename.split("-")[0]
        #print(txt_path)
        tmp_df = pd.read_csv(txt_path, sep=',', encoding='utf-8',
                             index_col=None,
                             error_bad_lines=False)
        tmp_df['channel_id'] = channel_id
        tmp_df['mitm_attempt'] = 0
        # tmp_df['mitm_fail'] = 0
        # take distinct TCP connections
        df = df.append(tmp_df.drop_duplicates("tcp.stream"))
    assert len(df)
    # replace dots in column names with underscores
    # mapping = {old_col: old_col.replace(".", "_") for old_col in df.columns}
    # df.rename(columns=mapping, inplace=True)
    replace_in_column_names(df, ".", "_")
    # only take outgoing TCP packets
    df = df[df.ip_src == tv_ip]
    if name_resolution and ip_2_domains_by_channel is not None:
        add_hostname_col_by_dns(df, ip_2_domains_by_channel, "ip_dst")

    # add human readable timestamps
    df['timestamp'] = df['frame_time_epoch'].map(lambda x: datetime.fromtimestamp(
            int(x)).strftime('%Y-%m-%d %H:%M:%S'))
    channel_df = read_channel_details_df()
    try:
        add_channel_details(df, channel_df)
    except Exception as e:
        # missing channel metadata
        print("ERR", e)
        pass

    playback_detected = get_playback_detection_results(crawl_name)
    df['playback'] = df['channel_id'].map(lambda x: x in playback_detected)
    crawl_statuses = get_crawl_status(crawl_data_dir)
    add_channel_crawl_status(df, crawl_statuses, drop_from_unfinished)
    http_hostnames = get_http_hostnames(crawl_name, http_requests)
    tls_snis = get_tls_snis(crawl_name)
    # 1- use host header from the HTTP request if available
    # 2- for connections to port 443: use SNI
    # 3- use DNS records if 1 and 2 fails
    df['host'] = df.apply(lambda x: get_hostname_for_tcp_conn(x, http_hostnames, tls_snis, ip_2_domains_by_channel), axis=1)
    df = replace_nan(df)

    if adBlockStat:
        add_adblocked_status(df)

    df['domain'] = df.host.map(lambda x: get_fld("http://" + x, fail_silently=True))
    return df


# Load all (All HTTP data)
def get_http1_df(crawl_data_dir):
    requests = []
    responses = []
    multiple_msg_cnt = 0
    post_process_dir = join(crawl_data_dir, 'post-process')
    dns_df, ip_2_domains = load_dns_data_from_pcap_csvs(crawl_data_dir)
    channel_df = read_channel_details_df()
    # print("Num. of channel details", len(channel_df))
    tv_ip = get_tv_ip_addr(crawl_data_dir)

    pattern = "*.http.json"
    if DEBUG:
        pattern = "com.w*.http.json"

    for json_path in glob(join(post_process_dir, pattern)):
        # print(json_path)
        channel_id = basename(json_path).split("-")[0]
        tcp_payloads = load_json_file(json_path)
        for tcp_payload in tcp_payloads:
            # payload has 6 fields when it doesn't contain any HTTP payload
            if len(tcp_payload['_source']['layers']) <= 7:
                continue
            payload = tcp_payload['_source']['layers']
            # some responses have multiple
            if any([len(x) > 1 for x in payload.values()]):
                multiple_msg_cnt += 1
                if payload["ip.src"][0] == tv_ip:
                # if "http.response.code" not in payload:
                    print("Pipelined request")
                # print ("Multiple payload", ("http.response.code" in payload))
            payload['channel_id'] = [channel_id]

            if payload["ip.dst"][0] == tv_ip:
                responses.append({field.replace(".", "_"): value[0]
                                  for field, value in payload.items()})
            else:
                requests.append({field.replace(".", "_"): value[0]
                                 for field, value in payload.items()})

    print(len(dns_df))
    assert len(requests)
    assert len(responses)
    print("Multiple messages", multiple_msg_cnt)

    req_df = pd.DataFrame(requests)
    resp_df = pd.DataFrame(responses)

    replace_in_column_names(req_df, "http_", "")
    replace_in_column_names(resp_df, "http_", "")
    replace_in_column_names(resp_df, "response_", "")

    req_df["http2"] = False
    resp_df["http2"] = False

    req_df["http2_type"] = ""

    add_hostname_col_by_dns(req_df, ip_2_domains, "ip_dst")
    add_hostname_col_by_dns(resp_df, ip_2_domains, "ip_src")
    try:
        add_channel_details(req_df, channel_df)
        add_channel_details(resp_df, channel_df)
    except Exception as e:
        # missing channel metadata
        # print(e)
        pass

    req_df.rename(columns={'file_data': 'post_data',
                           'request_full_uri': 'url',
                           'request_method': 'method',
                           'frame_time_epoch': 'time'}, inplace=True)
    resp_df.rename(columns={'file_data': 'body',
                            'frame_time_epoch': 'time'}, inplace=True)

    # raw data sent as POST or TCP payload is extracted as "data" column
    # in tshark.
    # See 12-1555086164.pcap (Netflix) or 219692-1555201676.pcap in
    # roku-data-20190412-122224 crawl for examples

    # move "data" to "post_data" column for POST requests
    if "post_data" not in req_df.columns:
        req_df["post_data"] = ""
    if "data" not in req_df.columns:
        req_df["data"] = ""
    req_df["post_data"] = req_df.apply(
        lambda x: decode_payload_data(x["data"])
        if x["post_data"] == "" and x["method"] == "POST"
        else x["post_data"], axis=1)
    # decode "data" column, exclude those from POST requests which are already
    # copied to the post_data column
    req_df["decoded_data"] = req_df.apply(
        lambda x: decode_payload_data(x['data'])
        if x['method'] != "POST" else "", axis=1)
    # req_df.drop("data", axis=1)

    req_df = replace_nan(req_df)
    resp_df = replace_nan(resp_df)
    req_df["url"] = req_df.apply(
        lambda x: x['url'] if x['url'] else x['request_uri'], axis=1)
    req_df = req_df[req_df.url != ""]
    req_df['host'] = req_df.url.map(lambda x: urlparse(x).hostname)
    add_domain_column(req_df, "url", "req_domain")
    return (req_df.drop(["eth_src", "request_uri", "data", "ip_src", "tcp_srcport"], axis=1),
            resp_df.drop(["eth_src", "ip_dst", "tcp_dstport"], axis=1),
            dns_df)


def add_domain_column(df, src_col_name="url", dst_col_name="req_domain"):
    df[dst_col_name] = df[src_col_name].map(
        lambda x: get_fld(x, fail_silently=True))


def add_channel_details(df, channel_df):
    df['channel_name'] = df['channel_id'].map(lambda x: channel_df.loc[x]['channel_name'])
    df['rank'] = df['channel_id'].map(lambda x: channel_df.loc[x]['rank'])
    df['category'] = df['channel_id'].map(lambda x: channel_df.loc[x]['category'])


def add_channel_crawl_status(df, crawl_statuses, drop_from_unfinished=False):
    df['status'] = df.channel_id.map(lambda x: crawl_statuses.get(x, "UNKNOWN"))
    if drop_from_unfinished:
        df = df[df.status == "TERMINATED"]


def get_http_df(crawl_name, drop_from_unfinished=True):
    # print("Will load HTTP dataframe for", crawl_data_dir)
    crawl_data_dir = get_crawl_data_path(crawl_name)
    h1_requests, h1_responses, h1_dns = get_http1_df(crawl_data_dir)
    h2_requests, h2_responses, h2_dns = get_http2_df(crawl_data_dir)
    requests = h1_requests.append(h2_requests, sort=False)
    responses = h1_responses.append(h2_responses, sort=False)

    crawl_statuses = get_crawl_status(crawl_data_dir)
    add_channel_crawl_status(requests, crawl_statuses, drop_from_unfinished)
    add_channel_crawl_status(responses, crawl_statuses, drop_from_unfinished)

    playback_detected = get_playback_detection_results(crawl_name)
    requests['playback'] = requests['channel_id'].map(lambda x: x in playback_detected)
    responses['playback'] = responses['channel_id'].map(lambda x: x in playback_detected)

    add_adblocked_status(requests, check_by_url=True)
    requests["tcp_stream"] = pd.to_numeric(requests["tcp_stream"])
    requests["tcp_dstport"] = pd.to_numeric(requests["tcp_dstport"])
    return replace_nan(requests), replace_nan(responses), h1_dns


# https://www.iana.org/assignments/http2-parameters/http2-parameters.xhtml#frame-type
HTTP2_FRAME_TYPE_DATA = "0"
HTTP2_FRAME_TYPE_HEADERS = "1"
HTTP2_MIN_NUM_FIELDS = 7


# Load HTTP2 data
def get_http2_df(crawl_data_dir):
    requests = []
    responses = []
    decode_errors = 0
    channels = set()
    post_process_dir = join(crawl_data_dir, 'post-process')
    tv_ip = get_tv_ip_addr(crawl_data_dir)
    dns_df, ip_2_domains = load_dns_data_from_pcap_csvs(crawl_data_dir)
    channel_df = read_channel_details_df()
    # print("Num. of channel details", len(channel_df))

    pattern = "*.http2.json"
    if DEBUG:
        pattern = "com.w*.http2.json"

    for json_path in glob(join(post_process_dir, pattern)):
        # print(json_path)
        channel_id = basename(json_path).split("-")[0]
        tcp_payloads = load_json_file(json_path)
        for tcp_payload in tcp_payloads:
            # payload has 7 fields when it doesn't contain any HTTP payload
            if len(tcp_payload['_source']['layers']) <= HTTP2_MIN_NUM_FIELDS:
                continue
            payload = dict()
            payload['channel_id'] = channel_id
            channels.add(channel_id)
            for field, value in tcp_payload['_source']['layers'].items():
                field = field.replace(".", "_")
                if field == "http2_data_data":
                    # print(tcp_payload['_source']['layers'])
                    if tcp_payload['_source']['layers']["ip.dst"] == tv_ip:
                        # skip response bodies
                        continue
                    if isinstance(value, list):
                        value = ":".join(value)
                    try:
                        payload[field] = bytearray.fromhex(value.replace(":", "")).decode()
                    except Exception:
                        # print("DEC ERR", json_path, tcp_payload)
                        decode_errors += 1
                elif field == "http2_type":
                    payload[field] = ",".join(value)
                    # list based fields
                elif field in ["http2_header_name", "http2_header_value"]:
                    payload[field] = value
                else:  # fields extracted as a list but contain only one element
                    assert len(value) == 1
                    payload[field] = value[0]

            if (HTTP2_FRAME_TYPE_HEADERS not in payload["http2_type"]):
                continue

            if "http2_header_name" not in payload:
                # DATA frame without any header
                if payload["ip_dst"] == tv_ip:
                    responses.append(payload)
                else:
                    requests.append(payload)
                continue
            # frames with headers
            header_names = payload["http2_header_name"]
            header_values = payload["http2_header_value"]
            assert len(header_names) == len(header_values)
            headers = {}

            for idx, header_name in enumerate(header_names):
                headers[header_name.strip(":").lower()] = header_values[idx]

            if "status" in headers:  # response
                assert payload["ip_dst"] == tv_ip
                payload["content_type"] = headers.get("content-type")
                payload["response_code"] = headers["status"]
                payload["set-cookie"] = headers.get("set-cookie", "")
                payload["location"] = headers.get("location", "")
                responses.append(payload)
            else:  # request
                payload["host"] = headers["authority"]
                payload["user_agent"] = headers.get("http.useragent", "")
                payload["url"] = "%s://%s%s" % (
                    headers["scheme"], headers["authority"], headers["path"])
                payload["method"] = headers["method"]
                payload["cookie"] = headers.get("cookie", "")
                payload["referer"] = headers.get("referer", "")
                if payload["url"]:
                    requests.append(payload)
    if not len(requests):
        return pd.DataFrame([]), pd.DataFrame([]), pd.DataFrame([])
    req_df = pd.DataFrame(requests)
    resp_df = pd.DataFrame(responses)

    add_hostname_col_by_dns(req_df, ip_2_domains, "ip_dst")
    add_hostname_col_by_dns(resp_df, ip_2_domains, "ip_src")
    add_channel_details(req_df, channel_df)
    add_channel_details(resp_df, channel_df)

    req_df["http2"] = True
    resp_df["http2"] = True

    req_df.rename(columns={'http2_data_data': 'post_data',
                           'frame_time_epoch': 'time'}, inplace=True)
    resp_df.rename(columns={'http2_data_data': 'response_body',
                            'frame_time_epoch': 'time'}, inplace=True)

    replace_in_column_names(req_df, "http_", "")
    replace_in_column_names(resp_df, "http_", "")
    replace_in_column_names(req_df, "request_", "")
    replace_in_column_names(resp_df, "response_", "")

    HTTP2_REQ_DROP = ["http2_header_name", "http2_header_value", "eth_src", "ip_src", "tcp_srcport"]
    HTTP2_RESP_DROP = ["http2_header_name", "http2_header_value", "eth_src", "ip_dst", "tcp_dstport"]
    # print("Decode errors", decode_errors)
    # print("channels", channels)
    req_df['host'] = req_df.url.map(lambda x: urlparse(x).hostname)
    add_domain_column(req_df, "url", "req_domain")
    return (req_df.drop(HTTP2_REQ_DROP, axis=1).replace(np.nan, '', regex=True),
            resp_df.drop(HTTP2_RESP_DROP, axis=1).replace(np.nan, '', regex=True),
            dns_df)


def get_playback_detection_results(crawl_name):
    playback_detected = dict()
    craw_dir = get_crawl_data_path(crawl_name)
    for log_file in glob(join(craw_dir, "logs", "*.log")):
        channel_id = basename(log_file).rsplit("-", 1)[0]
        for l in open(log_file):
            if "SMART_CRAWLER: Playback detected on channel" in l:
                time_str = l.split('[')[1].split(']')[0]
                # the following works with python 3 
                # timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f').timestamp()
                playback_detected[channel_id] = time_str
    return playback_detected


def get_n_successful_channels(crawl_name):
    """Return the number channels crawled without problem."""
    crawl_dir = get_crawl_data_path(crawl_name)
    crawl_statuses = get_crawl_status(crawl_dir)
    return sum(1 for status in crawl_statuses.values() if status == "TERMINATED")


def print_crawl_summary(crawl_name):
    detected = get_playback_detection_results(crawl_name)
    crawl_dir = get_crawl_data_path(crawl_name)
    crawl_statuses = get_crawl_status(crawl_dir)
    n_success = sum(1 for status in crawl_statuses.values() if status == "TERMINATED")
    print("Crawl summary:", crawl_name, crawl_dir)
    print("---------------------")
    print ("Total channels", len(crawl_statuses))
    print ("Successful crawls", n_success)
    print("Results", Counter(crawl_statuses.values()))
    print ("Playback detected in", len(detected))
    return n_success

# Create df containing all SSL handshakes
def get_distinct_ssl_conns(crawl_name, name_resolution=True):
    df = pd.DataFrame([])
    crawl_data_dir = get_crawl_data_path(crawl_name)
    post_process_dir = join(crawl_data_dir, 'post-process')
    print("Loading distinct SSL connections from %s " % post_process_dir)

    for txt_path in glob(join(post_process_dir, "*.ssl_connections")):
        filename = basename(txt_path)
        channel_id = filename.split("-")[0]
        #print(txt_path)
        tmp_df = pd.read_csv(txt_path, sep='|', encoding='utf-8', index_col=None)
        tmp_df['channel_id'] = channel_id
        tmp_df["ssl.record.content_type"] = tmp_df["ssl.record.content_type"].astype(str)
        # print(df["ssl.record.content_type"].value_counts())
        # print("before", len(df))
        tmp_df = tmp_df[tmp_df["ssl.record.content_type"].str.contains("22")]
        df = df.append(tmp_df.drop_duplicates("tcp.stream"))
    assert len(df)

    # replace dots in column names with underscores
    # mapping = {old_col: old_col.replace(".", "_") for old_col in df.columns}
    # df.rename(columns=mapping, inplace=True)
    replace_in_column_names(df, ".", "_")
    return df


def get_tls_snis(crawl_name):
    tls_snis = dict()
    ssl_df = get_distinct_ssl_conns(crawl_name)
    ssl_df = replace_nan(ssl_df)
    for _, row in ssl_df.iterrows():
        tls_snis[(row['channel_id'], row["tcp_stream"], row["ip_dst"])] = row["ssl_handshake_extensions_server_name"]
    return tls_snis



def get_resp_url(row, req_urls):
    return req_urls.get((row['channel_id'], int(row["tcp_stream"]), row["ip_src"], int(row["tcp_srcport"])))


def get_https_upgrade_redirectors(crawl_name, http_req, http_resp):
    http_resp = http_resp[http_resp.code != ""]
    req_urls = get_http_hostnames(crawl_name, requests=http_req, value_type="url")
    http_resp['url'] = http_resp.apply(lambda x: get_resp_url(x, req_urls), axis=1)
    assert not len(http_resp[http_resp.url==""])
    http_resp = replace_nan(http_resp)
    redirects = http_resp[http_resp.location != ""]

    add_domain_column(redirects, "url", "req_domain")
    add_domain_column(redirects, "location", "loc_domain")
    redirects['https_upgrade'] = redirects.apply(
        lambda x: (x.tcp_srcport == "80" and x.location.startswith('https://')
        and x.req_domain==x.loc_domain), axis=1)
    https_upgrades = redirects[redirects.https_upgrade]
    cross_origin_redirects = redirects[redirects.req_domain!=redirects.loc_domain]
    return redirects, https_upgrades, cross_origin_redirects


def get_last_smart_launch_times(crawl_name):
    """Use timestamps.txt files to find the beginning of smart launch for each channel.
    
    We will use this to only consider leaks from the last launch.
    """
    last_smart_launch_times = {}
    crawl_dir = get_crawl_data_path(crawl_name)
    for fname in glob(join(crawl_dir, "logs/*-timestamps.txt")):
        channel_name = basename(fname).split("-")[0]
        for l in open(fname):
            # find the beginning of the smart launch
            if "key-seq-01" in l and "key-0" not in l:
                last_smartlaunch_ts = l.rstrip().split(",")[-1]
                last_smart_launch_times[channel_name] = last_smartlaunch_ts

    return last_smart_launch_times

if __name__ == '__main__':
    pass

