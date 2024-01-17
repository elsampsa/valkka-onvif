"""base.py : Discovery module for onvif cameras, using wsdiscovery and brute-force scan

Copyright 2017-2019 Valkka Security Ltd. and Sampsa Riikonen.

Authors: Sampsa Riikonen (sampsa.riikonen@iki.fi)

This particular file, referred below as "Software", is licensed under the MIT LICENSE:

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom
the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE 
AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, 
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

@file    base.py
@author  Sampsa Riikonen
@date    2019
@version 1.6.6 

@brief   Discovery module for onvif cameras, using wsdiscovery and brute-force scan
"""
# from multiprocessing import Process, Manager
# from dataclasses import dataclass
import sys, time
# import signal
# import os, errno, select
import inspect
import asyncio
import re
import traceback
import pty

from valkka.discovery.wsdiscovery import WSDiscovery, QName, Scope
from valkka.discovery.ipconfig import getInterfaces
from valkka.discovery.probe import probe
from valkka.discovery.arp import runARPScan_

"""
- Run WSDiscovery
- For each discovered device, poke port 554 with an RTSP OPTIONS request
- ..but do that in parallel, using asyncio
- For each found IP camera, try a few user & password combos
- In fact, no need to do that brute-force port 554 scan if we filter
  ws-discovery results having /onvif/ in the device list
"""

def runWSDiscovery() -> list:
    """Returns a list of tuples (ip, port)
    """
    reg = "^http:\/\/([^\/]*)\/onvif"
    wsd = WSDiscovery()
    wsd.start()
    ws_devices = wsd.searchServices()
    ip_addresses = []
    for ws_device in ws_devices:
        for http_address in ws_device.getXAddrs():
            # print(">>", http_address)
            match = re.search(reg, http_address)
            if match is None:
                continue
            else:
                # print(match)
                ip_port = match.group(1)
                if len(ip_port.split(":")) > 1:
                    ip, port = ip_port.split(":")
                    port = int(port)
                else:
                    ip = ip_port
                    port = 80
                ip_addresses.append((ip, port))

        """ws_device.
        getXAddrs
            returns a list like this:
            ['http://192.168.1.57/onvif/device_service', 'http://[fe8d::8ef7:48ee:feed:a84d]/onvif/device_service']

        getEPR
        getInstanceId
        getMessageNumber
        getMetadataVersion
        getScopes
        getTypes
        """
    wsd.stop()
    return ip_addresses


"""
def getMacIPMap(exclude_interfaces = [], max_time_per_interface=10, verbose=False) -> dict:
    #Returns a dictionary (mapping) from mac to IP addresses
    #
    #This works also as discovery (i.e. we use "arp-scan" instead of plain "arp")
    lis = runARPScan_(exclude_interfaces = exclude_interfaces, max_time_per_interface = max_time_per_interface, verbose = verbose)
    dic = {}
    for res in lis:
        dic[res.mac]=res.ip
    return dic
"""

def runARPScan(exclude_list = [], exclude_interfaces = [], max_time_per_interface=10, verbose=False, return_all=False, return_always=[]) -> list:
    """brute-force port 554 & 8554 scan & RTSP OPTIONS test ping in parallel

    Returns a list of (ip, port) tuples, where "ip" is ip address and port is the port

    :param exclude_list: ip addresses to be exluded
    :param exclude_interfaces: interfaces to be excluded from the scan
    :param max_time_per_interface: (int) how many secs to be spent max in each interface (default: 10)

    quicktest:

    ::

        python3 -c "from valkka.discovery import runARPScan; print(runARPScan(verbose=False))"


    TODO: we want:
    all devices found by arp-scan, succesfull rtsp devices with their port number set to correct value

    """
    lis=runARPScan_(exclude_interfaces = [], max_time_per_interface=10, verbose=False)
    if len(lis) < 1:
        return []
    #for l in lis:
    #    print(">>>", l)

    # order by ip address
    arp_scan_results_by_ip = {}
    for arp_scan_result in lis:
        arp_scan_results_by_ip[arp_scan_result.ip] = arp_scan_result

    coros = [probe(ip, 554) for ip in arp_scan_results_by_ip.keys()]
    coros += [probe(ip, 8554) for ip in arp_scan_results_by_ip.keys()]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    finished, unfinished = asyncio.get_event_loop().run_until_complete(
        asyncio.wait(coros)
    )

    # results = [] # list of (ip, port) tuples
    for task in finished:
        result = task.result()
        if result is not None:
            ip, port = result
            arp_scan_results_by_ip[ip].port = port

    # filter out failed probes, excluded ip addresses, etc.
    lis2 = []
    for res in lis.copy():
        if res.ip in exclude_list:
            continue
        if ((res.port) or (return_all) or (res.ip in return_always)):
            lis2.append(res)

    loop.close()
    return lis2 # list of ArpRTSPScanResult objects


if __name__ == "__main__":
    """
    results = runARPScan()
    for res in results:
        print(res)
    """
    pass

