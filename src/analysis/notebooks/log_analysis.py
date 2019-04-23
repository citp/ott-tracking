from urllib.parse import urlparse
import ntpath
import re
import os
import ipaddress
import sys
import pandas as pd
import json
import traceback
from glob import glob
from os.path import join, sep, isfile, basename
from _collections import defaultdict


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
def get_distinct_tcp_conns(root_dir):
    print("Generating Global DF from %s " % root_dir)
    df = pd.DataFrame([])
    for txt_path in glob(join(root_dir, "*.uniq_tcp_conns")):
        filename = basename(txt_path)
        #print(txt_path)
        channel_name = filename.split("-")[0]
        #print(channel_name)
        #print(txt_path)
        tmp_df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
        tmp_df['channel_name'] = channel_name
        tmp_df['mitm_attempt'] = 0
        tmp_df['mitm_fail'] = 0
        df = df.append(tmp_df)
        #print(len(global_df.index))
        #print(global_df)
    return df


def get_tcp_conns(post_process_dir, suffix):
    # Find all tls failure due to invalid cert:
    unique_tcp_conn_ids = {}
    assert suffix in ["*.pcap.ssl_fail", "*.pcap.mitmproxy-attempt", "*.pcap.ssl_success"]
    for txt_path in glob(join(post_process_dir, suffix)):
        filename = txt_path.split(sep)[-1]
        channel_name = filename.split("-")[0]
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
    packet_timestamp = row["frame.time_epoch"]
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

if __name__ == '__main__':
    test()


#"104458-1549016122.log:10.42.0.119:60948: GET https://player.vimeo.com/external/85009516.hd.mp4?s=1112830b731d1291ae084647833a0af5"

