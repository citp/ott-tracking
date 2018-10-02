import re
import json
import utils

class GhosteryListParser:

    def __init__(self, bugs_file=None, bug_db=None, categorical_blocking=False):
        if bugs_file is None:
            bugs = bug_db
        else:
            with open(bugs_file) as f:
                bugs = json.load(f)
        regexes = bugs['patterns']['regex']
        for bugid in regexes:
            regex = regexes[bugid]
            regexes[bugid] = re.compile(regex, re.IGNORECASE)
        self.bugs = bugs
        self.categorical_blocking = categorical_blocking
        self.categories_classes = utils.get_categories_classes(bugs)

    def get_num_classes(self):
        if self.categorical_blocking:
            return len(self.categories_classes)
        else:
            return 2

    def get_classes_description(self):
        if self.categorical_blocking:
            description = [None]*self.get_num_classes()
            for category in self.categories_classes:
                description[self.categories_classes[category]] = category
            return description
        else:
            return ['NotBlocked', 'Blocked']

    def should_block(self, url, options=None):
        bug_id = self._should_block_bug_id(url, options)

        if bug_id is not None and int(bug_id):
            return True
        else:
            return False

    def get_block_class(self, url, options=None):
        bug_id = self._should_block_bug_id(url, options)
        if int(bug_id):
            if self.categorical_blocking:
                return self.categories_classes[utils._get_category(self.bugs, utils._get_app_id(self.bugs, bug_id))]
            else:
                return 1
        else:
            return 0

    def should_block_with_items(self, url, options=None):
        top_url = ''
        if options:
            top_url = options['top_url']
        url_protocol, url_host, url_path, url, anchor, url_cleaned = self._process_url(url)

        bug_ids_host_path = self._get_blocked_bug_ids_host(self.bugs['patterns']['host_path'], url_host, url_path)
        bug_ids_host = self._get_blocked_bug_ids_host(self.bugs['patterns']['host'], url_host)
        bug_ids_path = self._get_blocked_bug_ids_path(url_path)
        bug_ids_regex = self._get_blocked_bug_ids_regex(url)
        bug_ids = bug_ids_host_path + bug_ids_host + bug_ids_path + bug_ids_regex
        final_bug_ids = []
        for bug_id in bug_ids:
            bug_id = str(bug_id)
            if bug_id in self.bugs['firstPartyExceptions'] and \
                    self._fuzzy_url_match(top_url, self.bugs['firstPartyExceptions'][bug_id]):
                return False, []
            elif int(bug_id):
                final_bug_ids.append(bug_id)
        if len(final_bug_ids) == 0:
            return False, []
        else:
            return True, final_bug_ids

    def get_block_class_with_items(self, url, options=None):
        block, bug_ids = self.should_block_with_items(url, options)
        if len(bug_ids) > 0:
            bug_id = bug_ids[0]
            if self.categorical_blocking:
                return self.categories_classes[utils._get_category(self.bugs, utils._get_app_id(self.bugs, bug_id))], bug_ids
            else:
                return 1, bug_ids
        else:
            return 0, []

    def get_bug_db(self):
        return self.bugs

    @staticmethod
    def get_all_items(bugs_file):
        with open(bugs_file) as f:
            bugs = json.load(f)
        bugs = bugs['bugs']
        bug_ids = []
        for bug_id in bugs:
            bug_ids.append(bug_id)
        return bug_ids

    def _process_url(self, url):
        index = url.find('#')
        if index >= 0:
            anchor = url[index+1]
            url = url[:index]
        else:
            anchor = ''

        index = url.find('?')
        if index >= 0:
            url = url[:index]

        url_cleaned = url

        index_http = url.find('http://')
        index_https = url.find('https://')
        index_relative = url.find('//')
        url_protocol = ''
        if index_http == 0:
            url_protocol = url[:4]
            url = url[7:]
        elif index_https == 0:
            url_protocol = url[:5]
            url = url[8:]
        elif index_relative == 0:
            url_protocol = ''
            url = url[2:]

        url = url.lower()

        index_1 = url.find('/')
        index_2 = url.find('@')

        if index_2 >= 0 and (index_1 == -1 or index_2 < index_1):
            url = url[(index_2+1):]
            index_1 = url.find('/')

        if index_1 >= 0:
            url_host = url[:index_1]
            url_path = url[(index_1+1):]
        else:
            url_host = url
            url_path = ''

        index = url_host.find(':')
        if index >= 0:
            url_host = url_host[:index]

        return url_protocol, url_host, url_path, url, anchor, url_cleaned


    def _matches_host_path(self, dict_nodes, path):
        for dict_node in dict_nodes:
            if '$' in dict_node:
                dict_paths = dict_node['$']
                for dict_path in dict_paths:
                    if path.find(dict_path['path']) == 0:
                        return dict_path['id']
        return None


    def _matches_host(self, dict_node, host, path=None):
        host_rev_array = host.split('.')
        host_rev_array.reverse()
        bug_id = None
        dict_nodes_with_paths = []

        for host_part in host_rev_array:
            if host_part in dict_node:
                dict_node = dict_node[host_part]
                if '$' in dict_node:
                    bug_id = dict_node['$']
                    if path is not None:
                        dict_nodes_with_paths.append(dict_node)
            else:
                if path is not None:
                    return self._matches_host_path(dict_nodes_with_paths, path)
                return bug_id
        if path is not None:
            return self._matches_host_path(dict_nodes_with_paths, path)
        return bug_id


    def _matches_path(self, path):
        dict_paths = self.bugs['patterns']['path']
        path = '/' + path
        for dict_path in dict_paths:
            if path.find(dict_path) >= 0:
                return dict_paths[dict_path]
        return None

    def _matches_regex(self, url):
        regexes = self.bugs['patterns']['regex']
        for bug_id in regexes:
            if regexes[bug_id].search(url):
                return int(bug_id)
        return None

    def _fuzzy_url_match(self, url, checking_urls):
        url_protocol, url_host, url_path, url, anchor, url_cleaned = self._process_url(url)
        if url_host.find('www.') == 0:
            url_host = url_host[4:]

        for checking_url in checking_urls:
            checking_url_protocol, checking_url_host, checking_url_path, \
            checking_url, checking_anchor, checking_url_cleaned = self._process_url(checking_url)
            if checking_url_host != url_host:
                continue
            if not checking_url_path or checking_url_path == '':
                return True
            if checking_url_path[-1:] == '*':
                if url_path.find(checking_url_path[0:-1]) == 0:
                    return True
            else:
                if checking_url_path == url_path:
                    return True

    def _should_block_bug_id(self, url, options=None):
        top_url = ''
        if options:
            top_url = options['top_url']
        url_protocol, url_host, url_path, url, anchor, url_cleaned = self._process_url(url)

        bug_host_path = self._matches_host(self.bugs['patterns']['host_path'], url_host, url_path)
        bug_host = self._matches_host(self.bugs['patterns']['host'], url_host)
        bug_path = self._matches_path(url_path)
        bug_regex = self._matches_regex(url)

        bug_id = bug_host_path or bug_host or bug_path or bug_regex
        if bug_id:
            bug_id = str(bug_id)
            if bug_id in self.bugs['firstPartyExceptions'] and \
                    self._fuzzy_url_match(top_url, self.bugs['firstPartyExceptions'][bug_id]):
                return None
            else:
                return bug_id
        else:
            return None

    def _get_blocked_bug_ids_host_path(self, dict_nodes, path):
        bug_ids = []
        for dict_node in dict_nodes:
            if '$' in dict_node:
                dict_paths = dict_node['$']
                for dict_path in dict_paths:
                    if path.find(dict_path['path']) == 0:
                        bug_ids.append(dict_path['id'])
        return bug_ids

    def _get_blocked_bug_ids_host(self, dict_node, host, path=None):
        host_rev_array = host.split('.')
        host_rev_array.reverse()
        bug_ids = []
        dict_nodes_with_paths = []

        for host_part in host_rev_array:
            if host_part in dict_node:
                dict_node = dict_node[host_part]
                if '$' in dict_node:
                    bug_ids.append(dict_node['$'])
                    if path is not None:
                        dict_nodes_with_paths.append(dict_node)
            else:
                if path is not None:
                    return self._get_blocked_bug_ids_host_path(dict_nodes_with_paths, path)
                return bug_ids
        if path is not None:
            return self._get_blocked_bug_ids_host_path(dict_nodes_with_paths, path)
        return bug_ids

    def _get_blocked_bug_ids_path(self, path):
        bug_ids = []
        dict_paths = self.bugs['patterns']['path']
        path = '/' + path
        for dict_path in dict_paths:
            if path.find(dict_path) >= 0:
                bug_ids.append(dict_paths[dict_path])
        return bug_ids

    def _get_blocked_bug_ids_regex(self, url):
        bug_ids = []
        regexes = self.bugs['patterns']['regex']
        for bug_id in regexes:
            if regexes[bug_id].search(url):
                bug_ids.append(int(bug_id))
        return bug_ids
