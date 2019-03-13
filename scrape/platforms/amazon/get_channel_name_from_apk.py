"""
Extracts channel names from APKs in the apk_cache.

"""
import subprocess
import re
from scrape_amazon_stick_app_page import get_standard_channel_name


def main():

    # Parse APK installation log
    reader = open('pull_apks.log')

    # Write result to CSV
    writer = open('channel_names.csv', 'w')
    print >>writer, 'amazon_ranking,channel_name,apk_id'

    ranking = None

    for line in reader:

        line = line.strip()

        # Find APKs installed --- in the order in which they were installed
        match = re.search(r'Done with (.*)', line)
        if not match:
            continue
        apk_id = match.group(1)

        if ranking is None:
            ranking = 0
        else:
            ranking += 1

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
            print >>writer, '{},{},{}'.format(ranking, channel_name, apk_id)
            writer.flush()
        else:
            print 'No name:', apk_id

    writer.close()
    reader.close(0)


if __name__ == '__main__':
    main()
