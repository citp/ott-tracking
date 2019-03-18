from __future__ import print_function
import redis
import os
import sys
import subprocess
from scapy.all import *
from datetime import datetime


def querysniff(pkt):
    global Name2IPDic, IP2NameDic, rName2IPDic, rIP2NameDic
    if IP in pkt:
        ip_src = pkt[IP].src
        ip_dst = pkt[IP].dst
        if pkt.haslayer(DNS) and pkt.getlayer(DNS).qr == 1:
            p = pkt.getlayer(DNS)
            #print str(ip_src) + " -> " + str(ip_dst) + " : " + "(" + pkt.getlayer(DNS).qd.qname + ")"
            if isinstance(p.an, DNSRR):
                for x in range(p.ancount):
                    # Check A and AAAA records
                    if p[DNSRR][x].type == 1 or p[DNSRR][x].type == 28:
                        DomainName = (p.qd.qname).decode("utf-8")
                        IPAddr = p[DNSRR][x].rdata
                        if not DomainName in Name2IPDic:
                            Name2IPDic[DomainName] = set()
                        Name2IPDic[DomainName].add(IPAddr)
                        rName2IPDic.sadd(DomainName, IPAddr)
                        if not IPAddr in IP2NameDic:
                            IP2NameDic[IPAddr] = set()
                        IP2NameDic[IPAddr].add(DomainName)
                        rIP2NameDic.set(IPAddr, DomainName)
                        timestamp = '[{}] '.format(datetime.today())
                        print(timestamp + DomainName + " mapped to IP address " + IPAddr + ":" + str(p[DNSRR][x].type))
                    #name = p.an.rdata
                    #print(name)


def clear_dns_cache():
    print("Clearing DNS cache")
    plat = subprocess.check_output(['uname', '-a']).decode("utf-8")
    if 'Ubuntu' in plat:
        cmd = "sudo systemd-resolve --flush-caches"
        p = subprocess.Popen(cmd, shell=True)


def dns_sniffer_call(interface, hostIP=None):
    global Name2IPDic, IP2NameDic, rName2IPDic, rIP2NameDic
    clear_dns_cache()
    Name2IPDic = {}
    IP2NameDic = {}

    rName2IPDic = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
    rName2IPDic.flushdb()
    rIP2NameDic = redis.StrictRedis(host='localhost', port=6379, db=1, charset="utf-8", decode_responses=True)
    rIP2NameDic.flushdb()



    '''
    try:
        interface = raw_input("[*] Enter Desired Interface: ")
    except KeyboardInterrupt:
        print "[*] User Requested Shutdown..."
        print "[*] Exiting..."
        sys.exit(1)
    '''

    sniff_filter = "port 53"
    if hostIP is not None:
        sniff_filter = "host " + hostIP + " and " + sniff_filter

    print("Sniffing on " + str(interface) + " with filter : \"" + sniff_filter + "\"")

    sniff(iface = interface,filter = sniff_filter, prn = querysniff, store = 0)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        interface = str(sys.argv[1])
    else:
        interface = os.getenv('WLANIF', "wlan0")
    dns_sniffer_call(interface)
