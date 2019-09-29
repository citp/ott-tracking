# encoding=utf8
from __future__ import print_function
import sys
#reload(sys)
#sys.setdefaultencoding('utf8')

import requests
import xml.etree.ElementTree as ET
import traceback
from time import sleep

HTTP_OK = 200

DEBUG_HTTP = False


class RokuRemoteControl():

    def __init__(self, ip_address, channel_id, port=8060):
        self.api_url = "http://%s:%s" % (ip_address, port)
        self.installed_apps = {}
        self.channel_id = channel_id

    def send_post_request(self, url):
        try:
            r = requests.post(url)
            if DEBUG_HTTP:
                print((r.status_code, r.reason))
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print((r.status_code, r.reason))
        except Exception as e:
            print ("HTTP POST REQ FAIL FOR %s" % str(url))
            traceback.print_tb(e.__traceback__)
            return None
        return r

    def send_get_request(self, url):
        try:
            r = requests.get(url)
            if DEBUG_HTTP:
                print((r.status_code, r.reason))
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print((r.status_code, r.reason))
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            return None
        return r

    def press_key(self, key):
        self.send_post_request("%s/keydown/%s" % (self.api_url, key))
        self.send_post_request("%s/keyup/%s" % (self.api_url, key))

    def launch_channel(self):
        self.send_post_request("%s/launch/%s" % (self.api_url, self.channel_id))

    def install_channel(self):
        # the following launches the Channel Store details, but
        # but doesn't install the channel. We simulate a user key press
        # to install the channel
        self.send_post_request("%s/install/%s" % (self.api_url, self.channel_id))
        sleep(2)
        self.press_key("Select")
        # TODO: this will leave the confirmation (channel added) dialog on
        # send a Home key press to dismiss

    def is_showing_home(self):
        return True

    def uninstall_channel(self):
        """Uninstall a given channel by simulating key presses."""
        # 11 is the Roku Channel Store app id
        # https://sdkdocs.roku.com/display/sdkdoc/External+Control+API#ExternalControlAPI-query/apps  # noqa
        self.send_post_request("%s/launch/11?contentID=%s" % (self.api_url, self.channel_id))
        sleep(2)
        self.press_key("Down")  # go to Remove channel
        sleep(0.5)
        self.press_key("Select")
        sleep(0.5)
        self.press_key("Up")  # Confirm removal
        sleep(0.5)
        self.press_key("Select")

    def get_installed_channels(self):
        channel_list = {}
        r = self.send_get_request("%s/query/apps" % self.api_url)
        if r == None:
            print("Request for get_channel_list failed!")
            return None
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
        if r == None:
            print("Request for get_active_channel failed!")
            return None
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

    def reboot(self):
        pass

    def terminate(self):
        pass
