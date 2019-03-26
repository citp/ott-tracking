#load tcp/ssl stream from csv file
import sys
import pandas as pd
import json
import traceback
from glob import glob
from os.path import join, sep

crawl_data_dir = sys.argv[1]

##Replace _ with -
def load_timestamp_json(root_dir):
    global data
    channel_timstamps = {}
    for txt_path in glob(root_dir + "/**/*_timestamps.json", recursive=True):
        filename = txt_path.split(sep)[-1]
        print("Loading %s" % txt_path)
        channel_name = filename.split("_")[0]
        try:
            with open(txt_path) as f:
                data = json.load(f)
                #df1 = pd.DataFrame(data)
                channel_timstamps[channel_name] = data
        except Exception:
            print("Couldn't open %s" % filename)
            traceback.print_exc()
    return channel_timstamps


channel_timestamps = load_timestamp_json(crawl_data_dir)
df_ch_timestamps = pd.DataFrame(channel_timestamps).transpose()



local_data_dir = sys.argv[2]
global_df = None
for txt_path in glob(join(local_data_dir, "*.uniq")):
    filename = txt_path.split(sep)[-1]
#    print(txt_path)
    channel_name = filename.split("-")[0]
#    print(channel_name)
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

#find all streams in the list that have mitm in the cert

for txt_path in glob(join(local_data_dir, "*.pcap.mitmproxy-attemp")):
    filename = txt_path.split(sep)[-1]
    channel_name = filename.split("-")[0]
    df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
    #df['Channel Name'] = channel_name
    #df['MITM Attemp'] = 1
    #print( df.columns.str.lower())
    for i, row in df.iterrows():
        for name, value in row.iteritems():
            if name == 'tcp.stream':
                tcp_stream = value
                global_df.loc[(global_df['tcp.stream'] ==  tcp_stream)
                                 & (global_df['Channel Name'] == channel_name), 'MITM Attemp'] = 1
                break

#find all tls failure due to invalid cert:

for txt_path in glob(join(local_data_dir, "*.pcap.ssl_fail")):
    filename = txt_path.split(sep)[-1]
    channel_name = filename.split("-")[0]
    df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
    #df['Channel Name'] = channel_name
    #df['MITM Attemp'] = 1
    #print( df.columns.str.lower())
    for i, row in df.iterrows():
        for name, value in row.iteritems():
            if name == 'tcp.stream':
                tcp_stream = value
                global_df.loc[(global_df['tcp.stream'] ==  tcp_stream)
                                 & (global_df['Channel Name'] == channel_name), 'SSL Failure'] = 1
                break


global_df = global_df.drop_duplicates(subset=['Channel Name', 'ip.dst',  'MITM Attemp',  'SSL Failure'])
print(global_df)


