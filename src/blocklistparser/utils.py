import json, pprint, random


# read into a bug_db from the blacklist file
def read_bug_db(bugs_file):
    with open(bugs_file) as f:
        bug_db = json.load(f)
    f.close()
    return bug_db


# write the bug_db in the blacklist file
def write_bug_db(bug_db, bugs_file):
    with open(bugs_file, 'w') as f:
        json.dump(bug_db, f)
    f.close()


# get the app_id given the bug_id
def get_app_information(bug_db, bug_id):
    bug_id = str(bug_id)
    bugs = bug_db['bugs']
    app_id = None
    if bug_id in bugs and 'aid' in bugs[bug_id]:
        app_id = bugs[bug_id]['aid']
    if app_id is not None:
        app_id = str(app_id)
        apps = bug_db['apps']
        if app_id in apps:
            return apps[app_id]
    return None


# get categories count
def get_categories_classes(bug_db):
    bugs = bug_db
    apps = bugs['apps']
    categories_classes = {}
    categories_classes['NotBlocked'] = 0
    num_classes = 1
    for app_id in apps:
        app_info = apps[app_id]
        cat = app_info['cat']
        if cat not in categories_classes:
            categories_classes[cat] = num_classes
            num_classes += 1
    return categories_classes


# print all the categories present in the bug_db
def print_all_categories(bug_db):
    bugs = bug_db
    apps = bugs['apps']
    categories = {}
    names = {}
    count = 0
    for app_id in apps:
        count += 1
        app_info = apps[app_id]
        name = app_info['name']
        cat = app_info['cat']
        if name in names:
            names[name] += 1
        else:
            names[name] = 1
        if cat in categories:
            categories[cat] += 1
        else:
            categories[cat] = 1
    print ("Number of apps", count)
    print ("Number of distinct names", len(names))
    print ("Number of distinct categories", len(categories))

    for cat in categories:
        print (cat, categories[cat])


# ******************************** Stripping the bug db based on categories you want ********************************

# get the category given the app_id
def _get_category(bug_db, app_id):
    app_id = str(app_id)
    apps = bug_db['apps']
    if app_id in apps and 'cat' in apps[app_id]:
        return apps[app_id]['cat']
    else:
        return None

# get the app_id given the bug_id
def _get_app_id(bug_db, bug_id):
    bug_id = str(bug_id)
    bugs = bug_db['bugs']
    if bug_id in bugs and 'aid' in bugs[bug_id]:
        return bugs[bug_id]['aid']
    else:
        return None

# strip the host_path dict based on the given categories
def _get_stripped_host_path_dict(bug_db, dict_node, categories):
    final_dict_node = {}
    for key in dict_node:
        if '$' == key:
            final_list = []
            for dict_path in dict_node[key]:
                bug_id = dict_path['id']
                app_id = _get_app_id(bug_db, bug_id)
                if _get_category(bug_db, app_id) in categories:
                    final_list.append(dict_path)
            if len(final_list) > 0:
                final_dict_node[key] = final_list
        else:
            recursive_stripped_dict = _get_stripped_host_path_dict(bug_db, dict_node[key], categories)
            if len(recursive_stripped_dict) > 0:
                final_dict_node[key] = recursive_stripped_dict
    return final_dict_node


# strip the host dict based on given categories
def _get_stripped_host_dict(bug_db, dict_node, categories):
    final_dict_node = {}
    for key in dict_node:
        if '$' == key:
            bug_id = dict_node[key]
            app_id = _get_app_id(bug_db, bug_id)
            if _get_category(bug_db, app_id) in categories:
                final_dict_node[key] = dict_node[key]
        else:
            recursive_stripped_dict = _get_stripped_host_dict(bug_db, dict_node[key], categories)
            if len(recursive_stripped_dict) > 0:
                final_dict_node[key] = recursive_stripped_dict
    return final_dict_node

# strip the bug_db based on categories
def get_stripped_bug_db(bug_db, categories):
    apps = bug_db['apps']
    bugs = bug_db['bugs']
    first_party_exceptions = bug_db['firstPartyExceptions']
    patterns = bug_db['patterns']
    regex = patterns['regex']
    host_path = patterns['host_path']
    host = patterns['host']
    path = patterns['path']

    final_apps = {}
    for app_id in apps:
        if _get_category(bug_db, app_id) in categories:
            final_apps[app_id] = apps[app_id]

    final_bugs = {}
    for bug_id in bugs:
        app_id = _get_app_id(bug_db, bug_id)
        if _get_category(bug_db, app_id) in categories:
            final_bugs[bug_id] = bugs[bug_id]

    final_first_party_exceptions = {}
    for bug_id in first_party_exceptions:
        app_id = _get_app_id(bug_db, bug_id)
        if _get_category(bug_db, app_id) in categories:
            final_first_party_exceptions[bug_id] = first_party_exceptions[bug_id]

    final_regex = {}
    for bug_id in regex:
        app_id = _get_app_id(bug_db, bug_id)
        if _get_category(bug_db, app_id) in categories:
            final_regex[bug_id] = regex[bug_id]

    final_host_path = _get_stripped_host_path_dict(bug_db, host_path, categories)
    final_host = _get_stripped_host_dict(bug_db, host, categories)

    final_path = {}
    for p in path:
        bug_id = path[p]
        app_id = _get_app_id(bug_db, bug_id)
        if _get_category(bug_db, app_id) in categories:
            final_path[p] = path[p]

    final_patterns = {}
    final_patterns['regex'] = final_regex
    final_patterns['host_path'] = final_host_path
    final_patterns['host'] = final_host
    final_patterns['path'] = final_path

    final_bug_db = {}
    final_bug_db['apps'] = final_apps
    final_bug_db['bugs'] = final_bugs
    final_bug_db['firstPartyExceptions'] = final_first_party_exceptions
    final_bug_db['patterns'] = final_patterns

    return final_bug_db

# ************************************************************************************************


# ******************************** Get counts of different dicts in bug db ********************************
# get the count of bug_ids for host_path dict
def _get_count_host_path_dict(dict_node):
    final_count = 0
    final_dict_node = {}
    for key in dict_node:
        if '$' == key:
            for dict_path in dict_node[key]:
                final_count += 1
                bug_id = dict_path['id']
        else:
            final_count += _get_count_host_path_dict(dict_node[key])
    return final_count


# get the count of bug_ids for host dict
def _get_count_host_dict(dict_node):
    final_count = 0
    for key in dict_node:
        if '$' == key:
            final_count += 1
        else:
            final_count += _get_count_host_dict(dict_node[key])
    return final_count


# get the count for regexes
def _get_count_regex(dict_node):
    final_count = 0
    for bug_id in dict_node:
        final_count += 1
    return final_count


# get the count for paths dict
def _get_count_path(dict_node):
    final_count = 0
    for p in dict_node:
        final_count += 1
    return final_count


# get the number of first party exceptions
def _get_count_firstPartyExceptions(dict_node):
    final_count = 0
    for bug_id in dict_node:
        final_count += len(dict_node[bug_id])
    return final_count

def get_count_host_path_dict(bug_db):
    return _get_count_host_path_dict(bug_db['patterns']['host_path'])


def get_count_host_dict(bug_db):
    return _get_count_host_dict(bug_db['patterns']['host'])


def get_count_regex(bug_db):
    return _get_count_regex(bug_db['patterns']['regex'])


def get_count_path(bug_db):
    return _get_count_path(bug_db['patterns']['path'])


def get_count_firstPartyExceptions(bug_db):
    return _get_count_firstPartyExceptions(bug_db['firstPartyExceptions'])

# ************************************************************************************************


# ******************************** Replacing bugids with 0 for shortening the blacklist ********************************
# replace bugids with 0's for host_path dict based on the index set which contains indices of bugids to be turned 0
# where indices are numbered from 0 to the number of bugids in this dict
def _replace_bugid_with_zeros_host_path_dict(dict_node, index_set, cur_count):
    for key in dict_node:
        if '$' == key:
            for dict_path in dict_node[key]:
                if cur_count in index_set:
                    dict_path['id'] = 0
                cur_count += 1
        else:
            _replace_bugid_with_zeros_host_path_dict(dict_node[key], index_set, cur_count)
            cur_count += _get_count_host_path_dict(dict_node[key])


# replace bugids with 0's for host dict based on the index set which contains indices of bugids to be turned 0
# where indices are numbered from 0 to the number of bugids in this dict
def _replace_bugid_with_zeros_host_dict(dict_node, index_set, cur_count):
    for key in dict_node:
        if '$' == key:
            if cur_count in index_set:
                dict_node[key] = 0
        else:
            _replace_bugid_with_zeros_host_dict(dict_node[key], index_set, cur_count)
            cur_count += _get_count_host_dict(dict_node[key])


# replace bugids with 0's for path dict based on the index set which contains indices of bugids to be turned 0
# where indices are numbered from 0 to the number of bugids in this dict
def _replace_bugid_with_zeros_path(dict_node, index_set, cur_count):
    for p in dict_node:
        if cur_count in index_set:
            dict_node[p] = 0
        cur_count += 1


# replace bugids with 0's for regexes dict based on the index set which contains indices of bugids to be turned 0
# where indices are numbered from 0 to the number of bugids in this dict
def _replace_bugid_with_zeros_regex(dict_node, index_set, cur_count):
    for bug_id in dict_node:
        if cur_count in index_set:
            dict_node[bug_id] = "////////////////"
        cur_count += 1


# replace bugids with 0's for first party exceptions dict based on the index set which contains indices of bugids to be turned 0
# where indices are numbered from 0 to the number of bugids in this dict
def _replace_bugid_with_zeros_firstPartyExceptions(dict_node, index_set, cur_count):
    for bug_id in dict_node:
        temp_list = []
        for exception in dict_node[bug_id]:
            if cur_count not in index_set:
                temp_list.append(exception)
            cur_count += 1
        dict_node[bug_id] = temp_list

def replace_bugid_with_zeros_host_path_dict(bug_db, ratio):
    count = get_count_host_path_dict(bug_db)
    num_zeros = int(ratio*count)
    indices = random.sample(range(count), num_zeros)
    _replace_bugid_with_zeros_host_path_dict(bug_db['patterns']['host_path'], set(indices), 0)


def replace_bugid_with_zeros_host_dict(bug_db, ratio):
    count = get_count_host_dict(bug_db)
    num_zeros = int(ratio*count)
    indices = random.sample(range(count), num_zeros)
    _replace_bugid_with_zeros_host_dict(bug_db['patterns']['host'], set(indices), 0)


def replace_bugid_with_zeros_path(bug_db, ratio):
    count = get_count_path(bug_db)
    num_zeros = int(ratio*count)
    indices = random.sample(range(count), num_zeros)
    _replace_bugid_with_zeros_path(bug_db['patterns']['path'], set(indices), 0)


def replace_bugid_with_zeros_regex(bug_db, ratio):
    count = get_count_regex(bug_db)
    num_zeros = int(ratio*count)
    indices = random.sample(range(count), num_zeros)
    _replace_bugid_with_zeros_regex(bug_db['patterns']['regex'], set(indices), 0)


def replace_bugid_with_zeros_firstPartyExceptions(bug_db, ratio):
    count = get_count_firstPartyExceptions(bug_db)
    num_zeros = int(ratio*count)
    indices = random.sample(range(count), num_zeros)
    _replace_bugid_with_zeros_firstPartyExceptions(bug_db['firstPartyExceptions'], set(indices), 0)


def write_shorten_ghostery_list(blacklist_file, ratio, output_file):
    bug_db = read_bug_db(blacklist_file)
    replace_bugid_with_zeros_host_path_dict(bug_db, 1 - ratio)
    replace_bugid_with_zeros_host_dict(bug_db, 1 - ratio)
    replace_bugid_with_zeros_path(bug_db, 1 - ratio)
    replace_bugid_with_zeros_regex(bug_db, 1 - ratio)
    replace_bugid_with_zeros_firstPartyExceptions(bug_db, 1 - ratio)
    write_bug_db(bug_db, output_file)
# ************************************************************************************************

# ******************************** Rule thresholding the bug db based on item ratio map ********************************

# threshold the host_path dict based on the given item ratio map
def _get_thresholded_host_path_dict(bug_db, dict_node, ratio, item_ratio_map):
    final_dict_node = {}
    for key in dict_node:
        if '$' == key:
            final_list = []
            for dict_path in dict_node[key]:
                bug_id = dict_path['id']
                if str(bug_id) not in item_ratio_map or item_ratio_map[str(bug_id)] <= ratio:
                    final_list.append(dict_path)
            if len(final_list) > 0:
                final_dict_node[key] = final_list
        else:
            recursive_thresholded_dict = _get_thresholded_host_path_dict(bug_db, dict_node[key], ratio, item_ratio_map)
            if len(recursive_thresholded_dict) > 0:
                final_dict_node[key] = recursive_thresholded_dict
    return final_dict_node


# strip the host dict based on given categories
def _get_thresholded_host_dict(bug_db, dict_node, ratio, item_ratio_map):
    final_dict_node = {}
    for key in dict_node:
        if '$' == key:
            bug_id = dict_node[key]
            if str(bug_id) not in item_ratio_map or item_ratio_map[str(bug_id)] <= ratio:
                final_dict_node[key] = dict_node[key]
        else:
            recursive_thresholded_dict = _get_thresholded_host_dict(bug_db, dict_node[key], ratio, item_ratio_map)
            if len(recursive_thresholded_dict) > 0:
                final_dict_node[key] = recursive_thresholded_dict
    return final_dict_node

# strip the bug_db based on categories
def _get_thresholded_bug_db(bug_db, ratio, item_ratio_map):
    apps = bug_db['apps']
    bugs = bug_db['bugs']
    first_party_exceptions = bug_db['firstPartyExceptions']
    patterns = bug_db['patterns']
    regex = patterns['regex']
    host_path = patterns['host_path']
    host = patterns['host']
    path = patterns['path']

    final_apps = apps

    final_bugs = {}
    for bug_id in bugs:
        if str(bug_id) not in item_ratio_map or item_ratio_map[str(bug_id)] <= ratio:
            final_bugs[bug_id] = bugs[bug_id]

    final_first_party_exceptions = {}
    for bug_id in first_party_exceptions:
        if str(bug_id) not in item_ratio_map or item_ratio_map[str(bug_id)] <= ratio:
            final_first_party_exceptions[bug_id] = first_party_exceptions[bug_id]

    final_regex = {}
    for bug_id in regex:
        if str(bug_id) not in item_ratio_map or item_ratio_map[str(bug_id)] <= ratio:
            final_regex[bug_id] = regex[bug_id]

    final_host_path = _get_thresholded_host_path_dict(bug_db, host_path, ratio, item_ratio_map)
    final_host = _get_thresholded_host_dict(bug_db, host, ratio, item_ratio_map)

    final_path = {}
    for p in path:
        bug_id = path[p]
        if str(bug_id) not in item_ratio_map or item_ratio_map[str(bug_id)] <= ratio:
            final_path[p] = path[p]

    final_patterns = {}
    final_patterns['regex'] = final_regex
    final_patterns['host_path'] = final_host_path
    final_patterns['host'] = final_host
    final_patterns['path'] = final_path

    final_bug_db = {}
    final_bug_db['apps'] = final_apps
    final_bug_db['bugs'] = final_bugs
    final_bug_db['firstPartyExceptions'] = final_first_party_exceptions
    final_bug_db['patterns'] = final_patterns

    return final_bug_db

def write_thresholded_ghostery_list(blacklist_file, ratio, item_ratio_map, output_file_name):
    bug_db = _get_thresholded_bug_db(read_bug_db(blacklist_file), ratio, item_ratio_map)
    write_bug_db(bug_db, output_file_name)

# ************************************************************************************************


# sample test function which can be used
def test():
    bugs_file_prefix = '../../blacklists/bugs'
    bug_db = read_bug_db(bugs_file_prefix + '.json')

    bugs_file_analytics_prefix = bugs_file_prefix + '_analytics'
    bugs_file_widget_prefix = bugs_file_prefix + '_widget'
    bugs_file_tracker_prefix = bugs_file_prefix + '_tracker'
    bugs_file_ad_prefix = bugs_file_prefix + '_ad'
    bugs_file_privacy_prefix = bugs_file_prefix + '_privacy'

    # write_bug_db(get_stripped_bug_db(bug_db, ['analytics']), bugs_file_analytics_prefix + '.json')
    # write_bug_db(get_stripped_bug_db(bug_db, ['widget']), bugs_file_widget_prefix + '.json')
    # write_bug_db(get_stripped_bug_db(bug_db, ['tracker']), bugs_file_tracker_prefix + '.json')
    # write_bug_db(get_stripped_bug_db(bug_db, ['ad']), bugs_file_ad_prefix + '.json')
    # write_bug_db(get_stripped_bug_db(bug_db, ['privacy']), bugs_file_privacy_prefix + '.json')

    print("Number of rules in host_path dict", get_count_host_path_dict(bug_db))
    print("Number of rules in host dict", get_count_host_dict(bug_db))
    print("Number of rules in regex dict", get_count_regex(bug_db))
    print("Number of rules in path dict", get_count_path(bug_db))
    print("Number of first party exceptions", get_count_firstPartyExceptions(bug_db))

    write_shorten_ghostery_list(bugs_file_prefix + '.json', 0.8, bugs_file_prefix + '_shortened.json')
    bug_db = read_bug_db(bugs_file_prefix + '_shortened.json')

    print("Number of rules in host_path dict", get_count_host_path_dict(bug_db))
    print("Number of rules in host dict", get_count_host_dict(bug_db))
    print("Number of rules in regex dict", get_count_regex(bug_db))
    print("Number of rules in path dict", get_count_path(bug_db))
    print("Number of first party exceptions", get_count_firstPartyExceptions(bug_db))

