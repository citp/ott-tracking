#load tcp/ssl stream from csv file
import sys
import pandas as pd
from glob import glob
from os.path import join, sep

data_dir = sys.argv[1]
global_df = None
for txt_path in glob(join(data_dir, "*.uniq")):
    filename = txt_path.split(sep)[-1]
    print(txt_path)
    channel_name = filename.split("-")[0]
    print(channel_name)
    df = pd.read_csv(txt_path, sep=',', encoding='utf-8')
    df['Channel Name'] = channel_name
    if global_df is None:
        global_df = df
    else:
        global_df = global_df.append(df)
    #print(len(global_df.index))
    print(global_df)
#find all streams in the list that have mitm in the cert

#