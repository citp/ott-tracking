from curtsies import Input
from scrape_channels import *

# For each channel to the following (steps with * require a signal):
# 1-SCRIPT* (START_CHNL): Cleanup, start new channel, prompt for name
# 2-SCRIPT (START_INSTALL): Run tcpdump and dns_sniffer
# >>USER: Install the channel
# 3-SCRIPT* (optional START_MITM): Lanuch mitmdump
# >>USER: Launch channel (repeat xTimes)
# 4-SCRIPT* (COLLECT_DATA): collect pcap, (opt. mitm logs), redis-db
# 5-SCRIPT (END_CHNL): terminate tcpdump, (opt. mitmdump), dns_sniffer

START_CHNL = "Start channel"
START_MITM = "Start MITM"
LAUNCH_CHNL = "Launch channel"
RESET = "Reset channel"
COLLECT_DATA = "Collect data"
END_CHNL = "End channel"
QUIT = "Quit"

KEY_MAP = {
    's': START_CHNL,
    'm': START_MITM,
    'l': LAUNCH_CHNL,
    'r': RESET,
    'c': COLLECT_DATA,
    'e': END_CHNL,
    'q': QUIT
}

def get_key():
    with Input(keynames='curses') as ch_input:
        for key in ch_input:
            # print(repr(key))
            return key

def setup_channel():
    pass

def launch_mitm():
    pass

def launch_channel():
    pass

def collect_data():
    pass

def end_channel():
    pass

def scrape_channel():
    while True:
        key = get_key()
        ch = KEY_MAP.get(key, key)
        if not ch:
            print("Don't understand", ch)
            continue
        elif ch == END_CHNL:
            print("Ending channel")
        elif ch == QUIT:
            print("Will quit")
            return ""

def main_loop():
    while True:
        pass

if __name__ == '__main__':
    REC_AUD = True
    MITMPROXY_ENABLED = True
    scrape("00","123")
    main_loop()
