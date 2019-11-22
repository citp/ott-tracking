import pandas as pd
import sys

if __name__ == "__main__":
    file_name = sys.argv[1]
    df = pd.read_pickle(file_name)
    df.to_csv(sys.argv[2], index=None)
