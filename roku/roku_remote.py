# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import requests
import xml.etree.ElementTree as ET
from time import sleep

HTTP_OK = 200

DEBUG_HTTP = False


class RokuRemoteControl(object):

    def __init__(self, ip_address, port=8060):
        self.api_url = "http://%s:%s" % (ip_address, port)
        self.installed_apps = {}

    def send_post_request(self, url):
        r = requests.post(url)
        if DEBUG_HTTP:
            print(r.status_code, r.reason)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(r.status_code, r.reason)
        return r

    def send_get_request(self, url):
        r = requests.get(url)
        if DEBUG_HTTP:
            print(r.status_code, r.reason)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(r.status_code, r.reason)
        return r

    def press_key(self, key):
        self.send_post_request("%s/keydown/%s" % (self.api_url, key))
        self.send_post_request("%s/keyup/%s" % (self.api_url, key))

    def launch_channel(self, channel_id):
        self.send_post_request("%s/launch/%s" % (self.api_url, channel_id))

    def install_channel(self, channel_id):
        # the following launches the Channel Store details, but
        # but doesn't install the channel. We simulate a user key press
        # to install the channel
        self.send_post_request("%s/install/%s" % (self.api_url, channel_id))
        sleep(2)
        self.press_key("Select")
        # TODO: this will leave the confirmation (channel added) dialog on
        # send a Home key press to dismiss


    def uninstall_channel(self, channel_id):
        """Uninstall a given channel by simulating key presses."""
        # 11 is the Roku Channel Store app id
        # https://sdkdocs.roku.com/display/sdkdoc/External+Control+API#ExternalControlAPI-query/apps  # noqa
        self.send_post_request("%s/launch/11?contentID=%s" % (self.api_url, channel_id))
        sleep(2)
        self.press_key("Down")  # go to Remove channel
        sleep(0.5)
        self.press_key("Select")
        sleep(0.5)
        self.press_key("Up")  # Confirm removal
        sleep(0.5)
        self.press_key("Select")

    def get_channel_list(self):
        channel_list = {}
        r = self.send_get_request("%s/query/apps" % self.api_url)
        apps = ET.fromstring(r.text)
        for app in apps:
            app_id = app.get("id")
            channel_list[app_id] = {
                "id": app_id, "type": app.get("type"),
                "subtype": app.get("subtype"),
                "version": app.get("version"),
                "name": app.text
                }
            # print "App", app.get("id"), app.get("type"), app.get("subtype"),\
            #    app.get("version"), app.text
        return channel_list

    def get_active_channel(self):
        r = self.send_get_request("%s/query/active-app" % self.api_url)
        apps = ET.fromstring(r.text)
        for app in apps:
            app_id = app.get("id")
            #channel_list[app_id] = {
            #    "id": app_id, "type": app.get("type"),
            #    "subtype": app.get("subtype"),
            #    "version": app.get("version"),
            #    "name": app.text
            #    }
            # print "App", app.get("id"), app.get("type"), app.get("subtype"),\
            #    app.get("version"), app.text
        return app_id