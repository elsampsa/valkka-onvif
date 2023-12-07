Example on how to use the API:

```python
from valkka.onvif import OnvifProcess

p = OnvifProcess()
p.start() # start multiprocess

# register cameras
p.register(
    address = "192.168.1.12"
    port = 80,
    user = "admin"
    password = "123456",
    slot = 0
)
p.register(
    address = "192.168.1.13"
    ...
    slot=1
)
# register more cameras

# test onvif connection to all cameras in parallel
for slot, camera in p.cache.items():
    p.testOnvif(slot=slot)
    
# collect results from the onvif connection test
result = []
for slot, message in p.iterateResponses("OnvifStatus"):
    ok = message["All"] # status of all relevant/basic onvif services
    ip = p.cache[slot]["address"]
    onvif_port = p.cache[slot]["port"]
    if ok:
        result.append((ip, onvif_port)) # collect results into a list
p.stop() # stop the multiprocess
```
