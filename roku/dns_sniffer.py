from __future__ import print_function
import redis
import sys
from scapy.all import *

interface = "wlan0"
Name2IPDic = {}
IP2NameDic = {}

rName2IPDic = redis.StrictRedis(host='localhost', port=6379, db=0)
rName2IPDic.flushdb()
rIP2NameDic = redis.StrictRedis(host='localhost', port=6379, db=1)
rIP2NameDic.flushdb()



'''
try:
    interface = raw_input("[*] Enter Desired Interface: ")
except KeyboardInterrupt:
    print "[*] User Requested Shutdown..."
    print "[*] Exiting..."
    sys.exit(1)
'''

def querysniff(pkt):
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
                        DomainName = str(p.qd.qname)
                        IPAddr = str(p[DNSRR][x].rdata)
                        if not DomainName in Name2IPDic:
                            Name2IPDic[DomainName] = set()
                        Name2IPDic[DomainName].add(IPAddr)
                        rName2IPDic.set(DomainName, Name2IPDic[DomainName])

                        if not IPAddr in IP2NameDic:
                            IP2NameDic[IPAddr] = set()
                        IP2NameDic[IPAddr].add(DomainName)
                        rIP2NameDic.set(IPAddr, IP2NameDic[IPAddr])

                        print(DomainName + " IP:" + IPAddr + ":" + str(p[DNSRR][x].type))
                    #name = p.an.rdata
                    #print(name)

sniff(iface = interface,filter = "port 53", prn = querysniff, store = 0)
