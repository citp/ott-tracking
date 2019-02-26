import sys
import json
import curses
import roku_remote
from time import sleep

ROKU_IP = "192.168.10.20"

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


def record_channel(chn_id, remote, stdscr):
    key_seq = []
    recording = True
    print "Press to start"
    while True:
        c = stdscr.getch()
        ch = KEY_MAP.get(c, None)
        if not ch:
            print "Don't understand", c
            continue
        print ch
        if ch == MARKER_END:
            print "Mark End", key_seq
            return key_seq
        elif ch == RESET:
            print "Reset"
            key_seq = []
        elif ch == DELETE:  # backspace
            print "Will delete the last key"
            del key_seq[-1]
        elif ch == QUIT:
            print "Will quit"
            return QUIT
        elif ch == SKIP:
            print "Will skip this channel"
            return SKIP
        else:
            remote.press_key(ch)
            if recording:
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


def main(username):
    channel_file = "%s_channels_smart_crawl.txt" % username
    out_key_seq_csv = "%s_roku_key_seqs.csv" % username
    print("Will install channels from %s" % channel_file)
    print("Will write output to %s" % out_key_seq_csv)
    ch_dict = read_roku_channel_list(channel_file)
    remote = roku_remote.RokuRemoteControl(ROKU_IP)
    print("Will retrieve channel list from Roku at IP %s" % ROKU_IP)
    channel_list = remote.get_channel_list()
    print("Retrieved %d channels from Roku" % len(channel_list))
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)
    for chn_id, name in ch_dict.iteritems():
        chn_id = str(chn_id)
        if chn_id not in channel_list:
            print("Will install channel", chn_id, name)
            remote.install_channel(chn_id)
            sleep(3)
            remote.press_key(KEY_SELECT)

        remote.launch_channel(chn_id)
        key_seq = record_channel(chn_id, remote, stdscr)
        remote.uninstall_channel(chn_id)
        sleep(1)
        remote.press_key(KEY_HOME)
        if key_seq is SKIP:
            continue
        elif key_seq is QUIT:
            break
        elif not len(key_seq):
            continue
        print("Will write to file %s" % key_seq)
        seq_str = ','.join(key_seq)
        append_to_file(out_key_seq_csv, "%s,%s\n" % (chn_id, seq_str))
    remote.press_key(KEY_HOME)
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()


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
