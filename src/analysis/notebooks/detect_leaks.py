import sys
from df_utils import load_and_save_dfs, load_df, save_pickle
from crawl_ids import ROKU_CRAWLS, FIRE_TV_CRAWLS, CrawlRokuTop1KNoMITM
from log_analysis import get_crawl_data_path, get_http_df
from os.path import basename
from ott_leaks import run_leak_detection, DEVICE_ID_NAMES, detect_openwpm_leaks
import traceback


def detect_leaks(crawl_list):
    for crawl_name in crawl_list:
        if not crawl_name:
            continue
        print("Will leak detect and pickle %s" % crawl_name)
        try:
            req_df = load_df(crawl_name, "http_req")
            openwpm_leaks_df, id_dict = detect_openwpm_leaks(crawl_name)
            leaks_df, id_dict = run_leak_detection(crawl_name, req_df)
            save_pickle(leaks_df, crawl_name, "leak")
            save_pickle(openwpm_leaks_df, crawl_name, "openwpm_leak")
        except Exception as e:
            print("ERR while detecting leaks", e)
            traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 2:  # no arg means process all crawls
        detect_leaks(ROKU_CRAWLS + FIRE_TV_CRAWLS)
    else:  # process a single crawl
        print(len(sys.argv))
        crawl_name = basename(sys.argv[1].rstrip('/'))
        detect_leaks((crawl_name, ))

