from curtsies import Input
from scrape_channels import *
from datetime import datetime
import time


# For each channel to the following (steps with * require a signal):
# 1-SCRIPT* (START_CHNL): Cleanup, start new channel, prompt for name
# 2-SCRIPT (START_INSTALL): Run tcpdump and dns_sniffer
# >>USER: Install the channel
# 3-SCRIPT* (optional START_MITM): Lanuch mitmdump
# >>USER: Launch channel (repeat xTimes)
# 4-SCRIPT* (COLLECT_DATA): collect pcap, (opt. mitm logs), redis-db
# 5-SCRIPT (END_CHNL): terminate tcpdump, (opt. mitmdump), dns_sniffer


def get_key():
    with Input(keynames='curses') as ch_input:
        for key in ch_input:
            # print(repr(key))
            return key


def scrape_channel():
    output_file_desc = open(scrape_config.LOG_FILE_PATH_NAME)
    dns_sniffer_run()
    while True:
        #key = get_key()
        #ch = KEY_MAP.get(key, key)
        #restart if "r" is pressed
        time.sleep(2)
        print("CONSOLE>>> Do you need MITM for the next channel[y/n]? ")
        key = get_key()
        if key == "y":
            scrape_config.MITMPROXY_ENABLED = True
        elif key == "n":
            scrape_config.MITMPROXY_ENABLED = False
        elif key == "r":
            print("CONSOLE>>> Restarting!")
            continue
        elif key == "q":
            print("CONSOLE>>> Quiting!")
            return
        else:
            print("CONSOLE>>> Not a valid input, try again!")
            continue
        channel_name = input("What is the name of the channel: ")
        date_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")
        channel_res_file = join(scrape_config.DATA_DIR, scrape_config.FIN_CHL_PREFIX,
                                channel_name) + ".txt"

        ret = setup_channel(channel_name, date_prefix)
        err_occurred = ret[0]
        if err_occurred:
            print("CONSOLE>>> Error occurred in setup!")
            continue
        else:
            surfer = ret[1]
            timestamps = ret[2]
            if scrape_config.MITMPROXY_ENABLED:
                mitmrunner = ret[3]
            else:
                mitmrunner = None
        nextKey = ""
        #while nextKey != 'n':
        key = ""
        while key!= 'n':
            print("CONSOLE>>> Install the channel manually then press \'n\'.")
            key = get_key()
            if key == "r":
                print("CONSOLE>>> Restarting!")
                collect_data(surfer, mitmrunner, timestamps, date_prefix, channel_name)
                break
            elif key == "q":
                print("CONSOLE>>> Quiting!")
                collect_data(surfer, mitmrunner, timestamps, date_prefix, channel_name)
                return
        if key == "r":
            continue
        if scrape_config.MITMPROXY_ENABLED:
            launch_mitm(mitmrunner)
        while key!= 'c':
            print("CONSOLE>>> Launch the channel manually then press \'c\' when done to collect data.")
            key = get_key()
            if key == "r":
                print("CONSOLE>>> Restarting!")
                collect_data(surfer, mitmrunner, timestamps, date_prefix, channel_name)
                break
            elif key == "q":
                print("CONSOLE>>> Quiting!")
                collect_data(surfer, mitmrunner, timestamps, date_prefix, channel_name)
                return
        if key == "r":
            continue
        err_occurred = collect_data(surfer, mitmrunner, timestamps, date_prefix, channel_name)
        write_log_files(output_file_desc, channel_name, channel_res_file, "TERMINATED")
        if not err_occurred:
            print("CONSOLE>>> Successfully scrapped channel %s" % channel_name)
        else:
            print("CONSOLE>>> Error in scrapping channel %s" % channel_name)


def main_loop():
    scrape_channel()
    dns_sniffer_stop()

if __name__ == '__main__':
    main_loop()
