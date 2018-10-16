README


== Pcaps related ==

auto-copy-pcap-to-cs.py: Automatically copies files to CS and deletes copied files.

dumpcap.sh: Captures packets and saves them to disk in 100 MByte chunks



== IP table related ==

reset_routing.sh: Removes routes for mitmproxy; sets up routes for wireless hotspot. You run this script when you want to disable mitmproxy and enable the wireless hotspot feature on the rasp pi.

set-up-routing.sh: Sets up routes for mitmproxy.


== MITMproxy related ==

start-mitm.sh: Starts mitmproxy. Buggy.

tls_passthrough.py: A mitmproxy module that dynamically whitelist domains if they were associated with failed TLS handshakes previously. Buggy; adapted from mitmproxy's repo. Uses RedisSet (from redis_set.py) to remember which domains to whitelist on a global level.

mitmproxy-sslstrip.py: Downgrades HTTPS to HTTP. Buggy; adapted from mitmproxy's repo.
