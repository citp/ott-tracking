import os
'''
Crawl settings
'''

ENABLE_SMART_CRAWLER = True  # remove after testing
MITMABLE_DOMAINS_WARM_UP_CRAWL = True
remove_dup = False
RSYNC_EN = False
REC_AUD = True
TLS_INTERCEPT = True
SSL_STRIP = False
THREADED_SCRAPE = False
AMAZON_HDMI_SCREENSHOT = False
DEDUPLICATE_SCREENSHOTS = True

MITMPROXY_ENABLED = SSL_STRIP or TLS_INTERCEPT

if MITMABLE_DOMAINS_WARM_UP_CRAWL and MITMPROXY_ENABLED:
    LAUNCH_RETRY_CNT = 15  # detect and store unmitmable domains and IPs
    SMART_CRAWLS_CNT = 15  # run multiple smart crawls to discover the best number for the warmup
else:
    LAUNCH_RETRY_CNT = 2  # load unmitmable domains and IPs from files
    SMART_CRAWLS_CNT = 1

TV_IP_ADDR = os.environ['TV_IP_ADDR']
SLEEP_TIMER = 20
FWD_SLEEP_TO = 3 # Used in Smart Crawl to stop Fast Forwarding after few seconds
DATA_DIR = os.path.abspath(os.getenv("DATA_DIR"))
PLAT = os.getenv("PLATFORM")
PLATFORM_DIR = os.path.abspath(os.getenv("PLATFORM_DIR"))
PCAP_PREFIX = "pcaps/"
DUMP_PREFIX = "mitmdumps/"
MITM_LOG_PREFIX = "mitmlog/"
LOG_PREFIX = "logs/"
LOG_FILE = 'scrape_channels.log'
LOCAL_LOG_DIR = os.path.abspath(os.getenv("LogDir"))
LOG_FILE_PATH_NAME = os.getenv("LOG_OUT_FILE")
SCREENSHOT_PREFIX = "screenshots/"
AUDIO_PREFIX="audio/"
SSLKEY_PREFIX = "keys/"
DB_PREFIX = "db/"
#Each channel will have a file with the result of crawl of that channel in this folder
FIN_CHL_PREFIX = "finished/"
folders = [PCAP_PREFIX, DUMP_PREFIX, MITM_LOG_PREFIX, SCREENSHOT_PREFIX, SSLKEY_PREFIX,
           LOG_PREFIX, AUDIO_PREFIX, FIN_CHL_PREFIX, DB_PREFIX]


RSYNC_DIR = ' hoomanm@portal.cs.princeton.edu:/n/fs/iot-house/hooman/crawl-data/'


CUTOFF_TRESHOLD=100000

if MITMABLE_DOMAINS_WARM_UP_CRAWL:
    SCRAPE_TO = 1800  # timeout
else:
    SCRAPE_TO = 900

PLAT = os.getenv("PLATFORM")

print("Environment:")
l = list( locals().items())
for k in l:
    if "__" in k[0] or "module" in str(k[1]):
        continue
    print(k)
