from pathlib import Path
from pprint import pprint
import copy, argparse, sys, os, yaml, logging
from valkka.discovery.camsearch.base import run
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
            'A more advanced camera search using combinations of WSDiscovery, arp-scan and OnVif probing'
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--user", action="store", help="username to try", default="admin", type=str,
        required=False)
    parser.add_argument("--passwd", action="store", help="password to try", default="123456", type=str,
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

    encodings=["h264"] if pars.h264 else encodings=None
    cams = run(user=pars.user, password=pars.passwd, encodings=encodings, width=pars.width)
    

    
if __name__ == "__main__":
    main()
