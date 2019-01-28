"""
Simulates the installation of Amazon Fire TV apps using Selenium.

"""

from selenium import webdriver
import time
import datetime
import os
import random


ASIN_PATH = 'fire_stick_app_asins.txt'

FIREFOX_PROFILE_PATH = '/home/danny/.mozilla/firefox/rq3qfpez.default'

BUY_BUTTON_PATH = "//input[@class='a-button-input' and @value='buy.mas']"

SUCCESS_PATH = "//span[@id='install-text']"

LOG_PATH = 'install_from_app_store.log'


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
                    success = line.split()[3] == 'successful'
                    asin = line.split()[2]
                except Exception:
                    continue
                if success:
                    previously_installed_asins.add(asin)

    # Install each ASIN
    with open(ASIN_PATH) as fp:
        for asin in fp:
            asin = asin.strip()
            if asin and asin not in previously_installed_asins:
                status = browse_page(driver, asin)
                log_status(asin, status)

    driver.quit()


def browse_page(driver, asin):

    time.sleep(random.randint(2, 10))

    driver.get('https://www.amazon.com/dp/{}'.format(asin))

    buy_button = find_element(driver, BUY_BUTTON_PATH)

    if buy_button is None:
        return False

    time.sleep(random.randint(2, 10))
    buy_button.click()

    if find_element(driver, SUCCESS_PATH) is None:
        return False

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
        print >> fp, datetime.datetime.today(), asin, success_str

    print asin, success_str


if __name__ == '__main__':
    main()
