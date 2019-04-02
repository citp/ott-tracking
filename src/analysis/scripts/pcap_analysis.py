import sys
import pandas as pd
import json
import traceback
from glob import glob
from os.path import join, sep

##Load Timestamps
def load_timestamp_json(root_dir):
    global data
    channel_timstamps = {}
    print("Loading timestamp data from %s" % root_dir)
    for txt_path in glob(root_dir + "/**/*-timestamps.json", recursive=True):
        filename = txt_path.split(sep)[-1]
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


#Create global_df, containing all SSL/TCP streams SYN packets
def gen_global_df(root_dir):
    print("Generating Global DF from %s " % root_dir)
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
        #print(len(global_df.index))
        #print(global_df)
    return global_df

#Add SSL features
def add_ssl_features(global_df, post_process_dir):
    print("Adding SSL features to DF from %s " % post_process_dir)
    #Find all streams in the list that have mitm in the cert
    for txt_path in glob(join(post_process_dir, "*.pcap.mitmproxy-attemp")):
        filename = txt_path.split(sep)[-1]
        channel_name = filename.split("-")[0]
        df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
        tcp_stream_list = df['tcp.stream'].unique()
        global_df.loc[(global_df['tcp.stream'].isin(tcp_stream_list)) &
                      (global_df['Channel Name'] == channel_name), 'MITM Attemp'] = 1

    #Find all tls failure due to invalid cert:
    for txt_path in glob(join(post_process_dir, "*.pcap.ssl_fail")):
        filename = txt_path.split(sep)[-1]
        channel_name = filename.split("-")[0]
        df = pd.read_csv(txt_path, sep=',', encoding='utf-8', index_col=None)
        tcp_stream_list = df['tcp.stream'].unique()
        global_df.loc[(global_df['tcp.stream'].isin(tcp_stream_list)) &
                      (global_df['Channel Name'] == channel_name), 'SSL Failure'] = 1
    return global_df



def str_to_int_key(text):
    return int(text.split('-')[1])
