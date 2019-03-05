from curtsies import Input
from scrape_channels import scraper

def get_key():
    with Input(keynames='curses') as ch_input:
        for key in ch_input:
            # print(repr(key))
            return key

def setup_channel():
    pass

def scrape_channel():
    pass

if __name__ == '__main__':
    scrape_channel()
