"""
Simulates the installation of Amazon Fire TV apps using Selenium.

When running this script, also run pull_apks.py to simultaneously pull the APKs
to local disk in the order in which the respective channels are installed.

"""

from selenium import webdriver
import time
import datetime
import os
import random

LABEL = 'cat'

ASIN_PATH = 'fire_stick_app_asins.txt'

FIREFOX_PROFILE_PATH = '/path/to/firefox/profile' # noqa

BUY_BUTTON_PATH = "//input[@class='a-button-input' and @value='buy.mas']"

SUCCESS_PATH = "//span[@id='install-text']"

LOG_PATH = 'install_from_app_store.log'

PAGE_SOURCE_PATH = 'install_from_app_store.page_source.txt'

if LABEL:
    ASIN_PATH = 'fire_stick_app_asins_LABEL.txt'.replace('LABEL', LABEL)
    LOG_PATH = 'install_from_app_store_LABEL.log'.replace('LABEL', LABEL)
    PAGE_SOURCE_PATH = 'install_from_app_store_LABEL.page_source.txt'.replace('LABEL', LABEL) # noqa


def main():

    fp = webdriver.FirefoxProfile(FIREFOX_PROFILE_PATH)
    driver = webdriver.Firefox(fp)

    # Get ASINs that were previously installed
    previously_installed_asins = set()
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH) as fp:
            for line in fp:
                line = line.strip()
                try:
                    success = line.split()[6] == 'successful'
                    asin = line.split()[5]
                except Exception:
                    continue
                if success:
                    previously_installed_asins.add(asin)

    # Find all cat/asin pairs
    cat_asin_dict = {}
    with open(ASIN_PATH) as fp:
        for line in fp:
            cat, asin = line.strip().split()
            asin = asin.strip()
            if asin and asin not in previously_installed_asins:
                cat_asin_dict.setdefault(cat, []).append(asin)

    # Install each asin, breadth-first
    while True:
        install_count = 0
        for (cat, asin_list) in cat_asin_dict.iteritems():
            if asin_list:
                asin = asin_list.pop(0)
                status = browse_page(driver, asin)
                log_status(asin, status)
                install_count += 1
        if install_count == 0:
            break

    driver.quit()


def browse_page(driver, asin):

    time.sleep(random.randint(1, 5))

    driver.get('https://www.amazon.com/dp/{}'.format(asin))

    buy_button = find_element(driver, BUY_BUTTON_PATH)

    if buy_button is None:
        return False

    html_source = driver.page_source

    time.sleep(random.randint(1, 5))
    try:
        buy_button.click()
    except Exception:
        return False

    if find_element(driver, SUCCESS_PATH) is None:
        return False

    with open(PAGE_SOURCE_PATH, 'a') as fp:
        print >> fp, repr({
            'asin': asin,
            'timestamp': int(time.time()),
            'html_source': html_source
        })

    return True


def find_element(driver, xpath, timeout=20):

    for _ in range(timeout):
        time.sleep(1)
        for element in driver.find_elements_by_xpath(xpath):
            return element

    return None


def log_status(asin, success):

    success_str = 'successful' if success else 'failed'

    with open(LOG_PATH, 'a') as fp:
        print >> fp, datetime.datetime.today(), '@', int(time.time()),
        print >> fp, '-', asin, success_str

    print asin, success_str


if __name__ == '__main__':
    main()
