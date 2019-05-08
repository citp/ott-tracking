ALL_CHANNELS_TXT = 'platforms/amazon/channel_lists/channel_names.csv'  # file that includes all channel details

def get_channel_list(channel_csv=ALL_CHANNELS_TXT):
    """Returns a dictionary of all available channels for install."""

    channel_list = []

    with open(channel_csv) as fp:
        for (line_index, line) in enumerate(fp):
            if line.startswith("#"):
                continue
            channel_values = line.strip().split(',')
            if 'amazon_ranking' in channel_values:
                continue
            if len(channel_values) == 3:
                ranking, channel_name, apk_id = channel_values
                record = {
                    'id': apk_id,
                    '_category': 'Unknown',
                    'type': 'Unknown',
                    'subtype': 'Unknown',
                    'version': 'Unknown',
                    'name': channel_name,
                    'ranking': int(ranking)
                }
            elif len(channel_values) == 8:
                amazon_ranking, apk_name, apk_id, amazon_category, product_id,\
                product_name, overlap_token_count, developer_name = channel_values
                record = {
                    'id': apk_id,
                    '_category': amazon_category,
                    'apk_name': apk_name,
                    'product_id': product_id,
                    'overlap_token_count': overlap_token_count,
                    'developer_name': developer_name,
                    'name': product_name,
                    'amazon_ranking': int(amazon_ranking)
                }
            channel_list.append(record)

    return channel_list

if __name__ == '__main__':
    get_channel_list()