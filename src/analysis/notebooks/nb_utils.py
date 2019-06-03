import numpy as np
import json
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

import pandas as pd
import ipaddress
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from tld import get_fld
from glob import glob
from os.path import join, sep, isdir
from IPython.display import display_html
from tabulate import tabulate

TSHARK_FIELD_SEP = "|"
ROKU_MACS = ["d8:31:34:22:e6:ff"]  # Roku MAC addresses to filter packets

CRAWL_ROOT_DIRS = [
    '/mnt/iot-house/crawl-data/',
    '/home/gacar/dev/smart-tv/data',
    '/media/gacar/Data/iot-house/',
    ]


def get_crawl_data_path(crawl_name):
    for crawl_root_dir in CRAWL_ROOT_DIRS:
        crawl_dir_path = join(crawl_root_dir, crawl_name)
        if isdir(crawl_dir_path):
            return crawl_dir_path
    else:
        raise Exception("Cannot find the crawl data dir %s" % crawl_name)


def get_ps1_or_ipaddress(url):
    try:
        return get_fld(url, fail_silently=False)
    except Exception:
        hostname = urlparse(url).hostname
        try:
            ipaddress.ip_address(hostname)
            return hostname
        except Exception:
            return None


def read_extracted_fields(csv_path):
    """Read fields from txt files generated by tshark."""
    for l in open(csv_path):
        yield l.rstrip().split(TSHARK_FIELD_SEP)


def parse_roku_output_filename(filename):
    """Parse file names, which follows a specific pattern."""
    parts = filename.replace(".pcap.txt", "").split("-")
    channel_id, start_ts, command = parts[0:3]
    select_idx = parts[3] if command == "select" else 0
    return int(channel_id), int(start_ts), command, int(select_idx)


def read_pcap_fields_from_csvs(csv_dir, suffix=".csv"):
    for csv_path in glob(join(csv_dir, suffix)):
        filename = csv_path.split(sep)[-1]
        filename_wo_extension = filename.split(".")[0]
        # channel_id, start_ts, command, select_idx = parse_roku_output_filename(filename)
        channel_id, start_ts = filename_wo_extension.split("-")
        for pcap_fields in read_extracted_fields(csv_path):
            yield [channel_id, start_ts] + pcap_fields


# Download and parse Roku channel json - From Danny's notebook
CHANNEL_DATA_URL = 'https://iot-inspector.princeton.edu/pcaps/roku-channel-surfer/channel-list.txt'


def download_roku_channel_details(channel_data_url=CHANNEL_DATA_URL):
    channel_df = []
    for channel in urlopen(CHANNEL_DATA_URL).read().split('\n'):
        if channel:
            channel_df.append(json.loads(channel))
    return pd.DataFrame(channel_df).set_index('id').sort_values("rankByWatched")


def get_cat(categories):
    return categories[0]["name"]

def read_roku_channel_details_df():
    channel_df = []
    ROKU_CHANNEL_DETAILS = "../../../scrape/platforms/roku/channel_lists/channels_info/"
    for ch_json in glob(join(ROKU_CHANNEL_DETAILS, "*.json")):
        for channel_json_str in open(ch_json):
            channel_df.append(json.loads(channel_json_str))

    roku_df = pd.DataFrame(channel_df)
    roku_df['category'] = roku_df['categories'].map(lambda x: get_cat(x))
    roku_df.rename(columns={'channelId': 'channel_id',
                            'rankByWatched': 'rank',
                            '_category': 'category',
                            'name': 'channel_name'}, inplace=True)
    roku_df = roku_df[['channel_id', 'rank', 'category', 'channel_name']]
    # print("roku_df.columns", roku_df.columns)
    roku_df['channel_id'] = roku_df['channel_id'].astype(str)
    #roku_df = roku_df.drop_duplicates('channel_id').set_index('channel_id').sort_values(["category", "rank"])
    # print(roku_df.columns)
    # roku_df.drop(['accessCode', 'datePublished'], inplace=True, axis=1)
    roku_df['platform'] = 'roku'
    # print(roku_df.columns)
    return roku_df


def get_category(categories):
    """Remove metacategories if the channel has multiple ."""
    META_CATEGORIES = ['New & Notable', '4K UHD Content Available',
                       'Most Watched', 'Top Paid', 'Top Free',
                       'Featured', 'New']
    if len(categories) == 1:
        return categories[0]["name"]

    for cat in categories:
        if cat["name"] in META_CATEGORIES:
            continue
        # print(cat["name"])
        return cat["name"]
    else:
        # this means the channel has only meya-categories
        print("Channel doesn't have a real category")
        return categories[0]["name"]


def replace_nan(df, replacement=""):
    return df.replace(np.nan, replacement, regex=True)

AMAZON_CHANNEL_DETAILS_1K_CAT_CSV = "../../../scrape/platforms/amazon/channel_details/apk_info_top_with_ranking.csv"
AMAZON_CHANNEL_DETAILS_TOP_1K = "../../../scrape/platforms/amazon/channel_details/apk-info-top1K.csv"
AMAZON_CHANNEL_DETAILS_CAT_CSV = "../../../scrape/platforms/amazon/channel_details/apk_info_cat.csv"
AMAZON_CHANNEL_DETAILS_CSV = "../../../scrape/platforms/amazon/channel_details/apk_info.csv"
AMAZON_CHANNEL_DETAILS_100_RANDOM_CSV = "../../../scrape/platforms/amazon/channel_lists/test/100-channel_name.csv"


def read_channel_details_df():
    channel_df = []
    ROKU_CHANNEL_DETAILS = "../../../scrape/platforms/roku/channel_lists/channels_info/"

    for ch_json in glob(join(ROKU_CHANNEL_DETAILS, "*.json")):
        for channel_json_str in open(ch_json):
            d = dict()
            obj = json.loads(channel_json_str)
            # print(obj.keys())
            # d["category"] = obj['categories'][0]["name"]
            d["category"] = get_category(obj['categories'])

            d["rank"] = obj['rankByWatched']
            d["ad_supported"] = obj['isAdSupported']
            d["channel_id"] = obj['channelId']
            d["channel_name"] = obj['name']
            channel_df.append(d)

    ROKU_CATEGORY_DIR = "../../../scrape/platforms/roku/channel_lists/categories/"
    for category_txt in glob(join(ROKU_CATEGORY_DIR, "*.txt")):
        for channel_json_str in open(category_txt):
            d = dict()
            # print(obj.keys())
            obj = json.loads(channel_json_str)
            d["category"] = obj['_category']
            d["rank"] = obj['rankByWatched']
            d["ad_supported"] = "Unknown"
            d["channel_id"] = obj['id']
            d["channel_name"] = obj['name']
            channel_df.append(d)

    ROKU_OLD_CHANNEL_LIST = "../../../legacy-code/roku_readonly/channel_list_readonly.txt"
    ROKU_KIDS_AND_TV_CHANNELS = "../../../scrape/platforms/roku/channel_lists/all_channel_list.txt"
    # ROKU_TOP = "../../../scrape/platforms/roku/channel_lists/channels_info/all_channels.json"
    # roku_channels_df = read_roku_channel_details_df()
    # print(roku_channels_df.columns)
    # for channel_list_file in [ROKU_OLD_CHANNEL_LIST, ROKU_KIDS_AND_TV_CHANNELS]:
    for channel_list_file in [ROKU_OLD_CHANNEL_LIST, ROKU_KIDS_AND_TV_CHANNELS]:
        for channel_json_str in open(channel_list_file):
            d = dict()
            obj = json.loads(channel_json_str)
            # print(obj.keys())
            d["category"] = obj['_category']
            d["rank"] = obj['rankByWatched']
            d["ad_supported"] = "Unknown"
            d["channel_id"] = obj['id']
            d["channel_name"] = obj['name']
            channel_df.append(d)

    roku_df = pd.DataFrame(channel_df)
    # roku_df = roku_channels_df
    # print(roku_df.columns)
    roku_df['channel_id'] = roku_df['channel_id'].astype(str)
    # roku_df = pd.concat([roku_df, roku_channels_df], axis=0, sort=True)
    # print(roku_df.columns)
    roku_df = roku_df.drop_duplicates('channel_id', keep='first').\
        set_index('channel_id').sort_values(["category", "rank"])
    # print(roku_df.columns)
    # roku_df.drop(['_scrape_ts', 'accessCode', 'datePublished', 'desc', 'thumbnail'], inplace=True, axis=1)
    roku_df['platform'] = 'roku'

    amazon_df = pd.read_csv(AMAZON_CHANNEL_DETAILS_TOP_1K)
    # print(amazon_df.head())
    # amazon_df['amazon_category'] = amazon_df['amazon_categories'].map(lambda x: x.split('+')[0])
    # amazon_df['amazon_ranking'] = amazon_df['amazon_category_ranking'].map(lambda x: x.split(':')[1])

    amazon_df.rename(columns={'amazon_categories': 'amazon_category',
                              'amazon_category_ranking': 'amazon_ranking'}, inplace=True)
    amazon_df = amazon_df.append(pd.read_csv(AMAZON_CHANNEL_DETAILS_CAT_CSV), sort=True)
    amazon_df = amazon_df.append(pd.read_csv(AMAZON_CHANNEL_DETAILS_CSV), sort=True)

    tmp_df = pd.read_csv(AMAZON_CHANNEL_DETAILS_100_RANDOM_CSV, comment='#')
    # print(amazon_df.columns)
    # print(tmp_df.columns)
    # amazon_df = amazon_df.append(tmp_df.rename({"channel_name": "product_name"}, axis=1), sort=True)
    # print(amazon_df.columns)
    amazon_df = replace_nan(amazon_df)
    amazon_df['amazon_category'] = amazon_df['amazon_category'].map(lambda x: x.capitalize())
    amazon_df.rename(columns={'amazon_ranking': 'rank',
                              'amazon_category': 'category',
                              'apk_id': 'channel_id',
                              'product_name': 'channel_name'}, inplace=True)
    amazon_df['channel_id'] = amazon_df['channel_id'].astype(str)
    # print(amazon_df.columns)
    amazon_df = amazon_df.drop_duplicates('channel_id', keep='first').set_index('channel_id').sort_values(["category", "rank"])
    amazon_df.category[amazon_df.category == ""] = 'Others'
    amazon_df = amazon_df[['rank', 'category', 'channel_name']]
    # amazon_df.drop(['product_id', 'apk_name', 'apk_name_matches_product_name',
    #                'overlap_token_count', 'developer_name'], inplace=True, axis=1)
    amazon_df['platform'] = 'amazon'
    # print(amazon_df.columns)
    # print("amaz len", len(amazon_df))
    df = roku_df.append(amazon_df, sort=True)
    df = df.replace('kids-family', "Kids & Family").replace('movies-tvs', "Movies & TV").\
            replace('Web-Video', "Web Video").replace('education', "Education").\
            replace('food', "Food").replace('health', "Health").replace('kids', "Kids").\
            replace('lifestyle', "Lifestyle").replace('medical', "Medical").replace('movies', "Movies").\
            replace('news', "News").replace('shopping', "Shopping").replace('sports', "Sports"). \
            replace('Movies & tv', "Movies & TV")

    return df


def get_popular_domains_from_reqs(df, head=10):
    group_by=["req_domain"]
    subset=["channel_id", "req_domain"]
    return df.drop_duplicates(subset=subset).\
        groupby(group_by).size().reset_index(name="Num. of channels").\
        sort_values(by=['Num. of channels'], ascending=False).head(head)


def get_popular_domains_from_tcp_conns(df, head=10):
    group_by=["domain"]
    subset=["channel_id", "domain"]
    return df.drop_duplicates(subset=subset).\
        groupby(group_by).size().reset_index(name="Num. of channels").\
        sort_values(by=['Num. of channels'], ascending=False).head(head)

pre = r"""
\begin{table}[H]
%\centering
%\resizebox{\columnwidth}{!}{%
"""

post = r"""
%}
\caption{CAPTION}
\label{tab:LABEL}
\end{table}"""


def make_latex_table(df, label="LABEL", caption="caption",
                     tablefmt="latex_booktabs"):
    df = df.rename(lambda x: x.replace("_", " ").capitalize(), axis='columns')
    tabu = tabulate(df, tablefmt=tablefmt, headers="keys", showindex=False)

    return pre + tabu + post.replace(
        "LABEL", label).replace("CAPTION", caption)


def display_side_by_side(*args):
    html_str = ''
    for df in args:
        html_str += df.to_html(index=False)
    display_html(html_str.replace(
        'table', 'table style="display:inline"'), raw=True)


def score_first_party(fp, rank_weight=1):
    """ Weight of 1/(rank of first_party) """
    return 1.0/float(fp)**rank_weight


def get_prominence_score(channel_ranks):
    return round(sum([score_first_party(channel_rank)
                      for channel_rank in channel_ranks]), 4)


def get_channels_with_most_domains(df, head=10, only_tracking_domains=True):
    title = "# domains"
    if only_tracking_domains:
        df = df[df.adblocked]
        title = "# tracking\n domains"
    return df.drop_duplicates(subset=["channel_name", "domain"]).\
        groupby(["channel_name", "rank", 'category']).size().\
        reset_index(name=title).\
        sort_values(by=[title], ascending=False).head(head)


if __name__ == '__main__':
    df = read_channel_details_df()
    # df = read_roku_channel_details_df()
    # amazon_df = df[(df.platform=="amazon")]
    # print(len(amazon_df))
    # top1k = amazon_df
    # print(top1k.category.value_counts())

