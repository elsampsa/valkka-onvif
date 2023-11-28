from valkka.discovery import runWSDiscovery, runARPScan
from valkka.onvif.multiprocess import OnvifProcess
from valkka.discovery.camsearch.datatype import Onvif, Camera
import logging


def OnvifSearch(ips, test_ports = (80, 8000, 8080, 2020), user = "admin", password = "123456") -> list:
    """Tests onvif connection for a list of ip addresses and for a set of port numbers

    :par ips: list of ip addresses
    :par test_ports: list of onvif ports to be tested

    Returns a list of (ip, onvif_port) values for valid onvif connections
    """
    p = OnvifProcess()
    pipe = p.getPipe() # returns a custom Duplex instance
    fd=pipe.getReadFd() # this can be used with select.select
    p.start()

    test_ip_port_list = [] # create a list of (ip_address, port) tuples
    for ip in ips:
        for onvif_port in test_ports:
            test_ip_port_list.append((ip, onvif_port))
    # register a set of ip-addresses + tentative port numbers
    cc=0
    for ip, port in test_ip_port_list:
        p.register(
            address = ip,
            port = port,
            user = user, # input par
            password = password, # input par
            slot = cc
        )
        cc+=1
    # test all that
    for slot, camera in p.cache.items():
        p.testOnvif(slot=slot)
    # search for succesfull onvif tests
    result = []
    for slot, message in p.iterateResponses("OnvifStatus"):
        ok = message["All"] # status of all relevant/basic onvif services
        ip = p.cache[slot]["address"]
        onvif_port = p.cache[slot]["port"]
        if ok:
            result.append((ip, onvif_port))
    p.stop()
    return result


def OnvifTest(cams: dict):
    """Test onvif connection for a set of cameras.  Update camera objects accordingly:
    If onvif connection is OK, then set camera.onvif = Onvif()

    :par cams: a dictionary with key: ip, value: Camera object
    """
    p = OnvifProcess()
    pipe = p.getPipe() # returns a custom Duplex instance
    fd=pipe.getReadFd() # this can be used with select.select
    p.start()
    cc=0
    for ip, camera in cams.items():
        if camera.onvif_port:
            p.register(
                address = camera.ip,
                port = camera.onvif_port,
                user = camera.user,
                password = camera.password,
                slot = cc
            )
            cc+=1
    # test all that
    for slot in p.cache.keys():
        p.testOnvif(slot=slot)
    # search for succesfull onvif tests
    result = []
    for slot, message in p.iterateResponses("OnvifStatus"):
        ok = message["All"] # status of all relevant/basic onvif services
        ip = p.cache[slot]["address"]
        if ok:
            cams[ip].onvif = Onvif() # setting this member means that onvif connection is OK
        else:
            cams.pop(ip) # remove the camera .. let arp-scan try to do the work for it
    p.stop()


def N1_WSDiscovery(user="admin", password="123456") -> dict:
    """Initial WSDiscovery

    Returns dictionary with key: ip address, value: Camera object
    """
    cams = {}
    for ip, onvif_port in runWSDiscovery(): # list of (ip, onvif-port) tuples
        cams[ip] = Camera(
                ip = ip,
                user = user,
                password = password,
                # set default rtsp uri
                uri=f"rtsp://{user}:{password}@{ip}:554",
                onvif_port = onvif_port
            )
    # check onvif connections
    OnvifTest(cams) # now some of them have .onvif member set to OnVif()
    return cams


def N2_ArpScan(cams: dict, user="admin", password="123456"):
    """Append camera's with arp and rtsp describe scan

    :par cams: key: ip address, value: Camera object
    """
    ips = []
    for ip, rtsp_port in runARPScan(exclude_list=list(cams.keys())):
        # print("arp>", ip)
        ips.append(ip)
        cams[ip] = Camera(
            ip = ip,
            user = user,
            password = password,
            uri = f"rtsp://{user}:{password}@{ip}:{rtsp_port}"
        )
    for ip, onvif_port in OnvifSearch(ips): # tries onvif ports and test connection on them
        if ip in cams:
            cams[ip].onvif_port = onvif_port
            cams[ip].onvif = Onvif()

            
def N3_GetStreamURIs(cams: dict, width: int = 1920, encodings: list = None):
    """For all cameras that have their onvif connection allright, try to 
    update the initial rtsp uri using onvif calls

    :param encodings: a list of acceptable codec values, for example: ["h264"]
    """
    p = OnvifProcess()
    # p.formatLogger(logging.DEBUG)
    pipe = p.getPipe() # returns a custom Duplex instance
    fd=pipe.getReadFd() # this can be used with select.select
    p.start()
    cc=0
    for ip, camera in cams.items():
        if camera.onvif:
            p.register(
                address = camera.ip,
                port = camera.onvif_port,
                user = camera.user,
                password = camera.password,
                slot = cc
            )    
            cc+=1
    # query for tails
    for slot in p.cache.keys(): # aka slot numbers
        p.getTails(slot, max_width=width, encodings = encodings)
    for slot, message in p.iterateResponses("tails"):
        ip = p.cache[slot]["address"]
        cams[ip].onvif.streams=message["value"] # NOTE: this is a list of dicts
        """keys: enc, port, tail, width, height, snapshot_port, snapshot_tail
        """
        # update original stream uri to optimal one:
        el = message["value"][0]
        rtsp_port = el["port"]
        tail = "/"+el["tail"]
        cam = cams[ip]
        # update stream uri
        cams[ip].uri=f"rtsp://{cam.user}:{cam.password}@{cam.ip}:{rtsp_port}{tail}"

        if el["snapshot_tail"] and el["snapshot_port"]:
            tail = "/" + el["snapshot_tail"]
            port = el["snapshot_port"]
            cams[ip].snapshot_uri=f"http://{cam.ip}:{port}{tail}" 
    p.stop()

def printCams(cams):
    for ip, cam in cams.items():
        print(cam)
        print()


def run(user="admin", password="123456", encodings=None, width=1920) -> list:
    """Returns a list of Camera objects
    """
    """1. Find cameras with wsdiscovery.  Test onvif connection to all cameras found:
    """
    cams = N1_WSDiscovery(user=user, password=password)
    print("CAMERAS AFTER N1")
    printCams(cams)
    print()
    
    """2. Do arp-scan and rtsp describe probe to all arp found ip addresses excluding current cams
    For all cams found this way, an onvif-probe performed, i.e. test onvif connection to several possible
    onvif ports:
    """
    N2_ArpScan(cams)
    print("CAMERAS AFTER N2")
    printCams(cams)
    print()

    """3. Run over all cameras, for the ones with OK onvif connection, try finding optimal stream URI
    and also the static image URI
    """
    N3_GetStreamURIs(cams, width=width, encodings=encodings)
    print("CAMERAS AFTER N3")
    printCams(cams)


if __name__ == "__main__":
    run()
