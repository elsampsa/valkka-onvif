from pathlib import Path
from pprint import pprint
import copy, argparse, sys, os, yaml, logging
from valkka.discovery import runWSDiscovery, runARPScan
from valkka.onvif.multiprocess import OnvifProcess


def str2bool(val) -> bool:
    assert isinstance(val, str)
    if val.lower() in ["true","1"]:
        return True
    return False


def process_cl_args():
    comname = Path(sys.argv[0]).stem
    parser = argparse.ArgumentParser(
        usage=(
            f'{comname} [options]\n'
            '\n'
            'Searches for IP cameras using both WSDiscovery and also (optionally) a brute-force arp-scan'
            'When using WSDiscovery, tries also to do an ONVIF query for the camera rtsp address'
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        # ..shows default values with -h arg
    )
    parser.add_argument("--arp", action="store", help="perform an arp-scan", type=str2bool,
        default=True)
    parser.add_argument("--user", action="store", help="username to try", default="admin", type=str,
        required=False)
    parser.add_argument("--passwd", action="store", help="password to try", default="123456", type=str,
        required=False)
    parser.add_argument("--comm", action="store", help="(optional) launch a command (say, vlc) with the detected rtsp address", default=None, type=str,
        required=False)
    parser.add_argument("--csv", action="store", help="(optional) name of csv file to dump the results", default=None, type=str,
        required=False)    
    parser.add_argument("--yaml", action="store", help="(optional) name of valkka-streamer compatible yaml config file", default=None, type=str,
        required=False)
    parser.add_argument("--width", action="store", help="onvif search for stream profiles with this max. image width", default=7680, type=int,
        required=False)
    parser.add_argument("--debug", action="store_true", help="enable debugging output for OnvifProcess", default = False)
    parser.add_argument("--shutup", action="store_true", help="minimal output from OnvifProcess", default = False)
    parser.add_argument("--h264", action="store_true", help="Search only for H264 profiles", default = False)
    parsed, unparsed = parser.parse_known_args()
    for arg in unparsed:
        print("Unknow option", arg)
        sys.exit(2)
    return parsed


def confLogger(logger, level):
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers = []
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def main():
    pars = process_cl_args()
    if pars.debug:
        confLogger(logging.getLogger("OnvifProcess.onvif"), logging.DEBUG)
    elif pars.shutup:
        confLogger(logging.getLogger("OnvifProcess.onvif"), logging.CRITICAL)
    print("\nRUNNING WSDISCOVERY")
    ip_ports = runWSDiscovery() 
    # list of (ip, port), where port is the onvif port
    for ip, port in ip_ports:
        print(f'    ONVIF IP Address {ip}:{port}')

    p = OnvifProcess()
    pipe = p.getPipe() # returns a custom Duplex instance
    fd=pipe.getReadFd() # this can be used with select.select
    p.start()

    print("\nREGISTERING ONVIF ADDRESSES")
    cc=1
    for ip, port in ip_ports:
        p.register(
            address = ip,
            port = port,
            user = pars.user,
            password = pars.passwd,
            slot = cc
        )
        cc+=1

    print("\nTESTING ONVIF CONNECTIONS")
    # test all onvif connections in parallel
    for slot, camera in p.cache.items():
        p.testOnvif(slot=slot)

    # read results
    ok_slots = []
    for i in range(len(p.cache)):
        message=pipe.recv()
        if message() != "OnvifStatus":
            print(f"    FATAL: Got bad response '{message()}' from OnvifProcess")
            continue
        slot=message["slot"] # int
        ok=message["All"] # boolean # status of all relevant services
        ip = p.cache[slot]["address"]
        port = p.cache[slot]["port"]
        if ok:
            print(f'    Success for {ip}:{port}')
            ok_slots.append(slot)
        else:
            print(f'    WARNING: FAILED for {ip}:{port}')            

    # p.stop(); return

    print(f"\nSEARCHING RTSP ADDRESSES USING ONVIF FOR {len(ok_slots)} STREAM(S)")
    print("Looking for H264 profiles with max image width of", pars.width)

    # request probing the availability of H264
    # and get their "tails" if possible
    for slot in ok_slots:
        encodings = None
        if pars.h264:
            encodings = ["H264"]
        p.getTails(slot, max_width=pars.width, encodings = encodings)

    # read results
    good_streams = {} # key: ipv4 address, value: a list of {"rtsp" : rtsp address (with rtsp://,tail,etc.), "resolution" : (width, height), "encoding": "H264"}
    for slot in ok_slots:
        message=pipe.recv()
        onvif_ip = p.cache[slot]["address"]
        onvif_port = p.cache[slot]["port"]
        ip = p.cache[slot]['address']
        if message() != "tails":
            print(f"    FATAL: Got bad response '{message()}' from OnvifProcess for {onvif_ip}:{onvif_port}")
            continue
        # print(message)
        lis=message["value"]
        if len(lis) > 0:
            good_streams[ip] = []
            for dic in lis:
                tail = dic["tail"]
                enc = dic["enc"]
                port = dic["port"]
                resolution = (dic["width"], dic["height"])
                rtsp_adr = f"rtsp://{pars.user}:{pars.passwd}@{ip}:{port}/{tail}"
                good_streams[ip].append({
                    "rtsp": rtsp_adr,
                    "resolution": resolution,
                    "enc": enc
                })
            print(f"    Success for {onvif_ip}:{onvif_port} -> {rtsp_adr}")
        else:
            print(f"    WARNING: tail query failed for {onvif_ip}:{onvif_port}")

    # pprint(good_streams)
    p.stop()
    # return

    arp_streams={}
    if pars.arp:
        print(f"\nPERFORMING ARP-SCAN - EXCLUDING PREVIOUSLY SUCCESFULL {len(good_streams)} STREAM(S)")
        arp_list = runARPScan(exclude_list=good_streams.keys())
        # print("arp scan returned", arp_list)
        for ip, port in arp_list:
            rtsp_adr=f"rtsp://{pars.user}:{pars.passwd}@{ip}:{port}"
            arp_streams[ip] = rtsp_adr
            print(f"    found {rtsp_adr}")

    print("\n**** FINAL LIST OF RTSP ADDRESSES ****")
    print("\n---- from ONVIF & Guaranteed to work ----")
    for ip, lis in good_streams.items():
        print(f"{ip}")
        for dic in lis:
            width, height =dic["resolution"]
            print(f'    {dic["enc"]} stream {width}x{height} at {dic["rtsp"]}')

    if pars.arp:
        print("\n---- from ARP-SCAN ----------------------")
        for ip, rtsp in arp_streams.items():
            print(f"    {rtsp}")

    if pars.csv:
        print("\nWRITING CSV FILE", pars.csv)
        with open(pars.csv,"w") as f:
            cc=0
            for ip, lis in good_streams.items():
                for dic in lis:
                    width, height = dic["resolution"]
                    rtsp = dic["rtsp"]
                    enc = dic["enc"]
                    f.write(f'{cc}, ONVIF, {width}, {height}, {enc}, {rtsp}\n')
                    cc+=1
            if pars.arp:
                for ip, rtsp in arp_streams.items():
                    f.write(f'{cc}, ARP, ?, ?, ? {rtsp}\n')
                    cc+=1

    if pars.yaml:
        print("\nWRITING YAML FILE", pars.yaml)
        dic_yaml={}
        dic_yaml["streams"]=[]
        cc=0
        for ip, lis in good_streams.items():
            for dic in lis:
                width, height = dic["resolution"]
                rtsp = dic["rtsp"]
                enc = dic["enc"]
                dic_yaml["streams"].append({
                    "name" : f"cam{cc}",
                    "address" : rtsp,
                    "use" : True,
                    "discovered" : f"from onvif {width}x{height} {enc}"
                })
                cc+=1
        if pars.arp:
            for ip, rtsp in arp_streams.items():
                dic_yaml["streams"].append({
                "name" : f"cam{cc}",
                "address" : rtsp,
                "use" : True,
                "discovered" : "from arp"
                })
                cc+=1
        with open(pars.yaml,"w") as f:
            yaml.dump(dic_yaml, f, default_flow_style=False)

    if pars.comm:
        print("\nEXECUTING COMMAND", pars.comm, "FOR ALL STREAMS")
        for ip, lis in good_streams.items():
            for dic in lis[0:1]: # take just one stream
                rtsp=dic["rtsp"]
                comm=f"{pars.comm} {rtsp} &" # launch desired command in background
                print("executing", comm)
                os.system(comm)
        if pars.arp:
            for ip, rtsp in arp_streams.items():
                comm=f"{pars.comm} {rtsp} &" # launch desired command in background
                print("executing", comm)
                os.system(comm)

    print("\nbye!")


if __name__ == "__main__":
    main()
