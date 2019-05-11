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
