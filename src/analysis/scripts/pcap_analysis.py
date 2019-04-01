import sys
import pandas as pd
import numpy as np
import json
import traceback
from glob import glob
from os.path import join, sep

crawl_data_dir = sys.argv[1]
local_data_dir = sys.argv[2]


##Load Timestamps
def load_timestamp_json(root_dir):
    global data
    channel_timstamps = {}
    for txt_path in glob(root_dir + "/**/*-timestamps.json", recursive=True):
        filename = txt_path.split(sep)[-1]
        print("Loading %s" % txt_path)
        channel_name = filename.split("-")[0]
        try:
            with open(txt_path) as f:
                data = json.load(f)
                #df1 = pd.DataFrame(data)
                channel_timstamps[channel_name] = data
        except Exception:
            print("Couldn't open %s" % filename)
            traceback.print_exc()
    return channel_timstamps

#Create Timestamp DF
channel_timestamps = load_timestamp_json(crawl_data_dir)
df_ch_timestamps = pd.DataFrame(channel_timestamps).transpose().reset_index()
df_ch_timestamps.rename(columns={'index': 'Channel Name'}, inplace=True)


#Create global_df, containing all SSL/TCP streams SYN packets
def gen_global_df(root_dir):
    global_df = None
    for txt_path in glob(join(root_dir, "*.uniq")):
        filename = txt_path.split(sep)[-1]
        #print(txt_path)
        channel_name = filename.split("-")[0]
        #print(channel_name)
        df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
        df['Channel Name'] = channel_name
        df['MITM Attemp'] = 0
        df['SSL Failure'] = 0
        if global_df is None:
            global_df = df
        else:
            global_df = global_df.append(df)
        print(len(global_df.index))
        #print(global_df)
    return global_df

global_df = gen_global_df(local_data_dir)

#Find all streams in the list that have mitm in the cert
for txt_path in glob(join(local_data_dir, "*.pcap.mitmproxy-attemp")):
    filename = txt_path.split(sep)[-1]
    channel_name = filename.split("-")[0]
    df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
    tcp_stream_list = df['tcp.stream'].unique()
    global_df.loc[(global_df['tcp.stream'].isin(tcp_stream_list)) &
                  (global_df['Channel Name'] == channel_name), 'MITM Attemp'] = 1

#Find all tls failure due to invalid cert:
for txt_path in glob(join(local_data_dir, "*.pcap.ssl_fail")):
    filename = txt_path.split(sep)[-1]
    channel_name = filename.split("-")[0]
    df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
    tcp_stream_list = df['tcp.stream'].unique()
    global_df.loc[(global_df['tcp.stream'].isin(tcp_stream_list)) &
                  (global_df['Channel Name'] == channel_name), 'SSL Failure'] = 1

#Drop all duplicates
global_df = global_df.drop_duplicates(subset=['Channel Name', 'ip.dst',  'MITM Attemp',  'SSL Failure'])
print(global_df)




######Timestamp Analysis######
##############################

#Merge global_df with timestamp_df
global_df_merged = pd.merge(global_df, df_ch_timestamps, on=['Channel Name'])
global_df_merged['epoch'] = np.nan

epoch_list = list(df_ch_timestamps)
epoch_list.remove('Channel Name')


#Populate epoch column for channel based on
#the timestamp of SYN packet.
for epoch in epoch_list:
    global_df_merged['epoch'] = np.where(global_df_merged['frame.time_epoch']>global_df_merged[epoch],
                                     epoch, global_df_merged['epoch'])





#Graph
import numpy as np
import matplotlib.pyplot as plt

plt1 = plt.figure(1)
labels = [e for e in epoch_list if 'launch' in e]
new_endpoints_df = global_df_merged.drop_duplicates(subset=['Channel Name', 'ip.dst'])

new_endpoints_count = []
for epoch in labels:
    df_epoch = new_endpoints_df.loc[global_df_merged['epoch'] == epoch]
    total_len = len(df_epoch)
    print( "%s saw %s new end point" % (epoch, str(total_len)) )
    new_endpoints_count.append(total_len)

N = len(labels)
ind = np.arange(N)
width = 0.35

p1 = plt.bar(ind, new_endpoints_count, width)
plt.xticks(ind, labels)

plt1.show()


plt2 = plt.figure(2)
labels = epoch_list
failure_percentage = []
success_percentage = []
for epoch in epoch_list:
    df_epoch = global_df_merged.loc[global_df_merged['epoch'] == epoch]
    total_len = len(df_epoch)
    failure_len = len(df_epoch.loc[df_epoch['SSL Failure'] == 1])
    if total_len == 0:
        failure_percent = 0
        success_percent = 100
    else:
        failure_percent = 100 * float(failure_len)/float(total_len)
        success_percent = 100 - failure_percent
    failure_percentage.append(failure_percent)
    success_percentage.append(success_percent)
    print(failure_percentage)
    print(success_percentage)
    print('******')




N = len(epoch_list)
ind = np.arange(N)
width = 0.35


p1 = plt.bar(ind, failure_percentage, width)
p2 = plt.bar(ind, success_percentage, width, bottom=failure_percentage)
plt.xticks(ind, epoch_list)
plt.yticks(np.arange(0, 100, 10))
plt.ylabel('Percentage')
plt.title('TLS Failure Rates for each Stage')
plt.legend((p1[0], p2[0]), ('Failure', 'Success (Intercepted and Pass-Through'))


plt2.show()
