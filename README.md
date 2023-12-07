# Valkka Onvif

Onvif dependencies and camera discovery tools for libValkka.

For more information, see [here](https://elsampsa.github.io/valkka-examples/_build/html/onvif.html)

## Install

From pypi with:
```
pip install -U valkka-onvif
```

## Onvif Test Studio

You can play around with onvif using either ipython cli client or jupyter notebook:
```
cd examples
ipython3
%run studio.py
```
Check it out and develop further in [examples/studio.py](examples/studio.py)

## Discovery API

*work in progress*

Uses WSDiscovery, and linux ``arp`` and ``arp-scan`` programs.

In order to enable arp-scan-based tools, please give these commands:
```
sudo apt-get install arp-scan
sudo chmod u+s /usr/sbin/arp-scan
```

The API might still change and will be better documented in the future.  This is the state of play at the moment:
```python
from valkka.discovery import *

runWSDiscovery() 
# --> returns a list of tuples (ip, port)
runARPScan(exclude_list = [], exclude_interfaces = [], max_time_per_interface=10) 
# performs a combination of arp-scan and "rtsp options" probes
# --> returns a list of ArpRTSPScanResult objects
ARPIP2Mac(ip) 
# maps ip address to a mac address
# --> returns ArpRTSPScanResult object
# --> to get most recent ip address -> mac address mapping, you should run
getARPCache(update=True)
```
For ``ArpRTSPScanResult`` object, please see [valkka/discovery/datatype.py](valkka/discovery/datatype.py) in the source code.

WSDiscovery relies on the [python-ws-discovery](https://github.com/andreikop/python-ws-discovery) package.

Beware that some camera brands might work poorly with WSDiscovery, for example [TP-Link](https://github.com/andreikop/python-ws-discovery/issues/56).

## OnVif API

The API is explained in more detail in [here](https://elsampsa.github.io/valkka-examples/_build/html/onvif.html)

## OnVif Multiprocess

*work in progress*

A multiprocess for onvif calls is provided in [here](valkka/onvif/multiprocess/).  It can be used to send commands for a group of cameras, while all onvif requests are processed asynchronously, i.e. in non-blocking/parallel manner
(for more examples on how to use the multiprocess, please see the camera search program's [source code](valkka/discovery/camsearch/cli.py))

PTZ controls will be added at some stage.

## Camera search program

``valkka-camsearch`` uses a series of arp-scan(s), WSDiscovery and onvif trial connections to find as much information as possible on the IP
cameras available in your network and produce a yaml file report.

For more details on the output format, see [valkka/discovery/camsearch/yaml_format.md](valkka/discovery/camsearch/yaml_format.md)

To get started, try this:
```
valkka-camsearch -h
```

## Author & Copyright

(c) 2023 Sampsa Riikonen

Contains code from the [python-ws-discovery](https://github.com/andreikop/python-ws-discovery) package: please see directory [valkka/discovery/wsdiscovery/](valkka/discovery/wsdiscovery/)

## License

MIT 

For [python-ws-discovery](https://github.com/andreikop/python-ws-discovery), LGPL, see please see directory [valkka/discovery/wsdiscovery/](valkka/discovery/wsdiscovery/)


