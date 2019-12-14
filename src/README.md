## Data Processing Pipeline

For each new crawl, we run the `extract_comm_details.sh` script. This script processes pcaps (into json files), pickles dataframes so they can be loaded faster, and runs leak detection.

- `cd src/analysis/scripts`
- `./extract_comm_details.sh PATH_TO_CRAWL_DATA/roku-data-2019XXXX-XXXXXX/`

You can then run the [notebooks](analysis/notebooks) using the pickled datatframes.
