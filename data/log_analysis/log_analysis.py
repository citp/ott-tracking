import pandas as pd
from urllib.request import urlopen
from urllib.parse import urlparse
from tld import parse_tld
import json
import sys
import ntpath
import re
import time
import os
import ipaddress

#PUBLIC_SUFFIX_LIST_URL = https://publicsuffix.org/list/public_suffix_list.dat
PUBLIC_SUFFIX_LIST= 'public_suffix_list.dat'
channel_list = '../../scrape/platforms/roku/channel_list.txt'

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
        #return re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', req_line)[0]
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

    def format_csv(self, request_line):
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
        #print(res)
        return res

    def find_regex(self, regex):
        result_list = []
        with open(self.log_file_fullpath) as f:
            for line in f:
                # print(line)
                result = regex.search(line)
                if result is not None:
                    #res = str(self.channel_id) + '\t' + str(self.start_ts) + '\t' + line.split()[2]
                    res = self.format_csv(line)
                    print(res)
                    result_list.append(res)
        return result_list

    def https_urls(self):
        regex = re.compile('(GET|POST) https\:*')
        self.find_regex(regex)

    def http_urls(self):
        regex = re.compile('(GET|POST) http\:*')
        self.find_regex(regex)

    def pass_through(self):
        return


BANNER="channel_id	start_ts	command	select_idx	eth_src	ip_dst	req_method	protocol	url	channel_name	domain	host	rank	category"
def test():
    print(BANNER)
    channels = load_roku_channel_details()
    log_folder_name = sys.argv[1]
    for root, dirs, files in os.walk(log_folder_name):
        for file in files:
            if file.endswith(".log"):
                log_reader = LogFileReader(os.path.join(root, file), channels)
                #print('---HTTPS---')
                log_reader.https_urls()
                #print('---HTTP---')
                log_reader.http_urls()


if __name__ == '__main__':
    test()


#"104458-1549016122.log:10.42.0.119:60948: GET https://player.vimeo.com/external/85009516.hd.mp4?s=1112830b731d1291ae084647833a0af5"

