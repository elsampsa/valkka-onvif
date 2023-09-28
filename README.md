# Valkka Onvif

Onvif dependencies for libValkka.

For more information, see [here](https://elsampsa.github.io/valkka-examples/_build/html/onvif.html)

## Install

From pypi with:
```
pip install valkka-onvif
```

## Test studio

You can play around with onvif using either ipython cli client or jupyter notebook:
```
cd examples
ipython3
%run studio.py
```
Check that out and develop further in [examples/studio.py](examples/studio.py)

## Work in progress

A multiprocess, running an asynchronous multiprocessing backend for onvif calls in [here](valkka/onvif/multiprocess/base.py)

## Author & Copyright

(c) 2023 Sampsa Riikonen

Contains code from the WSDiscovery package: please see directory [valkka/discovery/wsdiscovery/](valkka/discovery/wsdiscovery/)

## License

MIT 

For WSDiscovery, LGPL, see please see directory [valkka/discovery/wsdiscovery/](valkka/discovery/wsdiscovery/)

