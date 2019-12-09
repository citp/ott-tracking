# Prerequisites

- Install pip3 ffmpeg
  - `sudo apt install python3-pip ffmpeg`
- Install Python packages:
  - `pip3 install --user curtsies redis-dump-load mitmproxy scapy`
- Install Redis:
  - Use the script `tools/redis/install_redis.sh`
  - For more info see: https://redis.io/topics/quickstart
- For Amazon Fire TV, install adb:
  - `sudo apt install adb`
- To run scapy without root access:
   - `setcap cap_net_raw=eip /usr/bin/pythonX.X` -> Your python3 executable.
   - `setcap cap_net_raw=eip /usr/bin/tcpdump`

## Crawl Setup:
- Set the platform to `amazon` or `roku` in `global.conf`.
- Crawl data directory is stored in `DATA_DIR` in `global.conf`.
- Store your WiFi interface name in `WLAN_IF` variable in `global.conf`.
- Modify `platform/"amazon/roku"/config.txt` to include the `TV_IP_ADDR`.
- For Amazon Fire TV, modify`platform/amazon/config.txt` to include `TV_SERIAL_NO`.


## Running crawls
- Network setup: The code should be run from a machine that is in the same network as the OTT device.
- To run Roku crawls run: `./starter_automatic.sh ./platforms/roku/channel_lists/random_channels_3.txt`
- To run Fire TV crawls run: `./starter_automatic.sh ./platforms/amazon/channel_lists/test/100-channel_name.csv`
