import logging
import csv
import can
import xml.etree.ElementTree as ET
from datetime import datetime
from os import makedirs
from pathlib import Path
from threading import Thread, Lock
from time import sleep
from dyno_v2.Module.CANcom import CANcom
from dyno_v2.Module.Parameter import Parameter
from dyno_v2.Module.util import signed, parse_etree, load_using_param_names, get_scale_value, indent
from dyno_v2.Module.exceptions import *


class VCMWatchdog:

    def __init__(self):
        self.com = CANcom(can_id=1)
