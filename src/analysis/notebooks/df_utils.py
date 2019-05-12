from log_analysis import get_http_df, get_crawl_data_path, get_distinct_tcp_conns
from os.path import join
import os
import pandas as pd

DF_PICKLE_PATH = "df_pickle"


def save_pickle(df, crawl_name, df_type):
    os.makedirs(DF_PICKLE_PATH, exist_ok=True)
    path = join(DF_PICKLE_PATH, "%s_%s.pickle" % (crawl_name, df_type))
    df.to_pickle(path)

    
def load_df(crawl_name, df_type):
    path = join(DF_PICKLE_PATH, "%s_%s.pickle" % (crawl_name, df_type))
    return pd.read_pickle(path)


def load_and_save_dfs(crawl_name):
    crawl_data_dir = get_crawl_data_path(crawl_name)
    http_req, http_resp, dns = get_http_df(crawl_data_dir)
    save_pickle(http_req, crawl_name, "http_req")
    save_pickle(http_resp, crawl_name, "http_resp")
    save_pickle(dns, crawl_name, "dns")
    tcp_conn = get_distinct_tcp_conns(crawl_name, http_requests=http_req)
    save_pickle(tcp_conn, crawl_name, "tcp_conn")   


def print_stats(crawl_name, crawl_title=""):
    tcp = load_df(crawl_name, "tcp_conn")
    len(tcp[tcp.host==""])
    tcp = tcp[tcp.host!=""]
    print("\nStats for", crawl_title, crawl_name)
    print("=====================")
    n_playback = len(get_playback_detection_results(crawl_name))
    n_channels = tcp.channel_id.nunique()
    print("Num of playback detected channels %s of %s" % (n_playback, n_channels))
    print("Distinct domains", tcp.domain.nunique())
    print("Number of connections", len(tcp))
    print("Number of dictinct blocked domains", len(tcp[tcp.disconnect_blocked].drop_duplicates("domain")))
    return tcp

