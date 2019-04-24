"""
Obtains a list of ASINs (Amazon Standard Identification Number) for "Movies and
TV" apps that are compatible on Fire Stick. Saves the list as
fire_stick_app_asins.txt.

The ASINs follow the ranking of the corresponding apps as appeared in Amazon's
app store.

"""
import re
import subprocess


KIDS = False


# We start scraping using this template URL.
CURL_CMD = r"""curl 'https://www.amazon.com/s/ref=sr_pg_2?fst=as%3Aoff&rh=n%3A2350149011%2Cn%3A%219209898011%2Cn%3A9408765011%2Cp_n_feature_nineteen_browse-bin%3A14067184011&page=PAGE_ID&bbn=9408765011&ie=UTF8&qid=1546640019' -H 'authority: www.amazon.com' -H 'upgrade-insecure-requests: 1' -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36' -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8' -H 'accept-encoding: gzip, deflate, br' -H 'accept-language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7' --compressed""" # noqa

if KIDS:
    CURL_CMD = r"""curl 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408582011&lo=grid&dc&page=PAGE_ID&fst=as%3Aoff&qid=1555943617&rnid=9209898011&ref=sr_pg_1' -H 'authority: www.amazon.com' -H 'upgrade-insecure-requests: 1' -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36' -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3' -H 'accept-encoding: gzip, deflate, br' -H 'accept-language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7' --compressed""" # noqa


# Regex used to extract ASINs
ASIN_REGEX = re.compile(r'data\-asin\=\"([0-9A-Z]+)\"')


def main():

    asin_list = []

    for page_id in range(1, 16):

        print 'Scraping page', page_id

        data = subprocess.Popen(
            CURL_CMD.replace('PAGE_ID', str(page_id)),
            stdout=subprocess.PIPE, shell=True
        ).communicate()[0]

        for line in data.split('\n'):
            match = ASIN_REGEX.search(line)
            if match:
                asin = match.group(1)
                if asin not in asin_list:
                    asin_list.append(asin)

    out_file = 'fire_stick_app_asins.txt'
    if KIDS:
        out_file = 'fire_stick_app_asins_kids.txt'

    with open(out_file, 'w') as fp:
        print >>fp, '\n'.join(asin_list)


if __name__ == '__main__':
    main()
