from valkka.onvif import DeviceManagement, Media

class Namespace:
    pass

address="10.0.0.4"
port=80
user="admin"
password="123456"

services = Namespace()
services.device = DeviceManagement(
    ip          = address,
    port        = port,
    user        = user,
    password    = password
)
services.media = Media(
    ip          = address,
    port        = port,
    user        = user,
    password    = password
)
f = services.device.zeep_client.type_factory("http://www.onvif.org/ver10/schema")

print("""
Use factory object f to create variables, for example: 

    StreamSetup=f.StreamSetup( 
        Stream = f.StreamType(0), 
        Transport = f.Transport( 
            Protocol = f.TransportProtocol(1) 
        ) 
    )

Then use services.device.ws_client and services.media.ws_client objects to make calls, for example:

    Profiles = services.media.ws_client.GetProfiles()
    ProfileToken = Profiles[0].token

    services.media.ws_client.GetStreamUri(StreamSetup, ProfileToken)


""")

