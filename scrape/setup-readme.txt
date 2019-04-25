#Install pip3
sudo apt install python3-pip
#Install packages
pip3 install --user curtsies redis-dump-load mitmproxy scapy 
# For Amazon install mitmproxy certs on the Amazon stick
#Install Redis database
scrape/tools/redis/install_redis.sh
sudo setcap cap_net_raw=eip `which python3.6`
sudo setcap cap_net_raw=eip `which tcpdump`

#Modify scrape/global.conf to include your WLAN interface name
#Modify platform/"amazon/roku"/config.txt to include the TV IP address

#Install ADB Amazon:
sudo apt install adb
