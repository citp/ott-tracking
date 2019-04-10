from glob import glob
from os.path import join
import sys


def separate_pipelined_requests_in_dir(csv_dir, pattern="*.http.csv"):
    for csv_path in glob(join(csv_dir, pattern)):
        separate_pipelined_requests(csv_path)


def separate_pipelined_requests(csv_path):
    request_tuples = []
    n_lines = 0
    n_pipelined_reqs = 0
    for line in open(csv_path):
        n_lines += 1
        columns = line.rstrip().split("|")
        assert len(columns) == 8
        method = columns[3]
        url = columns[4]
        user_agent = columns[5]
        referrer = columns[6]
        cookie = columns[7]
        if "," not in method:  # no pipelining
            request_tuples.append(columns + ["False",])
            continue

        n_pipelined_reqs += 1
        pipeline_methods = method.split(",")
        pipeline_urls = url.split(",")
        pipeline_user_agents = user_agent.split(",")
        pipeline_referrers = referrer.split(",")
        pipeline_cookies = cookie.split(",")
        n_pipelined_reqs = len(pipeline_methods)
        assert len(pipeline_urls) == n_pipelined_reqs
        assert len(pipeline_user_agents) == n_pipelined_reqs
        if len(pipeline_referrers) and len(pipeline_referrers) < n_pipelined_reqs:
            print ("Missing referrers", n_pipelined_reqs, len(pipeline_referrers))
            for _ in xrange(n_pipelined_reqs):
                pipeline_referrers.insert(0, "")
        if len(pipeline_cookies) and len(pipeline_cookies) < n_pipelined_reqs:
            print ("Missing cookies", n_pipelined_reqs, len(pipeline_cookies))
            for _ in xrange(n_pipelined_reqs):
                pipeline_cookies.insert(0, "")

        for idx in range(n_pipelined_reqs):
            request_tuples.append(
                (columns[0], columns[1], columns[2],
                 pipeline_methods[idx], pipeline_methods[idx],
                 pipeline_urls[idx], pipeline_user_agents[idx],
                 pipeline_referrers[idx], pipeline_cookies[idx], "True"))

    new_csv_path = csv_path.replace("http.csv", "pipeline_separated_http.csv")
    with open(new_csv_path, "w") as f:
        for request_tuple in request_tuples:
            f.write("|".join(request_tuple) + "\n")
    print ("No of pipelined reqs: %d. No of total reqs: %d (%0.1f%%))" % (n_pipelined_reqs, n_lines,  100 * float(n_pipelined_reqs) / n_lines))


if __name__ == '__main__':
    separate_pipelined_requests_in_dir(sys.argv[1])

