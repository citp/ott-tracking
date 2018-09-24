# Automatic channel surfer



## Prerequisites

Run `sudo apt install dsniff` to install the `arpspoof` tool.


## Method

Run the scripts in the next section on a computer that is connected to
the same network as your Roku TV.


## Scripts to run


First, edit `start_arpspoof.sh`. Replace `10.0.0.1` with the IP
address of your router. Replace `10.0.0.13` with th eIP address of
your Roku TV. Run `start_arpspoof.sh`.

Second, edit `start_pcap.sh`. Replace `10.0.0.13` with the IP address
of your Roku TV. Replace `b8:27:eb:63:ef:53` with the MAC address of
the computer that runs these scripts. Create a new directory called
`pcaps`. Run `start_pcap.sh`.

Third, edit `scrape_channels.py`. Replace `10.0.0.13` with the IP
address of your Roku TV. Run `scrape_channels.py`. In this way, the
Python script will go through all the channels in `channel_list.txt`
(from the most popular to the least popular by Roku's metrics),
install each one, capture packets, launch the channel, run the channel
for 20 seconds, stop the packet capture, and uninstall the channel.

