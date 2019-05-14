import os
import pickle
import pandas as pd
from os.path import join, isdir

from log_analysis import (get_http_df, get_distinct_tcp_conns,
                          get_playback_detection_results)


DF_PICKLE_PATH = "df_pickle"


def save_pickle(df, crawl_name, df_type):
    if not len(df):
        print("Empty dataframe", crawl_name, df_type)
        return
    if not isdir(DF_PICKLE_PATH):
        os.makedirs(DF_PICKLE_PATH)
    path = join(DF_PICKLE_PATH, "%s_%s.pickle" % (crawl_name, df_type))
    pickle.dump(df, open(path, 'wb'), protocol=2)
    print("Saved pickle", crawl_name, df_type, path)


def correct_firetv_ranks(firetv_df):
    firetv_df['rank'] = firetv_df['rank'].map(int)
    if firetv_df['rank'].min() == 0:
        firetv_df['rank'] = firetv_df['rank'] + 1


def load_df(crawl_name, df_type):
    path = join(DF_PICKLE_PATH, "%s_%s.pickle" % (crawl_name, df_type))
    df = pd.read_pickle(path)
    if "amazon" in crawl_name:
        correct_firetv_ranks(df)
    return df


def load_and_save_dfs(crawl_name):
    http_req, http_resp, dns = get_http_df(crawl_name)
    save_pickle(http_req, crawl_name, "http_req")
    save_pickle(http_resp, crawl_name, "http_resp")
    save_pickle(dns, crawl_name, "dns")
    tcp_conn = get_distinct_tcp_conns(crawl_name, http_requests=http_req)
    save_pickle(tcp_conn, crawl_name, "tcp_conn")


def print_stats(crawl_name, crawl_title=""):
    tcp = load_df(crawl_name, "tcp_conn")
    len(tcp[tcp.host == ""])
    tcp = tcp[tcp.host != ""]
    print("\nStats for", crawl_title, crawl_name)
    print("=====================")
    n_playback = len(get_playback_detection_results(crawl_name))
    n_channels = tcp.channel_id.nunique()
    print("Num of playback detected channels %s of %s" % (
        n_playback, n_channels))
    print("Distinct domains", tcp.domain.nunique())
    print("Number of connections", len(tcp))
    print("Number of dictinct blocked domains",
          len(tcp[tcp.disconnect_blocked].drop_duplicates("domain")))
    return tcp
