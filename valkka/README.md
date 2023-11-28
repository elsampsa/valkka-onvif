
Files at a glance:
```
valkka/

    onvif/
        base.py
            defines the OnVif class (valkka.onvif.OnVif), uses the wsdl files (see below) and zeep SOAP client
            ready-made subclasses of valkka.onvif.OnVif: Media, Events, etc.
        wsdl/
            wsdl files defining the onvif SOAP service
        multiprocess/
            A multiprocess that uses OnVif classes asynchronously 

    discovery/

        base.py
            brute-force arp-scan & rtsp-describe implementation
            uses wsdiscovery (see below) to search onvif cameras

        wsdiscovery/
            a copy of the python-ws-discovery code

        camsearch/
            valkka-camsearch helper app: uses valkka.onvif and valkka.discovery modules
            base.py
            datatype.py
            cli.py
```
