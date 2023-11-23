from multiprocessing import Event
from valkka.multiprocess import AsyncBackMessageProcess, MessageObject, EventGroup, SyncIndex, exclogmsg
from valkka.onvif import OnVif, getWSDLPath, DeviceManagement, Media
import asyncio, logging, traceback
import yaml
import re
from pprint import pprint, pformat


class Namespace:
    pass


class OnvifProcess(AsyncBackMessageProcess):

    def __init__(self, name = "onvif"):
        super().__init__(name=name)
        # print(">>", self.logger)
        self.cache = {}
        """{
            1 : { # indexed by the slot number
                "address" : "192.168.10.1",
                "user" : "admin",
                "password" : "12345",
            },
            2 : { ... }

        }"""
        self.event_group = EventGroup(10, Event) # create 10 multiprocessing.Event instances

    async def asyncPre__(self):
        pass


    async def asyncPost__(self):
        pass

    @exclogmsg
    async def c__register(self, address: str = None, port: int = 80, user: str = None, 
        password: str = None, slot: int = None, event_index = None):
        services = Namespace()
        services.device = DeviceManagement(
            ip          = address,
            port        = port,
            user        = user,
            password    = password,
            use_async   = True
            )
        services.media = Media(
            ip          = address,
            port        = port,
            user        = user,
            password    = password,
            use_async   = True
            )
        self.cache[slot] = {
            "address" : address,
            "user" : user,
            "port" : port,
            "password" : password,
            "services" : services
        }
        # let's take the object factory from the first registered service.devices:
        self.f = services.device.zeep_client.type_factory("http://www.onvif.org/ver10/schema")
        self.event_group.set(event_index)


    async def c__deRegister(self, slot: int = None):
        self.cache.pop(slot)
        self.event_group.set(event_index)


    def tailFromUri(self, uri):
        # print(f"uri >{uri}<")
        # p = "\/\/[^\/]+\/(.+)" # i.e. get "/media/video3" from "rtsp://10.0.0.4/media/video3" # OLD
        # uri="rtsp://10.0.0.4:80/media/video3"
        p = "\/\/([^\/]*)\/(.*)"
        match = re.search(p, uri) # group 1: ip-addr:port, group 2: tail
        # print(match, match.group(1))
        if match:
            ip_port = match.group(1)
            if len(ip_port.split(":")) > 1:
                ip, port = ip_port.split(":")
                port = int(port)
            else:
                ip = ip_port
                # port = None
                port=554 # better use the default port..
            tail = match.group(2)
            # print("> tail, port", tail, port)
            # await self.send_out__(MessageObject("tail", slot=slot, value=tail, port=port))
            return port, tail
        else:
            self.logger.warning("tailFromUri : Could not extract tail from %s", uri)
            # await self.send_out__(MessageObject("tail", slot=slot, value=None, port=None))
            return None, None


    @exclogmsg
    async def getTails__(self, slot: int = None, max_width = 1920, encodings: list = None):
        f=self.f # shorthand
        services = self.cache[slot]["services"]
        Profiles = await services.media.ws_client.GetProfiles()
        # search for media profiles that use H264 encoding and whose
        # width is <= max_width
        # token = None # profile token
        # width = 0
        # enc_name = None # name of the encoder profile
        lis = []
        for Profile in Profiles:
            width_ = Profile.VideoEncoderConfiguration.Resolution.Width
            height_ = Profile.VideoEncoderConfiguration.Resolution.Height
            self.logger.debug("c__getTails : slot %s -> profile token: %s, width: %s", slot, Profile.token, width_)
            enc = Profile.VideoEncoderConfiguration.Encoding # i.e. 'H264'
            if width_ <= max_width:
                if encodings and enc not in encodings:
                    continue
                #if width_ > width:
                # self.logger.debug("c__getTails : slot %s -> found better width %s", slot, width_)
                self.logger.debug("c__getTails : slot %s -> found width %s", slot, width_)
                # width = width_
                token = Profile.token
                name = Profile.VideoEncoderConfiguration.Name
                StreamSetup=f.StreamSetup( 
                    Stream = f.StreamType(0), 
                    Transport = f.Transport( 
                        Protocol = f.TransportProtocol(1) 
                    ) 
                )
                res=await services.media.ws_client.GetStreamUri(StreamSetup, token)
                port, tail = self.tailFromUri(res.Uri)
                if tail is not None:
                    self.logger.debug("c__getTails : slot %s append profile with width %s", slot, width_)
                    lis.append({
                        "slot": slot,
                        "enc": "H264",
                        "port": port,
                        "tail": tail,
                        "width": width_,
                        "height": height_
                    })
        await self.send_out__(MessageObject("tails", value=lis))

        """
        if not token:
            self.logger.warning("c__getTails : No suitable H264 media profile found for slot %s.  Current width: %s, enc: %s", slot, width, enc)
            # return
            await self.send_out__(MessageObject("tail", slot=slot, value=None, port=None))
            return

        StreamSetup=f.StreamSetup( 
            Stream = f.StreamType(0), 
            Transport = f.Transport( 
                Protocol = f.TransportProtocol(1) 
            ) 
        )
        """
        
    async def c__getTails(self, slot: int = None, max_width = 1920, encodings: list = None):
        asyncio.get_event_loop().create_task(self.getTails__(slot=slot, max_width=max_width, encodings = encodings))


    @exclogmsg
    async def testOnvif__(self, slot: int):
        services = self.cache[slot]["services"]
        status = {
            "slot" : slot,
            "DeviceManagement" : True,
            "Media" : True,
            "All" : True
        }
        res = await asyncio.gather(
            services.device.ws_client.GetServices(False),
            services.media.ws_client.GetProfiles(),
            return_exceptions=True
        )
        if issubclass(res[0].__class__, BaseException):
            status["DeviceManagement"] = False
            status["All"] = False
            self.logger.warning("c__testOnvif: DeviceManagement Service failed for slot %i with %s", slot, res[0])
        if issubclass(res[1].__class__, BaseException):
            status["Media"] = False
            status["All"] = False
            self.logger.warning("c__testOnvif: Media Service failed for slot %i with %s", slot, res[1])
        await self.send_out__(MessageObject("OnvifStatus", **status))


    async def c__testOnvif(self, slot: int):
        asyncio.get_event_loop().create_task(self.testOnvif__(slot=slot))



    # **** FRONTEND ******


    def register(self, address: str = None, port: int = 80, user: str = None, 
        password: str = None, slot: int = None):
        with SyncIndex(self.event_group) as i:
            assert(isinstance(address, str))
            assert(isinstance(port, int))
            assert(isinstance(user, str))
            assert(isinstance(password, str))
            assert(isinstance(slot, int))
            
            if slot in self.cache:
                self.logger.warning("slot %s already registered\
                    with %s - will skip", slot, self.cache[slot]["address"])
                return False
            
            self.cache[slot] = {
                "address" : address,
                "user" : user,
                "port" : port,
                "password" : password
            }

            self.sendMessageToBack(MessageObject(
                "register", address=address, port = port, user=user,
                password = password, slot = slot, event_index = i))


    def deRegister(self, slot: int):
        with SyncIndex(self.event_group) as i:
            assert(isinstance(slot, int))
            if slot not in self.cache:
                self.logger.warning("deRegister: slot %s not registered - will skip",
                    slot)
                return

            self.cache.pop(slot)
            self.sendMessageToBack(MessageObject(
                "deRegister", slot = slot, event_index = i))


    def iterateResponses(self, ex_message = "OnvifStatus"):
        """Returns an iterator over all response messages coming from the
        multiprocessing backend.  Messages that are not of the
        expected type, are disregarded

        :par ex_message: expected message type
        """
        pipe_ = self.getPipe()
        for i in range(len(self.cache)):
            message=pipe_.recv()
            if message() != ex_message:
                self.logger.warning("iterateResponses: got unexpected message type %s", message())
                continue
            slot=message["slot"]
            yield slot, message


    def has_slot__(self, slot: int):
        if slot not in self.cache:
            self.logger.warning("getProfiles: slot %s not registered - will skip",
                slot)
            return False
        return True

    def testOnvif(self, slot: int):
        if not self.has_slot__(slot): return
        self.sendMessageToBack(MessageObject(
            "testOnvif", slot = slot))


    def getTails(self, slot: int, max_width = 1920, encodings: list = None):
        if not self.has_slot__(slot): return
        self.sendMessageToBack(MessageObject(
            "getTails", slot = slot, max_width = max_width, encodings = encodings))
    


def test1():
    import time
    p = OnvifProcess()
    pipe = p.getPipe() # returns a custom Duplex instance
    fd=pipe.getReadFd() # this can be used with select.select
    p.start()
    """
    p.register(
        address = "10.0.0.2",
        user = "root",
        password = "silopassword",
        slot = 1
    )
    """
    #"""
    p.register(
        address="10.0.0.4",
        user="admin",
        password="123456",
        slot = 1
    )
    #"""
    p.testOnvif(slot=1)
    print("got>",pipe.recv())
    time.sleep(1)
    p.getTails(slot=1, max_width=1920)
    time.sleep(1)
    print("got>",pipe.recv())
    p.stop()


def test2():
    import copy
    from valkka.discovery import runWSDiscovery, runARPScan

    user="admin"
    password="123456"

    addresses = runWSDiscovery() 
    # list of (ip, port), where port is the onvif port

    print("WSDiscovery returned", addresses)

    p = OnvifProcess()
    pipe = p.getPipe() # returns a custom Duplex instance
    fd=pipe.getReadFd() # this can be used with select.select
    p.start()

    print("registering")
    cc=1
    for ip, port in addresses:
        p.register(
            address = ip,
            user = user,
            port = port,
            password = password,
            slot = cc
        )
        cc+=1

    print("test onvif connections")
    # test all onvif connections in parallel
    for slot, camera in p.cache.items():
        p.testOnvif(slot=slot)

    # read results
    ok_slots = []
    for i in range(len(p.cache)):
        message=pipe.recv()
        if message() != "OnvifStatus":
            continue
        slot=message["slot"] # int
        ok=message["All"] # boolean
        if ok:
            ok_slots.append(slot)

    print("slots with ok onvif:", ok_slots)
    # p.stop(); return

    # request probing the availability of H264
    # and get their "tails" if possible
    for slot in ok_slots:
        p.getTails(slot)

    # read results
    good_streams = {} # key: ipv4 address, value: rtsp address (with rtsp://,tail,etc.)
    for slot in ok_slots:
        message=pipe.recv()
        if message() != "tail":
            continue # one of the getTails requests didn't work out
        if message["value"]:
            tail = message["value"] # we got the tail!
            port = message["port"]
            if port is None:
                port = 554
            print("got tail", tail)
            ip = p.cache[slot]['address']
            rtsp_adr = f"rtsp://{user}:{password}@{ip}:{port}/{tail}"
            good_streams[ip] = rtsp_adr

    p.stop()

    arp_list = runARPScan(exclude_list=good_streams.keys())
    print("arp scan returned", arp_list)
    for ip, port in arp_list:
        rtsp_adr=f"rtsp://{user}:{password}@{ip}:{port}"
        good_streams[ip] = rtsp_adr
    
    for ip, rtsp in good_streams.items():
        print(rtsp)


if __name__ == "__main__":
    # test1()
    test2()
