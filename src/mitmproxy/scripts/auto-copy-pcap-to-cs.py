#!/usr/bin/python

"""
Automatically copies pcap files to cs server.

"""
import subprocess
import os
import time


def run(cmd, wait=False, return_stdout=True):
    """Runs some linux command."""

    if return_stdout:
        p = subprocess.Popen(cmd, shell=isinstance(cmd, basestring), stdout=subprocess.PIPE)
    else:
        p = subprocess.Popen(cmd, shell=isinstance(cmd, basestring))

    if wait:
        return p.communicate()[0]


def main():

    while True:
        
        # Constantly copying files
        print 'Copying files.'
        run(
            '/usr/bin/rsync -zv --progress /root/*.pcap yuxingh@wash.cs.princeton.edu:/n/fs/iot-house/public_html/pcaps/roku-tv/',
            wait=True, return_stdout=False
        )
        
        # Delete all pcaps except the latest 5
        file_list = run('ls -t /root/*.pcap', wait=True)
        for (ix, file_name) in enumerate(file_list.split()):
            if ix > 5:
                print 'Removing file:', file_name
                os.remove(file_name)

        time.sleep(10)
        

if __name__ == '__main__':
    main()

