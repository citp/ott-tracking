"""
Downloads the info from all Roku channels.

Saves output to channel_list.txt, where every line is a json of a channel.

"""
import urllib2
import json
import time


# TODO: Expand this list.
CHANNEL_URLS = {
    'movies-tvs': 'https://channelstore.roku.com/api/v5/channels?country=US&language=en&category=22cdb2edaf5e4c7a8ccf6e18cce49df2&pagestart={}&pagesize=24', # noqa
    'kids-family': 'https://channelstore.roku.com/api/v5/channels?country=US&language=en&category=040d64b80a8946e2a5bd9f8200e87515&pagestart={}&pagesize=24' # noqa
}


def main():

    fp = open('channel_list.txt', 'w')

    for (category, page_url) in CHANNEL_URLS.iteritems():

        page_number = 0

        while True:

            url = page_url.format(page_number)
            print 'Loading', url
            data = urllib2.urlopen(url).read()

            channel_list = json.loads(data)
            if not channel_list:
                break

            for channel in channel_list:
                channel['_category'] = category
                channel['_scrape_ts'] = int(time.time())
                print >> fp, json.dumps(channel, sort_keys=True)

            page_number += 1

    fp.close()


if __name__ == '__main__':
    main()
