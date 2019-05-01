"""
Extracts channel names from APKs in the apk_cache.

"""
import subprocess
import re
import os


LABEL = 'cat'


def main():

    # Write result to CSV
    if LABEL:
        writer = open('channel_names_LABEL.csv'.replace('LABEL', LABEL), 'w')
    else:
        writer = open('channel_names.csv', 'w')

    print >>writer, 'channel_name,apk_id'

    for apk_id in os.listdir('apk_cache'):

        # Use aapt to parse the name of the APK
        try:
            output = subprocess.check_output(
                'aapt d badging apk_cache/{0}'.format(apk_id),
                shell=True
            )
        except subprocess.CalledProcessError:
            print 'Error:', apk_id
            continue

        match = re.search(r"label='([^']+)' icon", output)
        if match:
            channel_name = get_standard_channel_name(match.group(1))
            print >>writer, '{},{}'.format(channel_name, apk_id)
            writer.flush()
        else:
            print 'No name:', apk_id

    writer.close()


def get_standard_channel_name(channel_name):

    channel_name = channel_name.lower()

    # Keep only alpha numeric characters
    output = ''
    for ch in channel_name:
        if 'a' <= ch <= 'z' or '0' <= ch <= '9':
            output += ch
        else:
            output += ' '

    # Remove extra spaces
    return ' '.join(output.split())


if __name__ == '__main__':
    main()
