import sys
from selenium import webdriver
from nb_utils import AMAZON_CHANNEL_DETAILS_1K_CAT_CSV
import pandas as pd
from time import sleep
import traceback
from selenium.common.exceptions import NoSuchElementException


# driver = webdriver.Firefox()
# driver.get("http://www.python.org")
# assert "Python" in driver.title
# elem = driver.find_element_by_name("q")
# elem.clear()
# elem.send_keys("pycon")
# elem.send_keys(Keys.RETURN)
# assert "No results found." not in driver.page_source
# driver.close()


def get_cat_for_asin(driver, asin):
    url = "https://www.amazon.com/dp/asin/%s" % asin
    driver.get(url)
    print("Will crawl for %s %s" % (asin, url))
    try:
        el = driver.find_element_by_xpath('//*[@id="wayfinding-breadcrumbs_feature_div"]/ul/li[3]/span/a')
    except NoSuchElementException:
        el = driver.find_element_by_xpath('/html/body/div[2]/div[2]/div[4]/div/div/ul/li[3]/span/a')

    if el and el.text:
        # print(el.text)
        return(el.text)
    print("Can't find the category for %s %s" % (asin, url))
    return "Unknown"


def save_csv(df, cat_dict, rank_dict, out_csv):
    df['amazon_categories'] = df['product_id'].map(
        lambda x: cat_dict.get(x, "Unknown"))
    df.to_csv(out_csv, index=False)


def crawl(driver):
    cat_dict = dict()
    rank_dict = dict()
    df = pd.read_csv(AMAZON_CHANNEL_DETAILS_1K_CAT_CSV)
    out_csv = AMAZON_CHANNEL_DETAILS_1K_CAT_CSV.replace(".csv", "_v2.csv")
    df['amazon_category_ranking'] = df['amazon_category_ranking'].map(lambda x: 1 + int(x.split(":")[-1]))
    df = df[df.amazon_category_ranking >= 1000]
    processed_cnt = 0
    for _, row in df.iterrows():
        processed_cnt += 1
        if not processed_cnt % 50:
            save_csv(df, cat_dict, rank_dict, out_csv)
            print("Written", processed_cnt)
            sleep(5)
        else:
            sleep(0.2)
        asin = row['product_id']
        try:
            cat = get_cat_for_asin(driver, asin)
        except Exception as e:
            print(asin, e, traceback.format_exc())
            cat_dict[asin] = "Others"
            sleep(1)
            continue
        print (processed_cnt, asin, cat)
        cat_dict[asin] = cat

    save_csv(df, cat_dict, rank_dict, out_csv)
    print(cat_dict)
    print("Finished crawling")


def correct_ranks():
    out_csv = "../../../scrape/platforms/amazon/channel_details/apk_info_top_with_ranking_v2"
    df = pd.read_csv(out_csv)
    df['amazon_category_ranking'] = df['amazon_category_ranking'].map(
        lambda x: int(x.split(":")[-1]) + 1)
    print(df['amazon_category_ranking'].min())
    print(df['amazon_category_ranking'].max())
    df[df['amazon_category_ranking'] <= 1000].sort_values(
        'amazon_category_ranking').to_csv(
        out_csv.replace(".csv", "_v2.csv"), index=False)
    sys.exit(0)


if __name__ == '__main__':
    # correct_ranks()
    try:
        driver = webdriver.Firefox()
        crawl(driver)
    except Exception as e:
        print(e, traceback.format_exc())
    finally:
        driver.quit()
