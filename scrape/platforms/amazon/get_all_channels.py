ALL_CHANNELS_TXT = 'platforms/amazon/channel_lists/channel_names.csv'  # file that includes all channel details

def get_channel_list(channel_csv=ALL_CHANNELS_TXT):
    """Returns a dictionary of all available channels for install."""

    channel_list = []

    with open(channel_csv) as fp:
        for (line_index, line) in enumerate(fp):
            if line_index <= 1 :
                continue
            ranking, channel_name, apk_id = line.strip().split(',')
            record = {
                'id': apk_id,
                '_category': 'Unknown',
                'type': 'Unknown',
                'subtype': 'Unknown',
                'version': 'Unknown',
                'name': channel_name,
                'ranking': int(ranking)
            }
            channel_list.append(record)

    return channel_list

if __name__ == '__main__':
    get_channel_list()