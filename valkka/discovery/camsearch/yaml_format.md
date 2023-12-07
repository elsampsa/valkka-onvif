# valkka-camsearch yaml output

The produced yaml file lists information on all cameras found.  Below interpretation of the results.

## 1. No onvif, no rtsp uri

```
- ip: 10.0.0.2
  mac: ac:cc:8e:c9:7b:c8
  onvif: null
  onvif_port: null
  password: '123456'
  uri: null
  user: admin
```
In this case, there is a camera that publishes itself using WSDiscovery, however ``onvif: null`` implies that onvif-connection could not be established.
This can be from several reasons: device doesn't respond to onvif due to wrong onvif username/password (or for some other reason) or the device doesn't support onvif at all, etc.

The device didn't neither respond to an rtsp options query, so there is no
uri one could try to get rtsp stream from

## 2. No onvif, but rtsp uri yes

```
- ip: 10.0.0.2
  mac: ac:cc:8e:c9:7b:c8
  onvif: null
  onvif_port: null
  password: '123456'
  uri: rtsp://admin:123456@10.0.0.2:554
  user: admin
```
Again, no onvif connection could be established.  However, the
rtsp options probe responded at port 554, so we have a **tentative**
uri ``rtsp://admin:123456@10.0.0.2:554``.

However, there is no guarantee that this uri would actually work (the provided username and password might be wrong)

## 3. Succesfull onvif

```
- ip: 10.0.0.8
  mac: 40:ed:00:e3:d3:e2
  onvif:
    streams:
    - enc: h264
      height: 1080
      port: 554
      snapshot_port: null
      snapshot_tail: null
      tail: stream1
      width: 1920
    - enc: h264
      height: 480
      port: 554
      snapshot_port: null
      snapshot_tail: null
      tail: stream2
      width: 640
  onvif_port: 2020
  password: '123456'
  uri: rtsp://admin:123456@10.0.0.8:554/stream1
  user: admin
```
``onvif`` and ``onvif_port`` now have something -> there was a
succesfull onvif connection.

The ``onvif/streams`` lists different streams offered by the camera,
according to the specifications defined in the cli arguments.  The first
one in the list is the best one.  

``snapshot_port`` and ``snaphost_tail`` are null which means that this device does not support camera image snapshot uris via onvif.

When ``onvif/streams`` has listed streams, an rtsp uri has been found
that is guaranteed to work: this is written into the ``uri`` argument
(``rtsp://admin:123456@10.0.0.8:554/stream1``)

## 4. All good

```
- ip: 10.0.0.4
  mac: 48:ea:63:41:4b:7d
  onvif:
    streams:
    - enc: h264
      height: 1080
      port: 554
      snapshot_port: 85
      snapshot_tail: images/snapshot.jpg
      tail: media/video1
      width: 1920
    - enc: h264
      height: 576
      port: 554
      snapshot_port: 85
      snapshot_tail: images/snapshot.jpg
      tail: media/video2
      width: 720
    - enc: h264
      height: 288
      port: 554
      snapshot_port: 85
      snapshot_tail: images/snapshot.jpg
      tail: media/video3
      width: 352
  onvif_port: 80
  password: '123456'
  uri: rtsp://admin:123456@10.0.0.4:554/media/video1
  user: admin
```

Like previous case, but now we also have addresses (tails) for requesting snapshot images
(``http://10.0.0.4:85/images/snapshot.jpg``).  Depending on your camera brand, doing HTTP GET
on these addresses, might work or hang forever.


