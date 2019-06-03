import sys
from df_utils import load_and_save_dfs
from crawl_ids import ROKU_CRAWLS, FIRE_TV_CRAWLS
from os.path import basename


def pickle_post_processed_data(crawl_list):
    for crawl_name in crawl_list:
        if not crawl_name:
            continue
        print("Will process and pickle %s" % crawl_name)
        try:
            load_and_save_dfs(crawl_name)
        except Exception as e:
            print("ERR", e)


if __name__ == '__main__':
    if len(sys.argv) < 2:  # no arg means process all crawls
        pickle_post_processed_data(ROKU_CRAWLS + FIRE_TV_CRAWLS)
    else:  # process a single crawl
        print(len(sys.argv))
        crawl_name = basename(sys.argv[1])
        pickle_post_processed_data((crawl_name, ))
