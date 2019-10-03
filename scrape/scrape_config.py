import os
from requests import get

'''
Crawl settings
'''

ENABLE_SMART_CRAWLER = True  # remove after testing
MITMABLE_DOMAINS_WARM_UP_CRAWL = True
REC_AUD = True
TLS_INTERCEPT = True
SSL_STRIP = False
AMAZON_HDMI_SCREENSHOT = True
DEDUPLICATE_SCREENSHOTS = True
MITM_STOP_NO_NEW_ENDPOINT = True
SEND_EMAIL_AFTER_CRAWL = False
MOVE_TO_NFS = False

MITMPROXY_ENABLED = SSL_STRIP or TLS_INTERCEPT

if not TLS_INTERCEPT:
    MITM_STOP_NO_NEW_ENDPOINT = False

if MITMABLE_DOMAINS_WARM_UP_CRAWL and TLS_INTERCEPT:
    LAUNCH_RETRY_CNT = 5  # detect and store unmitmable domains and IPs
    SMART_CRAWLS_CNT = 5  # run multiple smart crawls to discover the best number for the warmup
else:
    LAUNCH_RETRY_CNT = 2  # load unmitmable domains and IPs from files
    SMART_CRAWLS_CNT = 1

TV_IP_ADDR = os.environ['TV_IP_ADDR']
SLEEP_TIMER = 5 
FWD_SLEEP_TO = 3 # Used in Smart Crawl to stop Fast Forwarding after few seconds
DATA_DIR = os.path.abspath(os.getenv("DATA_DIR"))
PLAT = os.getenv("PLATFORM")
TV_SERIAL_NO = os.getenv("TV_SERIAL_NO")
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
if os.path.isfile(os.getenv("MITMPROXY_CERT")):
    MITMPROXY_CERT = os.path.abspath(os.getenv("MITMPROXY_CERT"))
else:
    MITMPROXY_CERT = None
folders = [PCAP_PREFIX, DUMP_PREFIX, MITM_LOG_PREFIX, SCREENSHOT_PREFIX, SSLKEY_PREFIX,
           LOG_PREFIX, AUDIO_PREFIX, FIN_CHL_PREFIX, DB_PREFIX]


CUTOFF_TRESHOLD=100000
FAILURE_CUTOFF = 20

if MITMABLE_DOMAINS_WARM_UP_CRAWL:
    SCRAPE_TO = 1800  # timeout
else:
    SCRAPE_TO = 900

PLAT = os.getenv("PLATFORM")

EXTERNAL_IP_ADDRESS = get('https://api.ipify.org').text

print("Environment:")
l = list(locals().items())
for k in l:
    if "__" in k[0] or "module" in str(k[1]):
        continue
    print(k)
