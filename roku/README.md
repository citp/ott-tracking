# Automatic channel surfer



## Prerequisites

Run `sudo apt install dsniff` to install the `arpspoof` tool.

Run `sudo apt install fswebcam` so that you can take screenshots of the Roku TV.

You need to buy "ClonerAlliance Flint LX". Here's the [Amazon link](https://www.amazon.com/gp/product/B076GXQTJK/ref=oh_aui_detailpage_o00_s00?ie=UTF8&psc=1). When you connect it to a PC via USB, the device shows up as a video capturing device under `/dev/video0`. You can basically interact with it as if it were a webcam.


## Method

Run the scripts in the next section on a computer that is connected to
the same network as your Roku TV.


## Scripts to run

### Capturing Packets

The first two steps let you create pcap files for Roku's traffic.

First, edit `start_arpspoof.sh`. Replace `10.0.0.1` with the IP
address of your router. Replace `10.0.0.13` with the IP address of
your Roku TV and replace `eth0` with your iface name. Run `start_arpspoof.sh`.

Second, edit `start_pcap.sh`. Replace `10.0.0.13` with the IP address
of your Roku TV. Replace `b8:27:eb:63:ef:53` with the MAC address of
the computer that runs these scripts. Create a new directory called
`pcaps`. Run `start_pcap.sh`.

### Scraping Channels

Third, edit `scrape_channels.py`. Replace `10.0.0.13` with the IP
address of your Roku TV. Run `scrape_channels.py`. In this way, the
Python script will go through all the channels in `channel_list.txt`
(from the most popular to the least popular by Roku's metrics),
install each one, capture packets, launch the channel, run the channel
for 20 seconds, stop the packet capture, and uninstall the channel.



#Package MITMPROXY requires the following packages to be installed:
scapy: https://scapy.net/

redis-dump-load: https://github.com/p/redis-dump-load
