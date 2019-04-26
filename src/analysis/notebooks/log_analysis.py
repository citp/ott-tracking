from urllib.parse import urlparse
import ntpath
import ujson
import numpy as np
import re
import os
import ipaddress
import sys
import pandas as pd
import json
import traceback
from datetime import datetime
from glob import glob
from os.path import join, sep, isfile, basename
from collections import defaultdict


#PUBLIC_SUFFIX_LIST_URL = https://publicsuffix.org/list/public_suffix_list.dat
PUBLIC_SUFFIX_LIST= 'public_suffix_list.dat'
channel_list = '../../scrape/platforms/roku/channel_lists/all_channel_list.txt'

def load_roku_channel_details():
    channels = []
    with open(channel_list) as fp:
        for line in fp:
            record = json.loads(line)
            channels.append(record)
    return channels




def read_dns_db():
    return

class PcapFileReader(object):

    def __init__(self, pcap_file):
        return

class LogFileReader(object):

    def __init__(self, log_file, channels):
        self.log_file_fullpath = os.path.abspath(log_file)
        self.log_file_name = ntpath.basename(log_file)
        self.get_channel_id()
        self.get_start_ts()
        self.init_unknown_fields()
        self.channel_info(channels)
        self.tls_hs_list = set()
        self.tls_pass_thru_list = set()
        return

    def init_unknown_fields(self):
        self.command = "\"\""
        self.select_idx = "\"\""
        self.eth_src = "\"\""
    def get_channel_id(self):
        self.channel_id = self.log_file_name.split('-')[0]

    def get_start_ts(self):
        self.start_ts = self.log_file_name.split('-')[1].split('.')[0]

    def channel_info(self, channels):
        for channel_list_item in channels:
            if str(channel_list_item['id']) == self.channel_id:
                #print(channel_list_item)
                self.category = channel_list_item['_category']
                self.scrape_ts  = channel_list_item['_scrape_ts']
                self.accessCode = channel_list_item['accessCode']
                self.desc = channel_list_item['desc']
                self.id = channel_list_item['id']
                self.channel_name = channel_list_item['name']
                self.payment = channel_list_item['payment']
                self.price = channel_list_item['price']
                self.rankByWatched = channel_list_item['rankByWatched']
                self.rating = channel_list_item['rating']
                self.thumbnail = channel_list_item['thumbnail']
                break

    def get_method(self, req_line):
        if 'GET' in req_line:
            return 'GET'
        if 'POST' in req_line:
            return 'POST'

    def get_proto(self, req_line):
        regexHTTPS = re.compile('(GET|POST) https\:*')
        regexHTTP = re.compile('(GET|POST) http\:*')
        if regexHTTPS.search(req_line):
            return 'https'
        if regexHTTP.search(req_line):
            return 'http'

    def get_url(self, req_line):
        # return re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', req_line)[0]
        return req_line.split()[2]

    def get_host(self, url):
        return urlparse(url).netloc

    def get_tld(self, url):
        hostname = self.get_host(url)
        try:
            ipaddress.ip_address(hostname)
            return hostname
        except (ValueError, TypeError):
            tokens = hostname.split('.')[::-1]
            res = tokens[0]
            if len(tokens) > 1:
                res = tokens[1] + '.' + res
            return res

    def get_dst_ip(self, url):
        return "\"\""

    def format_http_csv(self, request_line):
        #print(request_line)
        req_url = self.get_url(request_line)
        res = ''
        res += str(self.channel_id) + '\t'
        res += str(self.start_ts) + '\t'
        res += str(self.command) + '\t'
        res += str(self.select_idx) + '\t'
        res += str(self.eth_src) + '\t'
        res += str(self.get_dst_ip(request_line)) + '\t'
        res += str(self.get_method(request_line)) + '\t'
        res += str(self.get_proto(request_line)) + '\t'
        res += str('"' + req_url + '"') + '\t'
        res += str(self.channel_name) + '\t'
        res += str(self.get_tld(req_url)) + '\t'
        res += str(self.get_host(req_url)) + '\t'
        res += str(self.rankByWatched) + '\t'
        res += str(self.category)
        print(res)
        return res

    def tls_handshake_fail_hdl(self, request_line):
        #Assuming this format:
        #[2019-03-12 15:23:47.387505] 10.42.0.119:48764: Client Handshake failed. \
        #The client may not trust the proxy's certificate for api.sr.roku.com.
        self.tls_hs_list.add(request_line.split()[-1])

    def tls_pass_thru_hdl(self, request_line):
        global rIP2NameDB
        # Assuming this format:
        #[2019-03-12 15:23:52.560586] TLS passthrough for ('52.204.87.181', 443)
        # [mapped to scribe.logs.roku.com.].
        tmp = request_line.split()[3]
        srv_addr = re.sub('\(|\,|\'', '', tmp)

        if "mapped to" in request_line:
            domain = request_line.split()[-1]
        elif srv_addr in rIP2NameDB:
            domain = rIP2NameDB[srv_addr][0]
        else:
            print("Server doesn't have a domain name! Couldn't find the server name in the "
                  "DNS database either! Skipping!")
            print(request_line)
            return
        self.tls_pass_thru_list.add(domain)

    def find_regex(self, regex, format_func):
        result_list = []
        with open(self.log_file_fullpath) as f:
            for line in f:
                # print(line)
                result = regex.search(line)
                if result is not None:
                    #res = str(self.channel_id) + '\t' + str(self.start_ts) + '\t' + line.split()[2]
                    res = format_func(line)
                    result_list.append(res)
        return result_list

    def https_urls(self):
        regex = re.compile('(GET|POST) https\:*')
        self.find_regex(regex, self.format_http_csv)

    def http_urls(self):
        regex = re.compile('(GET|POST) http\:*')
        self.find_regex(regex, self.format_http_csv)

    def tls_handshake_fail(self):
        regex = re.compile('Client Handshake failed. The client may not trust the proxy\'s certificate for*')
        self.find_regex(regex, self.tls_handshake_fail_hdl)

    def tls_pass_thru(self):
        regex = re.compile('TLS passthrough for*')
        self.find_regex(regex, self.tls_pass_thru_hdl)

    def pass_through(self):
        return

BANNER="channel_id	start_ts	command	select_idx	eth_src	ip_dst	req_method	protocol	url	channel_name	domain	host	rank	category"
def http_s_log_to_csv(root_dir):
    print(BANNER)
    channels = load_roku_channel_details()
    log_folder_name = os.path.join(root_dir, "logs")
    for root, dirs, files in os.walk(log_folder_name):
        for file in files:
            if file.endswith(".log"):
                log_reader = LogFileReader(os.path.join(root, file), channels)
                #print('---HTTPS---')
                log_reader.https_urls()
                #print('---HTTP---')
                log_reader.http_urls()

def tls_pass_thru_list(root_dir):
    channels = load_roku_channel_details()
    log_folder_name = os.path.join(root_dir, "logs")
    for root, dirs, files in os.walk(log_folder_name):
        for file in files:
            if file.endswith(".log"):
                log_reader = LogFileReader(os.path.join(root, file), channels)
                log_reader.tls_handshake_fail()
                log_reader.tls_pass_thru()
                if bool(log_reader.tls_hs_list) and bool(log_reader.tls_pass_thru_list):
                    # print("TLS Handshake Failure Domains: " + str(log_reader.tls_hs_list))
                    #print("TLS Pass Through Domains: " + str(log_reader.tls_pass_thru_list))
                    delta = log_reader.tls_hs_list.difference(log_reader.tls_pass_thru_list)
                    if delta:
                        print("Info for Channel: " + log_reader.channel_name + " - " + log_reader.channel_id)
                        print("Delta: " + str(delta))
                        print('-----------------')


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


def load_pcaps(root_dir, transform_func):
    pcap_folder_name = os.path.join(root_dir, "pcaps")
    for root, dirs, files in os.walk(pcap_folder_name):
        for file in files:
            if file.endswith(".pcap"):
                #channel_name = file.split('-')[0]
                try:
                    transform_func(root, file)
                except Exception:
                    print("Error processing file %s" % file)
                    traceback.print_exc()


def find_tls_failures_pcap(root_dir):
    tls_failure_list = {}
    def tls_failure_find(root, file , failure_list = tls_failure_list):
        channel_name = file.split('-')[0]
        file_name = os.path.join(root, file)
        print(channel_name)
        # "./extract_fields.sh -i /tmp/amazon-data-100-nomitm/pcaps -f "http" -e eth.src -e ip.dst -e http.request.method -e http.host"

    load_pcaps(root_dir, tls_failure_find)

def test():
    global rIP2NameDB, rName2IPDB, channel_timstamps
    root_dir = sys.argv[1]
    (rIP2NameDB, rName2IPDB) = load_dns_data(root_dir)
    #channel_timstamps = load_timestamp_json(root_dir)
    #http_s_log_to_csv(root_dir)
    #tls_pass_thru_list(root_dir)
    find_tls_failures_pcap(root_dir)



def load_timestamps_from_crawl_data(root_dir):
    # Load Timestamps
    timestamps = defaultdict(list)
    print("Loading timestamp data from %s" % root_dir)
    for txt_path in glob(root_dir + "/logs/*timestamps.txt", recursive=True):
        filename = txt_path.split(sep)[-1]
        channel_name = filename.split("-")[0]
        try:
            for l in open(txt_path):
                label, ts = l.split(",")
                timestamps[channel_name].append((label, float(ts)))
        except Exception:
            print("Couldn't open %s" % filename)
            traceback.print_exc()
    return timestamps


'''Older version
def load_timestamp_json(root_dir):
    channel_timstamps = {}
    log_folder_name = os.path.join(root_dir, "logs")
    for root, dirs, files in os.walk(log_folder_name):
        for file in files:
            if file.endswith("-timestamps.json"):
                channel_name = file.replace('-timestamps.json','')
                file_name = os.path.join(root, file)
                try:
                    with open(file_name) as f:
                        data = json.load(f)
                        channel_timstamps[channel_name] = data
                except Exception:
                    print("Couldn't open %s" % file_name)
                    traceback.print_exc()
    return channel_timstamps
'''


#Create global_df, containing all SSL/TCP streams SYN packets
# def gen_network_df(root_dir):
def get_distinct_tcp_conns(crawl_data_dir, name_resolution=True):
    df = pd.DataFrame([])
    post_process_dir = join(crawl_data_dir, 'post-process')
    print("Loading distinct TCP connections from %s " % post_process_dir)
    if name_resolution:
        rIP2NameDB, _ = load_dns_data(crawl_data_dir)
        _, ip_2_domains_by_channel = load_dns_data_from_pcap_csvs(crawl_data_dir)

    for txt_path in glob(join(post_process_dir, "*.tcp_streams")):
        filename = basename(txt_path)
        channel_name = filename.split("-")[0]
        tmp_df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
        tmp_df['channel_name'] = channel_name
        tmp_df['mitm_attempt'] = 0
        # tmp_df['mitm_fail'] = 0
        # take distinct TCP connections
        df = df.append(tmp_df.drop_duplicates("tcp.stream"))
    assert len(df)

    # replace dots in column names with underscores
    mapping = {old_col:old_col.replace(".", "_") for old_col in df.columns}
    df.rename(columns=mapping, inplace=True)

    if name_resolution and rIP2NameDB is not None:
        # df["hostname"] = df["ip_dst"].map(lambda x: get_domain_by_ip(x, rIP2NameDB))
        df["hostname"] = df.apply(lambda x: ip_2_domains_by_channel[x["channel_name"]].get(x["ip_dst"], ''), axis=1)
    # add human readable timestamps
    df['timestamp'] = df['frame_time_epoch'].map(lambda x: datetime.fromtimestamp(
            int(x)).strftime('%Y-%m-%d %H:%M:%S'))
    return df


def get_unique_tcp_stream_ids(post_process_dir, suffix):
    unique_tcp_conn_ids = {}
    assert suffix in ["*.pcap.ssl_fail", "*.pcap.mitmproxy-attempt", "*.pcap.ssl_connections"]
    for txt_path in glob(join(post_process_dir, suffix)):
        filename = basename(txt_path)
        channel_name = filename.split("-")[0]

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
        unique_tcp_conn_ids[channel_name] = df['tcp.stream'].unique()
    return unique_tcp_conn_ids


def get_crawl_status(crawl_dir):
    status_dict = {}
    for f in glob(join(crawl_dir, "finished", "*.txt")):
        channel_name = basename(f).rsplit(".", 1)[0]
        status = open(f).read().rstrip()
        status_dict[channel_name] = status
    return status_dict

def get_epoch(row, channel_timestamps):
    ch_timestamps = channel_timestamps[row["channel_name"]]
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
        domain = row["dns.qry.name"]
        if domain.endswith("in-addr.arpa"):
            local_qrys.add(domain)
            continue
        channel_name = row["channel_name"]
        dns_answers = row["dns.a"]
        try:
            ips = dns_answers.split(",")
        except Exception:
            continue
        for ip in ips:
            ip_2_domains[channel_name][ip] = domain
    return ip_2_domains


def load_dns_data_from_pcap_csvs(crawl_data_dir):
    """Load IP address-to-domain mapping keyed by channel.

    Isolating DNS data by channel helps us avoid collisions.
    """
    dns_df = pd.DataFrame([])
    post_process_dir = join(crawl_data_dir, 'post-process')
    for dns_csv in glob(join(post_process_dir, "*dns.csv")):
        tmp_df = pd.read_csv(dns_csv, sep="|")
        channel_name = basename(dns_csv).split("-")[0]
        tmp_df['channel_name'] = channel_name
        dns_df = dns_df.append(tmp_df)
    return dns_df, get_ip_domain_mapping_from_dns_df(dns_df)


def get_tv_ip_addr(craw_dir):
    for crawl_config in glob(join(craw_dir, "crawl_info-*")):
        for line in open(crawl_config):
            if "TV_IP_ADDR" in line:
                return line.rstrip().split("=")[-1]

# pip3 install ujson
def load_json_file(json_path):
    with open(json_path) as json_file:
        return ujson.load(json_file)

    
# Load all (All HTTP data)
def get_http_df(crawl_data_dir):
    print (crawl_data_dir)
    post_process_dir = join(crawl_data_dir, '*post-process')
    requests = []
    responses = []
    multiple_msg_cnt = 0
    dns_df, ip_2_domains = load_dns_data_from_pcap_csvs(crawl_data_dir)
    tv_ip = get_tv_ip_addr(crawl_data_dir)

    for json_path in glob(join(post_process_dir, "*http.json")):
        # print(json_path)
        channel_name = basename(json_path).split("-")[0]
        tcp_payloads = load_json_file(json_path)
        for tcp_payload in tcp_payloads:
            # payload has 6 fields when it doesn't contain any HTTP payload
            if len(tcp_payload['_source']['layers']) <= 7:
                continue
            payload = tcp_payload['_source']['layers']
            # some responses have multiple
            if any([len(x)>1 for x in payload.values()]):
                multiple_msg_cnt += 1
                if "http.response.code" not in payload:
                    print ("Pipelined request", payload)
                # print ("Multiple payload", ("http.response.code" in payload))
            payload['channel_name'] = [channel_name]
            
            if payload["ip.dst"][0] == tv_ip:
                responses.append({field.replace(".", "_"): value[0] for field, value in payload.items()})
            else:
                requests.append({field.replace(".", "_"): value[0] for field, value in payload.items()})
    
    assert len(requests)
    assert len(responses)
    print ("Multiple messages", multiple_msg_cnt)
    req_df = pd.DataFrame(requests)
    resp_df = pd.DataFrame(responses)

    #req_df["hostname"] = req_df["ip_dst"].map(lambda x: get_domain_by_ip(x, rIP2NameDB))
    req_df["hostname"] = req_df.apply(lambda x: ip_2_domains[x["channel_name"]].get(x["ip_dst"], ''), axis=1)
    resp_df["hostname"] = resp_df.apply(lambda x: ip_2_domains[x["channel_name"]].get(x["ip_src"], ''), axis=1)

    req_df.rename(columns={'http_file_data':'post_data'}, inplace=True)
    resp_df.rename(columns={'http_file_data':'response_body'}, inplace=True)

    for df in [req_df, resp_df]:
        mapping = {col_name:col_name.replace("http_", "") for col_name in df.columns}
        df.rename(columns=mapping, inplace=True)
    req_df["request_full_uri"] = req_df.apply(lambda x: x['request_full_uri'] if x['request_full_uri'] else x['request_uri'], axis=1)
    return (req_df.drop("eth_src", axis=1).replace(np.nan, '', regex=True),
            resp_df.drop("eth_src", axis=1).replace(np.nan, '', regex=True),
            dns_df)

# https://www.iana.org/assignments/http2-parameters/http2-parameters.xhtml#frame-type
HTTP2_FRAME_TYPE_DATA = "0"
HTTP2_FRAME_TYPE_DATA = "1"

# Load all (All HTTP data)

def get_http2_df(crawl_data_dir):
    print ("get_http2_df", crawl_data_dir)
    post_process_dir = join(crawl_data_dir, 'post-process')
    requests = []
    responses = []
    decode_errors = 0
    channels = set()
    tv_ip = get_tv_ip_addr(crawl_data_dir)
    dns_df, ip_2_domains = load_dns_data_from_pcap_csvs(crawl_data_dir)

    for json_path in glob(join(post_process_dir, "*http2.json")):
        # print(json_path)
        channel_name = basename(json_path).split("-")[0]
        tcp_payloads = load_json_file(json_path)
        for tcp_payload in tcp_payloads:
            # payload has 7 fields when it doesn't contain any HTTP payload
            HTTP2_MIN_NUM_FIELDS = 7  # num. of required fields, HTTP packets have more
            if len(tcp_payload['_source']['layers']) <= HTTP2_MIN_NUM_FIELDS:
                continue

            payload = {}
            payload['channel_name'] = channel_name
            channels.add(channel_name)
            for field, value in tcp_payload['_source']['layers'].items():
                field = field.replace(".", "_")
                if field == "http2_data_data":
                    if payload["ip_dst"] == tv_ip:
                        continue
                    if isinstance(value, list):
                        value = ":".join(value)
                    try:
                        payload[field] = bytearray.fromhex(value.replace(":", "")).decode()
                    except:
                        print("DEC ERR", json_path, tcp_payload)
                        decode_errors += 1
                elif field == "http2_type":
                    payload[field] = ",".join(value)
                elif field in ["http2_header_name", "http2_header_value"]:  # list based fields
                    payload[field] = value
                else:  # fields extracted as lists but contain only one element
                    assert len(value) == 1
                    payload[field] = value[0]

            if HTTP2_FRAME_TYPE_DATA not in payload["http2_type"] and HTTP2_FRAME_TYPE_DATA not in payload["http2_type"]:
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
                payload["content_type"] = headers["content-type"]
                payload["response_code"] = headers["status"]
                payload["set-cookie"] = headers.get("set-cookie", "")
                payload["location"] = headers.get("location", "")
                responses.append(payload)
            else:  # request
                # payload["host"] = headers["authority"]
                payload["user_agent"] = headers["http.useragent"]
                payload["request_full_uri"] = "%s://%s%s" %(headers["scheme"], headers["authority"], headers["path"])
                payload["request_method"] = headers["method"]
                payload["cookie"] = headers.get("cookie", "")
                payload["referer"] = headers.get("referer", "")
                requests.append(payload)

    req_df = pd.DataFrame(requests)
    resp_df = pd.DataFrame(responses)

    #req_df["hostname"] = req_df["ip_dst"].map(lambda x: get_domain_by_ip(x, rIP2NameDB))
    req_df["hostname"] = req_df.apply(lambda x: ip_2_domains[x["channel_name"]].get(x["ip_dst"], ''), axis=1)
    resp_df["hostname"] = resp_df.apply(lambda x: ip_2_domains[x["channel_name"]].get(x["ip_src"], ''), axis=1)

    req_df.rename(columns={'http2_data_data':'post_data'}, inplace=True)
    resp_df.rename(columns={'http2_data_data':'response_body'}, inplace=True)

    for df in [req_df, resp_df]:
        mapping = {col_name:col_name.replace("http_", "") for col_name in df.columns}
        df.rename(columns=mapping, inplace=True)
    HTTP2_REQ_DROP = ["http2_header_name", "http2_header_value", "ip_src", "tcp_srcport", "eth_src"]
    HTTP2_RESP_DROP = ["http2_header_name", "http2_header_value", "ip_dst", "tcp_dstport", "eth_src"]
    print ("Decode errors", decode_errors)
    print ("channels", channels)
    return (req_df.drop(HTTP2_REQ_DROP, axis=1).replace(np.nan, '', regex=True),
            resp_df.drop(HTTP2_RESP_DROP, axis=1).replace(np.nan, '', regex=True),
            dns_df)


if __name__ == '__main__':
    test()


#"104458-1549016122.log:10.42.0.119:60948: GET https://player.vimeo.com/external/85009516.hd.mp4?s=1112830b731d1291ae084647833a0af5"

