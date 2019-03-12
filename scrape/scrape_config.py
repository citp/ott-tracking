import os
'''
Crawl settings
'''

ENABLE_SMART_CRAWLER = False  # remove after testing
MITMPROXY_ENABLED = int(os.environ['MITMPROXY_ENABLED'])
remove_dup = False
RSYNC_EN = False
REC_AUD = True
SSL_STRIP = False


MITMABLE_DOMAINS_WARM_UP_CRAWL = int(os.environ['MITMABLE_DOMAINS_WARM_UP_CRAWL'])

if MITMABLE_DOMAINS_WARM_UP_CRAWL and MITMPROXY_ENABLED:
    LAUNCH_RETRY_CNT = 5  # detect and store unmitmable domains and IPs
else:
    LAUNCH_RETRY_CNT = 1  # load unmitmable domains and IPs from files

TV_IP_ADDR = os.environ['TV_IP_ADDR']
SLEEP_TIMER = 20
DATA_DIR = os.getenv("DATA_DIR")
PCAP_PREFIX = "pcaps/"
DUMP_PREFIX = "mitmdumps/"
LOG_PREFIX = "mitmlog/"
LOG_FOLDER = "logs/"
LOG_FILE = 'scrape_channels.log'
LOG_DIR = os.getenv("LogDir")
LOG_FILE_PATH_NAME = os.getenv("LOG_OUT_FILE")
SCREENSHOT_PREFIX = "screenshots/"
AUDIO_PREFIX="audio/"
SSLKEY_PREFIX = "keys/"
DB_PREFIX = "db/"
#Each channel will have a file with the result of crawl of that channel in this folder
FIN_CHL_PREFIX = "finished/"
folders = [PCAP_PREFIX, DUMP_PREFIX, LOG_PREFIX, SCREENSHOT_PREFIX, SSLKEY_PREFIX, LOG_FOLDER, AUDIO_PREFIX, FIN_CHL_PREFIX, DB_PREFIX]


RSYNC_DIR = ' hoomanm@portal.cs.princeton.edu:/n/fs/iot-house/hooman/crawl-data/'


CUTOFF_TRESHOLD=100000
SCRAPE_TO = 900

PLAT = os.getenv("PLATFORM")

print("Environment:")
l = list( locals().items())
for k in l:
    if "__" in k[0] or "module" in str(k[1]):
        continue
    print(k)
