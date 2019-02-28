import sys
import json
from curtsies import Input
import roku_remote
from time import sleep

ROKU_IP = "192.168.10.11"

KEY_LEFT = "Left"
KEY_RIGHT = "Right"
KEY_UP = "Up"
KEY_DOWN = "Down"
KEY_SELECT = "Select"
KEY_HOME = "Home"
MARKER_START = "Start"
MARKER_END = "End"
RESET = "Reset"
BACK = "Back"
FWD = "Fwd"
PLAY = "Play"
DELETE = "Delete"  # delete the last key
QUIT = "Quit"
SKIP = "Skip"

MARKERS = (MARKER_START, MARKER_END)


KEY_MAP = {
    'KEY_LEFT': KEY_LEFT,
    'KEY_RIGHT': KEY_RIGHT,
    'KEY_UP': KEY_UP,
    'KEY_DOWN': KEY_DOWN,
    '\n': KEY_SELECT,
    'h': KEY_HOME,  # key "h"
    's': MARKER_START,  # key "s"
    'e': MARKER_END,  # key "e"
    'r': RESET,
    'b': BACK,
    'f': FWD,
    'p': PLAY,
    '\x7f': DELETE,  # backspace
    'q': QUIT,
    '\x1b': SKIP,  # escape
}


"""
KEY_MAP = {
    curses.KEY_LEFT: KEY_LEFT,
    curses.KEY_RIGHT: KEY_RIGHT,
    curses.KEY_UP: KEY_UP,
    curses.KEY_DOWN: KEY_DOWN,
    10: KEY_SELECT,
    104: KEY_HOME,  # key "h"
    115: MARKER_START,  # key "s"
    101: MARKER_END,  # key "e"
    114: RESET,
    98: BACK,
    102: FWD,
    112: PLAY,
    263: DELETE,
    113: QUIT,
    27: SKIP,
}
"""


def get_key():
    with Input(keynames='curses') as ch_input:
        for key in ch_input:
            # print(repr(key))
            return key


def record_key_seq(chn_id, remote):
    key_seq = []
    outcome = "Unknown"
    print("""Available keys:

            == Roku remote ==

            Enter: Select/OK
            Left, Right, Up, Down arrows
            b: Back
            h: Home
            p: Play/Pause

            == Program controls ==
            Backspace: Delete the last key
            Esc: Skip this channel
            q: Quit program
            e: End the recording for this channel
            r: Reset the recorded keys
            """)

    while True:
        print("Key sequence", key_seq)
        key = get_key()
        ch = KEY_MAP.get(key, key)
        if not ch:
            print("Don't understand", ch)
            continue
        print("You pressed", ch)
        if ch == MARKER_END:
            print ("Mark End", key_seq)
            outcome = get_outcome()
            return key_seq, outcome
        elif ch == RESET:
            print ("Reset")
            key_seq = []
        elif ch == DELETE:  # backspace
            print ("Will delete the last key")
            del key_seq[-1]
        elif ch == QUIT:
            print ("Will quit")
            return key_seq, QUIT
        else:
            remote.press_key(ch)
            key_seq.append(ch)


def append_to_file(file_path, text):
    with open(file_path, 'a') as f:
        f.write(text)


def read_roku_channel_list(ch_file):
    ch_dict = {}
    for l in open(ch_file):
        ch_details = json.loads(l)
        ch_dict[ch_details["id"]] = ch_details["name"]
    return ch_dict


def get_outcome():
    while(True):
        print("""

        What was the outcome?

            1-Succesfully opened a full video clip.
            2-Succesfully opened a sample video clip.
            3-This is a paid app (requires payment through Roku)
            4-This app requires subscription (requires subscription outside Roku)
            5-App did't install or load.
            6-App loads, but video playback fails
            7-App loads, but there is no video to play
            """)
        key = get_key()
        if 1 <= int(key) <= 6:
            print("You pressed", key)
            return key
        print("Please try again")


def install_channel(roku_remote, chn_id, chn_name):
    print("Will install channel", chn_id, chn_name)
    roku_remote.install_channel(chn_id)
    sleep(3)
    roku_remote.press_key(KEY_SELECT)


def record_channel(remote, chn_id, chn_name):
    while True:
        print("Launching channel", chn_id, chn_name)
        remote.press_key(KEY_HOME)
        remote.launch_channel(chn_id)
        key_seq, outcome = record_key_seq(chn_id, remote)
        if outcome == QUIT:
            return key_seq, outcome
        print("\nChannel %s, Outcome %s, Key sequence: %s" % (
            chn_name, outcome, key_seq))
        print("Press r to redo, n to proceed to the next channel")
        key = get_key()
        if key == "r":
            print("Will relaunch the channel")
            continue
        elif key == "n":
            print("Proceeding to the next channel")
            break
        else:
            print("Don't understand", key)
    return key_seq, outcome


def main(username):
    channel_file = "%s_channels_smart_crawl.txt" % username
    out_key_seq_csv = "%s_roku_key_seqs.csv" % username
    print("Will install channels from %s" % channel_file)
    print("Will write output to %s" % out_key_seq_csv)
    ch_dict = read_roku_channel_list(channel_file)
    remote = roku_remote.RokuRemoteControl(ROKU_IP)
    remote.press_key(KEY_HOME)
    print("Will retrieve channel list from Roku at IP %s" % ROKU_IP)
    channel_list = remote.get_channel_list()
    print("Retrieved %d channels from Roku" % len(channel_list))
    # stdscr = curses.initscr()
    # curses.noecho()
    # curses.cbreak()
    # stdscr.keypad(1)
    for chn_id, chn_name in ch_dict.items():
        chn_id = str(chn_id)
        if chn_id not in channel_list:
            install_channel(remote, chn_id, chn_name)
        key_seq, outcome = record_channel(remote, chn_id, chn_name)
        remote.uninstall_channel(chn_id)
        sleep(1)
        remote.press_key(KEY_HOME)
        if outcome is QUIT:
            break

        # if key_seq is SKIP:
        #    continue
        #elif not len(key_seq):
        #    continue
        seq_str = ','.join(key_seq)
        result = "%s,%s,%s\n" % (chn_id, outcome, seq_str)
        print("Writing to file %s" % result)
        append_to_file(out_key_seq_csv, result)
    remote.press_key(KEY_HOME)
    print("Key sequences are saved to %s\n Thanks for your help!"
          % out_key_seq_csv)

USERS = ["arunesh", "ben", "danny", "gunes", "hooman"]

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage python record_rc.py %s" % USERS)
        sys.exit(1)

    username = sys.argv[1]
    if username not in USERS:
        print("Usage python record_rc.py %s" % USERS)
        sys.exit(1)

    main(username)
