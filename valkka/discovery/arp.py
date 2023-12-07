from subprocess import Popen, PIPE, check_output, CalledProcessError, STDOUT
from multiprocessing import Process, Manager
from valkka.discovery.ipconfig import getInterfaces, getARPCache
from valkka.discovery.datatype import ArpRTSPScanResult
import pty
import re, time, os, select, errno


def ARPIP2Mac(ip) -> ArpRTSPScanResult:
    """Given an ip address, returns ArpRTSPScanResult.  None if there was an error.  This version uses arp cache
    """
    res = ArpRTSPScanResult(ip=ip)
    res.mac = getARPCache().get(ip, None)
    return res


def ARPScanIP2Mac(ip) -> ArpRTSPScanResult:
    """Given an ip address, returns ArpRTSPScanResult.  None if there was an error.  This version uses arp-scan
    """
    #interface_pattern = re.compile(r'Interface: ([^,]+), type: (\S+), MAC: (\S+), IPv4: (\S+)')
    #ip_mac_pattern = re.compile(r'(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\s+([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})')
    
    res = ArpRTSPScanResult(ip=ip)
    for interface in getInterfaces().keys(): #  TODO: run getInterfaces only once when the module is loaded
        comst=f"arp-scan --plain {ip} --interface {interface}"
        print("comst>", comst)
        p = Popen(comst.split(),
            stdout=PIPE,
            stderr=PIPE,
            text=True  # Use text=True for text output (Python 3.7 and later)
        )

        # Wait for the process to finish and get the output
        stdout, stderr = p.communicate()

        # Check if the command was successful
        if p.returncode == 0:
            for line in stdout.split("\n"):
                # print(">>",line)
                # 10.0.0.3        48:ea:63:36:32:82       Zhejiang Uniview Technologies Co., Ltd.
                cols=line.split()
                if len(cols)>=2:
                    res.mac=cols[1]
                    return res
                """
                # Search for the pattern in the output
                match = interface_pattern.search(line)
                # Check if a match is found
                if match:
                    # interface_name = match.group(1)
                    #print("Interface found:", interface_name)
                    res.interface = match.group(1)
                m = ip_mac_pattern.match(line)
                if (m is None) or (m.lastindex != 2):
                        pass
                else:
                    # ip = m.group(1)
                    # mac = m.group(2)
                    #print("Mac found:", mac)
                    res.mac=m.group(2)
            return res
                """
        else:
            print(f"No arp-scan found: install with 'sudo apt-get install arp-scan'.  You also need extra rights to run it: 'sudo chmod u+s /usr/sbin/arp-scan'")
            return None
    return res


def ARPScanInterface(name, ip, iplen, lis, max_time_per_interface = 10, verbose=False):
    """Parallelizable arp-scan on a certain interface

    :param name: name of the interface
    :param ip: ip address
    :param iplen: ip mask
    :param max_time_per_interface: max time spent scanning on the interface in seconds
    :param lis: a common multiprocess-protected list where several processes can append
    :param verbose: (bool) be verbose or not

    Returns a list of ArpRTSPScanResult objects
    """
    ip_mac_pattern = re.compile(r'(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\s+([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})')
    # .. thanks chatgpt!
    comst = f"arp-scan -g -retry=2 --interface={name} {ip}/{iplen}" # e.g. eno1 192.168.30.149/24
    # verbose = True
    if verbose: print("ARPScanInterface: starting for", comst)
    stdout = ""
    # as per: https://stackoverflow.com/questions/12419198/python-subprocess-readlines-hangs
    # the ONLY way to read process output on-the-fly
    master_fd, slave_fd = pty.openpty()
    # signal.alarm(max_time_per_interface) # in secs
    try:
        proc = Popen(comst.split(), stdin=slave_fd, stdout=slave_fd, stderr=STDOUT, close_fds=True)
    except FileNotFoundError:
        print(f"No arp-scan found: install with 'sudo apt-get install arp-scan'.  You also need extra rights to run it: 'sudo chmod u+s /usr/sbin/arp-scan'")
        return []
    os.close(slave_fd)
    timecount = 0
    try:
        while 1:
            if timecount > max_time_per_interface:
                print(f"WARNING: arp-scan '{comst}' took more than {max_time_per_interface} secs - aborting")
                break        
            t0 = time.time()
            try:
                r, w, e = select.select([ master_fd ], [], [], 1)
                dt = time.time() - t0
                timecount += dt
                if verbose: print("timecount>", timecount)
                if master_fd in r:
                    data = os.read(master_fd, 512)
                else:
                    continue
            except OSError as e:
                if e.errno != errno.EIO:
                    raise
                break # EIO means EOF on some systems
            else:
                if not data: # EOF
                    break
                # if verbose: print('>' + repr(data))
                if verbose: print('>', data.decode("utf-8"))
                stdout += data.decode("utf-8")
    finally:
        os.close(master_fd)
        if proc.poll() is None:
            proc.kill()
        proc.wait()
    if proc.returncode > 0:
        print("arp-scan error:", stdout)
        print("You might need to grant extra rights with: 'sudo chmod u+s /usr/sbin/arp-scan'")
        return []

    lis_ = []
    for line in stdout.split("\n"):
        m = ip_mac_pattern.match(line)
        if (m is None) or (m.lastindex != 2):
                continue
        ip = m.group(1)
        mac = m.group(2)
        if verbose: print("ip, mac>", ip, mac)
        if verbose: print("ARPScanInterface: appending", ip)
        lis_.append(ArpRTSPScanResult(
            interface=name,
            mac=mac,
            ip=ip
        ))

    if verbose: print("ARPScanInterface: finished for", comst)

    if len(lis_) < 1:
        if verbose: print("ARPScanInterface: did not find anything")
    for l in lis_: # append to multiprocess-protected list
        lis.append(l)
    # return lis_


def runARPScan_(exclude_interfaces = [], max_time_per_interface=10, verbose=False) -> list:
    """Runs arp-scan in parallel over all found interfaces.  Returns a list of ArpRTSPScanResult objects
    """
    # verbose = True
    # verbose = False
    lis = [] # a list of ArpRTSPScanResult objects
    processes = []    
    with Manager() as manager:
        # Create a shared list
        shared_list = manager.list()
        for name, subnets in getInterfaces().items():
            if name in exclude_interfaces:
                continue
            # print("runARPScan: scanning interface", name)
            for ip, iplen in subnets:
                # print(name+" "+ip+"/"+iplen) # stdbuf -oL
                p = Process(target=ARPScanInterface, args=(
                    name, ip, iplen, shared_list, max_time_per_interface, verbose
                ))
                processes.append(p)
                p.start()
        for p in processes:
            p.join()
        for l in shared_list:
            lis.append(l)
    return lis

