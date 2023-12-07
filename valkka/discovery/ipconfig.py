import re
from subprocess import check_output, CalledProcessError

__interfaces__ = None # singleton
__arp__ = None # singleton


def parse_ip_address_output(output) -> dict:
    """Sample output:
    
    ::
    
        {'br-2ad50d95054a': {'attributes': 'NO-CARRIER,BROADCAST,MULTICAST,UP',
                         'subnets': [('172.19.0.1', '16')]},
         'br-2cddc3bcd5fe': {'attributes': 'NO-CARRIER,BROADCAST,MULTICAST,UP',
                             'subnets': [('172.23.0.1', '16')]},
         'br-5100bab9ac22': {'attributes': 'NO-CARRIER,BROADCAST,MULTICAST,UP',
                             'subnets': [('172.24.0.1', '16')]},
         'br-52b32b08932e': {'attributes': 'NO-CARRIER,BROADCAST,MULTICAST,UP',
                             'subnets': [('172.20.0.1', '16')]},
         'br-7d96055bc7ee': {'attributes': 'NO-CARRIER,BROADCAST,MULTICAST,UP',
                             'subnets': [('172.18.0.1', '16')]},
         'docker0': {'attributes': 'NO-CARRIER,BROADCAST,MULTICAST,UP',
                     'subnets': [('172.17.0.1', '16')]},
         'enx4865ee147a39': {'attributes': 'BROADCAST,MULTICAST,UP,LOWER_UP',
                             'subnets': []},
         'lo': {'attributes': 'LOOPBACK,UP,LOWER_UP', 'subnets': [('127.0.0.1', '8')]},
         'wlp2s0': {'attributes': 'BROADCAST,MULTICAST,UP,LOWER_UP',
                    'subnets': [('192.168.1.135', '24')]}}
    
    P. S. Thanks chat-gpt!
    """
    interfaces = {}
    current_interface = None

    for line in output.splitlines():
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Check if it's a new interface line
        if line[0].isdigit():
            parts = line.split(": ")
            interface_name = parts[1].split()[0]
            current_interface = interface_name
            interfaces[current_interface] = {'subnets': [], 'attributes': ''}
            attributes = re.findall(r'<([^>]+)>', line)[0]
            interfaces[current_interface]['attributes'] = attributes

        
        # Check for subnets information within the interface
        elif line.startswith('inet '):
            if current_interface is not None:
                subnet_info = re.findall(r'inet ([\d.]+)/(\d+)', line)
                for subnet, mask in subnet_info:
                    interfaces[current_interface]['subnets'].append((subnet, mask))

    return interfaces


def getInterfaces_() -> dict:
    """Returns all 'normal' interfaces (excluding NO-CARRIER and LOOPBACK interfaces)
    
    Example output:
    
    ::
    
        {'wlp2s0': [('192.168.1.135', '24')], 'enx4865ee147a39': []}
    
    """
    try:
        ip_output = check_output(['ip', 'address'], universal_newlines=True)
        interfaces = parse_ip_address_output(ip_output)
        # pprint(interfaces)
    except CalledProcessError as e:
        print(f"Error executing 'ip address' command: {e}")
        return {}
    
    dic={}
    for name, interface in interfaces.items():
        # print(">",name, interface["attributes"])
        if "NO-CARRIER" not in interface["attributes"] and "LOOPBACK" not in interface["attributes"]:
            # print(name, interface["subnets"])
            dic[name] = interface["subnets"]
    return dic


def getInterfaces(update=False) -> dict:
    global __interfaces__
    if (__interfaces__ is None) or update:
        # print(">>refreshing interfaces")
        __interfaces__ = getInterfaces_()
    return __interfaces__


def getARPCache(update=False) -> dict:
    global __arp__
    if (__arp__ is None) or update:
        __arp__ = {}
        # print(">>refreshing arp-cache")
        for i, line in enumerate(check_output(['arp'], universal_newlines=True).split("\n")):
            if i<1:
                continue
            # print(line)
            cols=line.split()
            if len(cols) >= 4:
                # print(cols)
                ip = cols[0]
                mac = cols[2]
                # print(ip, mac)
                __arp__[ip] = mac
            """
            Address                  HWtype  HWaddress           Flags Mask            Iface
            192.168.1.18             ether   c2:52:5f:72:94:94   C                     wlp2s0
            axis-accc8ec97bc8.local          (incomplete)                              wlp2s0
            """
    else:
        return __arp__

getInterfaces()
getARPCache()

if __name__ == "__main__":
    getARPCache()





