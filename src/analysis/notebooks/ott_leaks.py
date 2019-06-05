import pandas as pd
import unicodedata
import LeakDetector
from nb_utils import get_crawl_data_path
from device_ids import TV_ID_MAP
from log_analysis import get_ott_device_mac
from os.path import join
from df_utils import load_df
from collections import defaultdict
from nltk.corpus import words


try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

CHECK_REFERRER_LEAKS = True

# we treat the following as ID leaks
DEVICE_ID_NAMES = ['AD ID', 'Serial No', 'MAC', 'Device name', 'Wifi SSID', 'Device ID']


def reverse_dict(d):
    new_d = dict()
    for k, v in d.items():
        new_d[v.lower()] = k
    return new_d


def check_row_for_leaks(detector, req):
    url, cookie_str, post_body, referrer_str = req['url'], \
        req.get('cookie', ''), req.get('post_data', ''), req.get('referer', '')
    url_leaks = detector.check_url(url)
    url_leaks += detector.substring_search(url, max_layers=2)
    cookie_leaks = detector.substring_search(cookie_str, max_layers=2)
    post_leaks = detector.substring_search(post_body, max_layers=2)
    if CHECK_REFERRER_LEAKS:
        referrer_leaks = detector.substring_search(referrer_str, max_layers=2)
        return url_leaks, cookie_leaks, post_leaks, referrer_leaks
    else:
        return url_leaks, cookie_leaks, post_leaks


def convert_leaks_to_df(device_ids, leaks_dict):
    r_ids = reverse_dict(device_ids)
    leaks_dicts = []
    for leak_type, leaks in leaks_dict.items():
        for leak in leaks:
            # print(leak, len(leak), leak[0])
            # assert len(leak) <= 2
            if len(leak) == 2:
                encoding, search = leak
            elif len(leak) == 1:
                search = leak[0]
                encoding = "unencoded"
            else:
                search = leak[-1]
                encoding = "-".join(leak[:-1])
                print("Leak can't be parsed", len(leak), leak)
            id_type = r_ids.get(search.lower(), "Unknown")
            leaks_dicts.append({'id_type': id_type, 'search': search,
                                "encoding": encoding, "leak_type": leak_type,
                                "id_leak": id_type in DEVICE_ID_NAMES})
    return pd.DataFrame(leaks_dicts)


def detect_leaks_in_requests(df, device_ids, title_dict=None):
    df.sort_values("channel_name", inplace=True)
    last_channel = ""
    leak_df = pd.DataFrame({})
    for _, req in df.iterrows():
        channel_name = unicodedata.normalize('NFKD', req['channel_name']).encode('ascii','ignore')
        if channel_name != last_channel:
            last_channel = channel_name
            DISABLE_CHANNEL_NAME_SEARCH = False
            if not DISABLE_CHANNEL_NAME_SEARCH:
                device_ids["Channel name"] = channel_name

            ch_id = req['channel_id']
            if title_dict is not None and len(title_dict[ch_id]):
                for title in title_dict[ch_id]:
                    if title.lower() in words.words():  # in dictionary
                        continue
                    # print(title, "NOT IN WORDS")
                    device_ids["imdb_title_%s" % title] = title
                # print(device_ids)

            if not len(device_ids):
                continue

            leak_detector = LeakDetector.LeakDetector(
                device_ids.values(), encoding_set=LeakDetector.ENCODINGS_NO_ROT,
                encoding_layers=2, hash_layers=2, debugging=False
            )
        if not len(device_ids):
            continue
        url_leaks, cookie_leaks, post_leaks, referrer_leaks = \
            check_row_for_leaks(leak_detector, req)

        tmp_df = convert_leaks_to_df(
            device_ids, {
                "url_leaks": url_leaks, "cookie_leaks": cookie_leaks,
                "post_leaks": post_leaks, "referrer_leaks": referrer_leaks})
        if title_dict is not None and len(tmp_df):
            if url_leaks:
                print(ch_id, "url_leaks", url_leaks)
            if cookie_leaks:
                print(ch_id, "cookie_leaks", cookie_leaks)
            if post_leaks:
                print(ch_id, "post_leaks", post_leaks)
            if referrer_leaks:
                print(ch_id, "referrer_leaks", referrer_leaks)

        tmp_df['channel_name'] = channel_name
        for col in df.columns:  # copy data from requests to leaks df
            if col != 'channel_name':   # already added, skip
                tmp_df[col] = req[col]
        leak_df = leak_df.append(tmp_df, sort=True)

    device_ids["Channel name"] = ""  # reset back
    return leak_df


def print_leak_stats(leak_df, _print=False):
    leaks = []
    for id_type in list(leak_df.id_type.unique()):
        df = leak_df[leak_df.id_type == id_type]
        num_leaks = len(df)
        num_channels = df.channel_id.nunique()
        if num_leaks:
            if _print:
                print ("%d channels leaked %s" % (num_leaks, id_type))
            leaks.append((id_type, num_leaks, num_channels))
    return pd.DataFrame.from_records(leaks, columns=["ID", "Num. of leaks", "Num. of channels"])


def is_ch_name_url_false_positive(row):
    if row['id_type'] != 'Channel name':
        return False
    channel_name = row['channel_name'].lower()
    if channel_name in urlparse(row['url']).hostname:
        return True
    return False


def remove_ch_name_url_false_positives(df):
    """If AccuRadio is talking to accuradio.com/xyz we shouldn't flag this as a leak."""
    df["ch_name_url_false_pos"] = df.apply(is_ch_name_url_false_positive, axis=1)
    df = df[~df.ch_name_url_false_pos]


def search_for_video_titles(crawl_name):
    crawl_data_dir = get_crawl_data_path(crawl_name)
    title_list = join(crawl_data_dir, "post-process/global_imdb_titles.json")
    title_dict = defaultdict(set)
    req_df = load_df(crawl_name, "http_req")
    for l in open(title_list):
        channel_id, ts, title = l.rstrip().split("\t")
        title_dict[channel_id].add(title)

    run_leak_detection(crawl_name, req_df, title_dict, device_ids={})


DEBUG = False


def run_leak_detection(crawl_name, req_df, title_dict=None, device_ids=None):
    if DEBUG:  # to quickly test changes
        req_df = req_df.head(1000)

    crawl_data_dir = get_crawl_data_path(crawl_name)
    if DEBUG:
        print("%d reqs from %d channels" % (
            len(req_df), req_df.channel_id.nunique()))

    if device_ids is None:
        device_ids = TV_ID_MAP[get_ott_device_mac(crawl_data_dir)]
    print("Will search for the following IDs", device_ids)
    leak_df = detect_leaks_in_requests(req_df, device_ids, title_dict)

    # remove channel names as part of the hostname
    # e.g. accuradio channel talking to accuradio.com
    remove_ch_name_url_false_positives(leak_df)

    if DEBUG:
        for id_type in device_ids.keys():
            num_leaks = leak_df[leak_df.id_type == id_type].channel_id.nunique()
            if num_leaks:
                print ("%d channels leaked %s" % (num_leaks, id_type))

    return leak_df, device_ids


if __name__ == '__main__':
    from crawl_ids import CrawlRokuTop1KNoMITM
    search_for_video_titles(CrawlRokuTop1KNoMITM)
