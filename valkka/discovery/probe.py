import re, asyncio, traceback


options_str = """OPTIONS rtsp://%s:%i RTSP/1.0\r
CSeq: 1\r
User-Agent: libValkka\r
\r
\r"""


def parse_http_resp(resp: str):
    reg = re.compile("(^\S*):(.*)")
    fields = resp.split("\r\n")
    output = {}
    for field in fields[1:]: # ignore "GET / HTTP/1.1" and the like
        try:
            m = reg.match(field)
            if m is None:
                continue
            key = field[m.start(1):m.end(1)]
            value = field[m.start(2):m.end(2)]
        except IndexError:
            continue
        else:
            output[key] = value
    return fields[0], output



async def probe(ip: str, port: int) -> tuple: # ip, port
    """Send an RTSP OPTIONS request to ip & port

    If succesfull, returns (ip, port), otherwise returns None
    """
    verbose = False
    # verbose = True
    timeout = 3

    if verbose:
        print("probe: trying", ip)
    writer = None
    ok = True # got a response to rtsp describe
    st = options_str % (ip, port)
    st_ = st.encode("utf-8")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout = timeout)
    except asyncio.TimeoutError:
        # traceback.print_exc()
        if verbose: print("probe: timeout", ip)
        ok = False
    except ConnectionRefusedError:
        if verbose: print("probe: connection refused", ip)
        # traceback.print_exc()
        ok = False
    except Exception as e:
        if verbose: print("probe: exception", e)
        # traceback.print_exc()
        ok = False
    
    if not ok:
        if writer is not None: writer.close()
        return None

    if verbose: print("probe: writing", ip)
    writer.write(st_)
    try:
        res = await asyncio.wait_for(reader.read(1024), timeout = timeout)
    except asyncio.TimeoutError:
        if verbose: print("probe: timeout at port", port)
        ok = False
    except Exception as e:
        traceback.print_exc()
        ok = False
    else:
        if verbose: print("probe: parsing response for", ip)
        header, res = parse_http_resp(res.decode("utf-8").lower())
        if verbose: print("probe: reply for", ip, ":", header, res)
        # if header.find("200 ok") > -1: 
        # NOTE: this is ALWAYS true - OPTIONS string doesn't require auth
        if header.find("rtsp") > -1:
            if verbose:
                print("\nSuccess at %s\n" % (ip))
            """
            if header.find("200") > -1:
                res.success = True
            else:
                res.success = False
            """
        else:
            ok = False

    writer.close()
    if ok: 
        return ip, port
    else:
        return None

