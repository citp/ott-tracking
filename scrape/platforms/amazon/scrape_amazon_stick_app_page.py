"""
Obtains a list of ASINs (Amazon Standard Identification Number) for "Movies and
TV" apps that are compatible on Fire Stick. Saves the list as
fire_stick_app_asins.txt.

The ASINs follow the ranking of the corresponding apps as appeared in Amazon's
app store.

"""
import re
import subprocess


LABEL = 'cat'


# We start scraping using this template URL.
CURL_CMDS = [('movies', r"""curl 'https://www.amazon.com/s/ref=sr_pg_2?fst=as%3Aoff&rh=n%3A2350149011%2Cn%3A%219209898011%2Cn%3A9408765011%2Cp_n_feature_nineteen_browse-bin%3A14067184011&page=PAGE_ID&bbn=9408765011&ie=UTF8&qid=1546640019' -H 'authority: www.amazon.com' -H 'upgrade-insecure-requests: 1' -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36' -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8' -H 'accept-encoding: gzip, deflate, br' -H 'accept-language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7' --compressed""")] # noqa


if LABEL:
    URLS = [
        ('news', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408802011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556651124&rnid=9209898011&ref=sr_pg_2'), # noqa - news
        ('movies', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408765011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556652077&rnid=9209898011&ref=sr_pg_2'), # noqa - moves
        ('sports', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408876011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556651182&rnid=9209898011&ref=sr_pg_2'), # noqa - sports
        ('lifestyle', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408710011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556651213&rnid=9209898011&ref=sr_pg_2'), # noqa - lifestyle
        ('health', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408710011%2Cn%3A9408749011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556651275&rnid=9408710011&ref=sr_pg_2'), # noqa -  health
        ('food', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408523011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556651309&rnid=9209898011&ref=sr_pg_2'), # noqa - food
        ('kids', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408582011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556651341&rnid=9209898011&ref=sr_pg_2'), # noqa - kids
        ('shopping', 'https://www.amazon.com/s?bbn=10208590011&rh=n%3A2350149011%2Cn%3A%212445993011%2Cn%3A10208590011%2Cn%3A9408875011&dc&fst=as%3Aoff&qid=1556651178&rnid=9209898011&ref=lp_10208590011_nr_n_21'), # noqa - shopping
        ('education', 'https://www.amazon.com/s?i=mobile-apps&bbn=10208590011&rh=n%3A2350149011%2Cn%3A2445993011%2Cn%3A10208590011%2Cn%3A9408490011&dc&page=PAGE_ID&fst=as%3Aoff&qid=1556651390&rnid=9209898011&ref=sr_pg_2'), # noqa - education
        ('medical', 'https://www.amazon.com/s?bbn=10208590011&rh=n%3A2350149011%2Cn%3A%212445993011%2Cn%3A10208590011%2Cn%3A10298306011&dc&fst=as%3Aoff&qid=1556651178&rnid=9209898011&ref=lp_10208590011_nr_n_13') # noqa - medical
    ]

    CURL_CMDS = [
        (cat, r"""curl 'URL' -H 'upgrade-insecure-requests: 1' -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36' -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3' -H 'accept-encoding: gzip, deflate, br' -H 'accept-language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7' --compressed""".replace('URL', url)) # noqa
        for (cat, url) in URLS
    ] # noqa


# Regex used to extract ASINs
ASIN_REGEX = re.compile(r'data\-asin\=\"([0-9A-Z]+)\" data-index')


def main():

    asin_list = []

    for (cat, curl_cmd) in CURL_CMDS:

        counter = 70
        page_id = 0

        while counter > 0:

            page_id += 1

            print 'Scraping', cat, 'page', page_id

            data = subprocess.Popen(
                curl_cmd.replace('PAGE_ID', str(page_id)),
                stdout=subprocess.PIPE, shell=True
            ).communicate()[0]

            for line in data.split('\n'):
                match = ASIN_REGEX.search(line)
                if match:
                    asin = match.group(1)
                    if asin not in asin_list:
                        if counter >= 1:
                            asin_list.append(cat + ' ' + asin)
                            counter -= 1

    out_file = 'fire_stick_app_asins.txt'
    if LABEL:
        out_file = 'fire_stick_app_asins_{}.txt'.format(LABEL)

    with open(out_file, 'w') as fp:
        print >>fp, '\n'.join(asin_list)


if __name__ == '__main__':
    main()
