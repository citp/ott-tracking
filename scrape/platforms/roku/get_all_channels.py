from __future__ import print_function
import json
import ast

ALL_CHANNELS_TXT = 'platforms/roku/channel_lists/all_channel_list.txt'  # file that includes all channel details

def get_channel_list(channel_list_file=ALL_CHANNELS_TXT):

    try:
        channel_list = []
        with open(channel_list_file, 'r') as f:
            list = ast.literal_eval(f.read())
        for channel in list:
            channel_item = {}
            channel_item['id'] = channel
            channel_item['_category'] = ""
            channel_list.append(channel_item)
        return channel_list
    except:
        print("Channel list file not a list, will continue!")

    channel_dict = {}
    with open(channel_list_file) as fp:
        for line in fp:
            record = json.loads(line)
            channel_dict.setdefault(record['_category'], []).append(record)
    return channel_dict
