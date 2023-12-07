from dataclasses import dataclass

@dataclass
class ArpRTSPScanResult:
    """Scan results from different phases:
    - arp-scan
    - RTSP OPTIONS probe
    - TODO: RTSP DESCRIBE probe with provided user and passwd
    """
    interface: str = None # interface name
    mac: str = None # mac address
    ip: str = None # ip address
    port: int = None # rtsp port with successfull RTSP OPTIONS probe
    success: bool = False

    def __str__(self):
        return (
            f"ArpRTSPScanResult(interface={self.interface}, "
            f"mac={self.mac}, ip={self.ip}, port={self.port}, success={self.success})"
        )

