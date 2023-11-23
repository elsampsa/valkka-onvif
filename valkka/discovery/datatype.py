from dataclasses import dataclass, fields

@dataclass
class Onvif:
    stream_tail: str = None # stream tail
    snapshot_tail: str = None # snapshot tail

@dataclass
class Camera:
    ip: str = None
    user: str = "admin"
    password: str = "123456"
    uri: str = None # complete rtsp uri # either default value of something optimal found by onvif
    snapshot_uri = None # complete snapshot uri (if avail)
    onvif_port: int = None # if set, implies that onvif connection port was found
    onvif: Onvif = None # if set, implies that the found onvif connection actually works

    def __str__(self):
        st=""
        for fname in ["ip", "user", "password", "uri", "snapshot_uri", "onvif_port"]:
            val = getattr(self, fname)
            if val is None:
                val = "<none>"
            # st+=f'{fname} : {val}\n'
            st += f"{fname.ljust(15)}: {val}\n"
        if self.onvif is None:
            st+="onvif".ljust(15)+": <none>\n"
        else:
            stream_tail = self.onvif.stream_tail if self.onvif.stream_tail is not None else "<none>"
            snapshot_tail = self.onvif.snapshot_tail if self.onvif.snapshot_tail is not None else "<none>"
            st+=f"onvif".ljust(15)+f": stream_tail: {stream_tail} snapshot_tail: {snapshot_tail}\n"
        return st

# Create an instance of Camera
# my_camera = Camera(uri='rtsp://example.com', onvif=Onvif())

if __name__ == "__main__":
    cam = Camera()
    print(cam)
    cam.onvif = Onvif(stream_tail="/kokkelis")
    print(cam)
