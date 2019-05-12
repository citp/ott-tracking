from adblockparser import AdblockRules
from GhosteryListParser import GhosteryListParser
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

import json


def read_ab_rules_from_file(filename):
    filter_list = set()
    for l in open(filename):
        if len(l) == 0 or l[0] == '!':  # ignore these lines
            continue
        else:
            filter_list.add(l.strip())
    return filter_list


def get_adblock_rules():
    raw_easylist_rules = read_ab_rules_from_file("blocklists/easylist.txt")
    raw_easyprivacy_rules = read_ab_rules_from_file("blocklists/easyprivacy.txt")
    # raw_ublock_rules = read_ab_rules_from_file("blocklists/adblock_blacklist_white.txt")

    print ("Loaded %s from EasyList, %s rules from EasyPrivacy" %
           (len(raw_easylist_rules), len(raw_easyprivacy_rules)))
    #        len(raw_ublock_rules)))

    easylist_rules = AdblockRules(raw_easylist_rules)
    easyprivacy_rules = AdblockRules(raw_easyprivacy_rules)
    # ublock_rules = AdblockRules(raw_ublock_rules)
    # return easylist_rules, easyprivacy_rules, ublock_rules
    return easylist_rules, easyprivacy_rules


def get_disconnect_blocked_hosts():
    blocked_hosts = set()
    disconnect = json.loads(open("blocklists/disconnect.json").read())
    categories = disconnect["categories"]
    for category_name, entries in categories.items():
        if category_name == "Content":
            # Content category is not used by default by Firefox's
            # tracking protection and Focus browsers
            print ("Will not block the hosts in Disconnect's Content category")
            continue
        for entry in entries:
            adresses = entry.values()
            for address in adresses:
                address.pop("dnt", None)  # there's one such entry
                # and it's not a domain/host
                # hosts_list = address.values()
                hosts_list = list(address.values())
                blocked_hosts.update(hosts_list[0])

    print (len(blocked_hosts), "blocked hosts")
    # note that disconnect keep a list of blocked hosts, not PS+1s
    assert "adwords.google.com" in blocked_hosts
    assert "facebook.com" in blocked_hosts
    return list(blocked_hosts)


def is_blocked_by_disconnect(url, disconnect_blocked_hosts):
    host = urlparse(url).hostname
    if host in disconnect_blocked_hosts:
        return True
    while True:
        # strip one subdomain at a time
        host = host.split(".", 1)[-1]  # take foo.com from bar.foo.com
        if "." not in host:
            return False
        if host in disconnect_blocked_hosts:
            return True
    return False  # this shouldn't happen unless we are provided a corrupt hostname


def check_urls_in_lists(urls):
    easylist_rules, easyprivacy_rules = get_adblock_rules()
    disconnect_blocklist = get_disconnect_blocked_hosts()
    ghostery_blocklist = GhosteryListParser("blocklists/ghostery.json")

    result = []

    for url in urls:
        url_result = {"url": url}
        url_result["easylist"] = True if easylist_rules.should_block(url) else False
        url_result["easypivacy"] = True if easyprivacy_rules.should_block(url) else False
        url_result["disconnect"] = True if is_blocked_by_disconnect(url, disconnect_blocklist) else False
        url_result["ghostery"] = True if ghostery_blocklist.check_host_in_list(url) else False

        result.append(url_result)

    return result
