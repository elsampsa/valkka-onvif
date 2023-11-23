from valkka.discovery import runWSDiscovery, runARPScan
from valkka.onvif.multiprocess import OnvifProcess
from valkka.discovery import Onvif, Camera


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
    for ip, camera in cams:
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

            
def N3_GetStreamURIs(cams: dict, width: int = 1920, encodings: list = ["H264"]):
    """For all cameras that have their onvif connection allright, try to 
    update the initial rtsp uri using onvif calls
    """
    p = OnvifProcess()
    pipe = p.getPipe() # returns a custom Duplex instance
    fd=pipe.getReadFd() # this can be used with select.select
    p.start()
    cc=0
    for ip, camera in cams.items():
        if camera.onvif:
            p.register(
                address = camera.ip,
                port = camera.onvif.port,
                user = camera.user,
                password = camera.password,
                slot = cc
            )    
            cc+=1
    # query for tails
    for i in p.cache.keys(): # aka slot numbers
        p.getTails(slot, max_width=width, encodings = encodings)
    for slot, message in p.iterateResponses("tails"):
        ip = p.cache[slot]["address"]
        cams[ip].onvif.stream_tail=message["value"]
        # update original stream uri to optimal one:
        cams[ip].uri+="/"+message["value"]
    """ # TODO
    # query for image tails
    for i in p.cache.keys(): # aka slot numbers
        p.getImageTail(slot)
    for slot, message in p.iterateResponses("imageTail"):
        ip = p.cache[slot]["address"]
        cams[ip].onvif.image_tail=message["value"]
    """
    p.stop()

def printCams(cams):
    for ip, cam in cams.items():
        print(cam)


def run(user="admin", password="123456"):
    """Find cameras with wsdiscovery.  Test onvif connection to all cameras found:
    """
    cams = N1_WSDiscovery(user=user, password=password)
    print("CAMERAS AFTER N1")
    printCams(cams)
    
    """Do arp-scan and rtsp describe probe to all arp found ip addresses excluding current cams
    For all cams found this way, an onvif-probe performed, i.e. test onvif connection to several possible
    onvif ports:
    """
    N2_ArpScan(cams)
    print("CAMERAS AFTER N2")
    printCams(cams)

    """Run over all cameras, for the ones with OK onvif connection, try finding optimal stream URI
    and also the static image URI
    """
    N3_GetStreamURIs(cams)
    print("CAMERAS AFTER N3")
    printCams(cams)


if __name__ == "__main__":
    run()
