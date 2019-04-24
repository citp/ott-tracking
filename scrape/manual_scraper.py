from curtsies import Input
from scrape_channels import *
from datetime import datetime
from os.path import join, isfile
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



question_list = [
"0. Did the app open?",
"1. Did the channel need a signup of any sort to view content? (Y/N)",
"2. Did you sign up to view content? (Y/N)",
"3. What was the sign up link? (Leave blank if there was no link)",
"4. How many videos did you watch? (0 if you couldn't watch video)",
"5. How many ads did you watch? (0 for no Ad)",
"6. Additional comments."
]

def questionnaire(channel_name):
    q_filename = join(scrape_config.DATA_DIR, scrape_config.FIN_CHL_PREFIX,
                                str(channel_name + "_questionnaire")) + ".txt"
    with open(q_filename, 'w') as f:
        for question in question_list:
            f.write(question + "\n")
            answer = input(question)
            f.write(answer + "\n")

def terminat_screenshot(screenshot_process_terminate_event, screenshot_process):
    screenshot_process_terminate_event.set()
    time.sleep(7)
    try:
        screenshot_process.terminate()
    except:
        print("Screenshot process not found!")

def scrape_channel(username):
    channels = read_channels_for_user(username)
    output_file_desc = open(scrape_config.LOG_FILE_PATH_NAME)
    dns_sniffer_run()
    for channel_name in channels:
        channel_res_file = join(scrape_config.DATA_DIR, scrape_config.FIN_CHL_PREFIX,
                                str(channel_name)) + ".txt"
        if isfile(channel_res_file):
            print('Skipping', channel_name, ' due to:', channel_res_file)
            continue
        print("Will scrape %s" % channel_name)
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
        # channel_name = input("What is the name of the channel(exact application name): ")
        # channel_name = channel
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
            if scrape_config.MITMPROXY_ENABLED:
                mitmrunner = ret[2]
            else:
                mitmrunner = None
        nextKey = ""
        #while nextKey != 'n':
        #key = ""
        #while key!= 'n':
        #    print("CONSOLE>>> Install the channel manually then press \'n\'.")
        #    key = get_key()
        #    if key == "r":
        #        print("CONSOLE>>> Restarting!")
        #        collect_data(surfer, mitmrunner, date_prefix)
        #        break
        #    elif key == "q":
        #        print("CONSOLE>>> Quiting!")
        #        collect_data(surfer, mitmrunner, date_prefix)
        #        return
        #if key == "r":
        #    continue
        print("CONSOLE>>> Installing channel %s" %channel_name)
        err_occurred = install_channel(surfer)
        if err_occurred:
            print("CONSOLE>>> Error during installing channel %s, restarting" %channel_name)
            continue
        while key!= 'l':
            print("CONSOLE>>> The channel installation is done. Press \'l\' to launch channel.")
            key = get_key()
            if key == "r":
                print("CONSOLE>>> Restarting!")
                collect_data(surfer, mitmrunner, date_prefix)
                break
            elif key == "q":
                print("CONSOLE>>> Quiting!")
                collect_data(surfer, mitmrunner, date_prefix)
                return
        if key == "r":
            continue
        sc_tuple = crawl_channel(surfer, mitmrunner, True)
        while key!= 'c':
            print("CONSOLE>>> Launch the channel manually then press \'c\' when done to collect data.")
            key = get_key()
            if key == "r":
                print("CONSOLE>>> Restarting!")
                collect_data(surfer, mitmrunner, date_prefix)
                terminat_screenshot(sc_tuple[0], sc_tuple[1])
                break
            elif key == "q":
                print("CONSOLE>>> Quiting!")
                collect_data(surfer, mitmrunner, date_prefix)
                terminat_screenshot(sc_tuple[0], sc_tuple[1])
                return
        if key == "r":
            continue
        err_occurred = collect_data(surfer, mitmrunner,  date_prefix)

        terminat_screenshot(sc_tuple[0], sc_tuple[1])

        questionnaire(channel_name)
        write_log_files(output_file_desc, channel_name, channel_res_file, "TERMINATED")
        if not err_occurred:
            print("CONSOLE>>> Successfully scrapped channel %s" % channel_name)
        else:
            print("CONSOLE>>> Error in scrapping channel %s" % channel_name)


def read_channels_for_user(username):
    apk_names = []
    for l in open("manual_interaction_channel_lists/%s.csv" % username):
        apk_name = (l.rstrip().split(",")[2])
        apk_names.append(apk_name)

    return apk_names


def main_loop(username):
    start_screenshot()
    flushall_iptables()
    scrape_channel(username)
    dns_sniffer_stop()
    stop_screenshot()

if __name__ == '__main__':
    username = sys.argv[1]
    print("CHs", read_channels_for_user(username))
    main_loop(username)
