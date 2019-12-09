# How to download APKs

This folder contains scripts that Danny used to pull APKs from the App Store.

Instructions for Danny:

1. Connect to the stick. Run `adb connect [IP address]`. Verify with `adb devices`.
2. (Optional) Run `python pull_apks.py` for a minute to remove all non-essential packages. This step may remove some system packages if Amazon has recently updated the OS.
3. (Optional)Reboot the TV, allowing Amazon to reinstall essential packages.
4. (Optional)Upon reboot, run `./get_base_packages.sh` to get a list of all system packages.
5. (Optional)Run `rm pull_apks.log`.
6. Run `python pull_apks.py` to monitor new packages and then pull them continuously.

In a separate terminal window, do the following:

0. Set all `LABEL` flag.
1. Run `python scrape_amazon_stick_app_page.py` to get the latest ASINs.
2. Run `rm install_from_app_store_LABEL.log`.
3. Run `python install_from_app_store.py` to scrape the app store.
4. When `install_from_app_store.py` terminates, wait for `pull_apks.py` to show no activities; sometimes, the install queue can be as long as 15 minutes --- in which case just terminate `pull_apks.py`.

The APKs will be downloaded to a local directory `apk_cache/`. Copy them to our webserver so that the other scripts can access the APKs as well. Run `rsync -av --progress apk_cache/* [remote_server]`. The APKs will be available at [http_server].

Also, update the channel names: `python get_channel_name_from_apk.py`

Finally, obtain the ranking and Amazon product info; refer to `channel_details/README.md`.
