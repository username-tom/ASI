import logging
import math
import os
from dyno_v2.Module.CANcom import *
from dyno_v2.Module.Parameter import get
import xml.etree.ElementTree as ET


ROOT_DIR = os.getcwd()
NAME_INDEX = {'Arbitrary Address Capable': 63,
            'Industry Group': 60,
            'Vehicle System Instance': 56,
            'Vehicle System': 49,
            'Function': 40,
            'Function Instance': 35,
            'ECU Instance': 32,
            'Manufacturer Code': 21,
            'Identity Number': 0}
MEMORY_ACCESS_REQUEST_TEMPLATE = {
    'Number of Requests': 1,
    'Pointer Type': 1,
    'Command': 1,
    'Unused - SAE Reserved': 1,
    'Pointer': 0,
    'Pointer Extension': 0x81,
    'Key/User Level': 0xffff
}
MEMORY_ACCESS_RESPONSE_TEMPLATE = {
    'Number of Requests Allowed': 1,
    'Unused - SAE Reserved': 1,
    'Status': 0,
    'Unused - SAE Reserved - 1': 1,
    'Error Indicator/EDC Value': 0,
    'EDCP Extension': 6,
    'Seed': 0xffff
}
BINARY_DATA_TRANSFER_TEMPLATE = {
    'Number of Raw bytes of valid data': 1,
    'Raw Byte Data 1': 0xff,
    'Raw Byte Data 2': 0xff,
    'Raw Byte Data 3': 0xff,
    'Raw Byte Data 4': 0xff,
    'Raw Byte Data 5': 0xff,
    'Raw Byte Data 6': 0xff,
    'Raw Byte Data 7': 0xff
}
BINARY_DATA_TRANSFER_FIRST_TEMPLATE = {
    'Sequence Number': 1,
    'Multi-packet Indicator': 0xff,
    'Raw Byte Data 1': 0xff,
    'Raw Byte Data 2': 0xff,
    'Raw Byte Data 3': 0xff,
    'Raw Byte Data 4': 0xff,
    'Raw Byte Data 5': 0xff,
    'Raw Byte Data 6': 0xff
}
BINARY_DATA_TRANSFER_MIDDLE_TEMPLATE = {
    'Sequence Number': 2,
    'Raw Byte Data 1': 0xff,
    'Raw Byte Data 2': 0xff,
    'Raw Byte Data 3': 0xff,
    'Raw Byte Data 4': 0xff,
    'Raw Byte Data 5': 0xff,
    'Raw Byte Data 6': 0xff,
    'Raw Byte Data 7': 0xff
}
BINARY_DATA_TRANSFER_FINAL_TEMPLATE = {
    'Sequence Number': 3,
    'Number of Raw Occurrences': 0,
    'Raw Byte Data 1': 0xff,
    'Raw Byte Data 2': 0xff,
    'Raw Byte Data 3': 0xff,
    'Raw Byte Data 4': 0xff,
    'Raw Byte Data 5': 0xff,
    'Raw Byte Data 6': 0xff
}
DATA_TRANSFER_TEMPLATE = {
    'Sequence Number': 1,
    'Raw Byte Data 1': 0xff,
    'Raw Byte Data 2': 0xff,
    'Raw Byte Data 3': 0xff,
    'Raw Byte Data 4': 0xff,
    'Raw Byte Data 5': 0xff,
    'Raw Byte Data 6': 0xff,
    'Raw Byte Data 7': 0xff
}
CONNECTION_MANAGEMENT_TEMPLATE = {
    'Control byte': 16,
    'Total Message Size, number of bytes': 0xffff,
    'Total Number of Packets': 0xff,
    'Maximum Number of Packets': 0xff,
    'Number of Packets that can be sent': 0xff,
    'Next Packet Number to be Sent': 0xff,
    'Sequence Number': 0xff
}



def get_pf(pgn):
    return (pgn & (0xff << 8)) >> 8


def get_ps(pgn):
    return pgn & 0xff


def get_edp(pgn):
    return (pgn & (1 << 17)) >> 17


def get_dp(pgn):
    return (pgn & (1 << 16)) >> 16

class J1939PGN:

    def __init__(
            self,
            pgn=None,
            pglabel=None,
            acronym=None,
            rate=None,
            multipacket=False,
            length=None,
            priority=None,
            spg=None,
            description=None
    ):
        self.pgn = pgn
        self.label = pglabel
        self.acronym = acronym
        self.rate = rate
        self.multipacket = multipacket
        self.length = length
        self.priority = priority
        self.spg = spg
        self.description = description
        self.has_counter = False

    def __repr__(self):
        template = ''
        template += f'PGN: {self.pgn} | {self.label}\n'
        template += f'Acronym: {self.acronym}\n'
        template += f'Transmission Rate: {self.rate}ms\n'
        template += f'PG Data Length: {self.length} bytes\n'
        template += f'PG Priority: {self.priority}\n'
        template += f'SPG:\n'
        for sp in self.spg:
            template += f'\t{sp}\n'
        template += f'Description: {self.description}'
        return template

    def set_using_xml_element(self, xml):
        self.pgn = int(get('ParameterGroupNumber', xml))
        self.label = get('Label', xml)
        self.acronym = get('Acronym', xml)
        self.rate = int(get('Rate', xml)) * 0.001 if get('Rate', xml) else 0
        self.multipacket = bool(get('Multipacket', xml))
        self.length = int(get('Length', xml))
        self.priority = int(get('Priority', xml))
        self.description = get('Description', xml)

        spg = {}
        spg_raw = xml.find('SuspectParameterGroup')
        for sp in spg_raw.findall('SuspectParameter'):
            temp = J1939SPN(spn=int(sp.find('SuspectParameterNumber').text) if sp.find('SuspectParameterNumber').text else None,
                            sglabel=sp.find('SuspectParameterLabel').text,
                            start=sp.find('Start').text,
                            length=int(sp.find('SuspectParameterLength').text),
                            scale=float(sp.find('Scale').text),
                            offset=float(sp.find('Offset').text),
                            unit=sp.find('Unit').text,
                            minimum=float(sp.find('Minimum').text) if sp.find('Minimum').text else None,
                            maximum=float(sp.find('Maximum').text) if sp.find('Maximum').text else None,
                            asi_parameter=sp.find('ASIParameter').text if sp.find('ASIParameter') else None,
                            description=sp.find('SuspectParameterDescription').text)
            spg[temp.label] = temp
            if 'counter' in sp.find('SuspectParameterLabel').text.lower():
                self.has_counter = True
        self.spg = spg

    def get_pf(self):
        return (self.pgn & (0xff << 8)) >> 8

    def get_ps(self):
        return self.pgn & 0xff

    def get_edp(self):
        return (self.pgn & (1 << 17)) >> 17

    def get_dp(self):
        return (self.pgn & (1 << 16)) >> 16


class J1939SPN:

    def __init__(
            self,
            spn=None,
            sglabel=None,
            start=None,
            length=None,
            scale=None,
            offset=None,
            unit=None,
            minimum=None,
            maximum=None,
            asi_parameter=None,
            description=None,
            value=None
    ):
        self.spn = spn
        self.label = sglabel
        self.start = start
        self.length = length
        self.scale = scale
        self.offset = offset
        self.unit = unit
        self.minimum = minimum
        self.maximum = maximum
        self.asi_parameter = asi_parameter
        self.description = description
        self.scaled_value = value

    def __repr__(self):
        template = ''
        template += f'\tSGN: {self.spn} | {self.label}\n'
        template += f'\tPG Start Location: {self.start} | Length: {self.length} bits\n'
        template += f'\tScale: {self.scale} | Offset: {self.offset}\n'
        template += f'\tValue: {self.scaled_value} | Unit: {self.unit}\n'
        template += f'\tCorresponding Parameter: {self.asi_parameter if self.asi_parameter else "N/A"}\n'
        template += f'\tRange: {self.minimum} - {self.maximum}\n'
        template += f'\tDescription: {self.description}'
        return template


class J1939Name(J1939SPN):

    def __init__(self, children=None):
        super().__init__(spn=2848, start='1-1', length=64, scale=1, offset=0,
                         description='Address Claimed Message from J1939-81')
        if children:
            self.children = children
        else:
            self._init_children()

    def _init_children(self):
        self.children = {
            'Arbitrary Address Capable': J1939SPN(spn=2844, start='8-8', length=1, scale=1, offset=0,
                                                  description='Identity Number from NAME', value=0),
            'Industry Group': J1939SPN(spn=2846, start='8-5', length=3, scale=1, offset=1,
                                       description='Industry Group from NAME', value=0),
            'Vehicle System Instance': J1939SPN(spn=2843, start='8-1', length=4, scale=1, offset=0,
                                                description='Vehicle System Instance from NAME', value=15),
            'Vehicle System': J1939SPN(spn=2842, start='7-2', length=7, scale=1, offset=0,
                                       description='Vehicle System from NAME', value=0x7f),
            'Function': J1939SPN(spn=2841, start='6-1', length=8, scale=1, offset=0,
                                 description='Function from NAME', value=0xff),
            'Function Instance': J1939SPN(spn=2839, start='5-4', length=5, scale=1, offset=0,
                                          description='Function Instance from NAME', value=31),
            'ECU Instance': J1939SPN(spn=2840, start='5-1', length=3, scale=1, offset=0,
                                     description='ECU Instance from NAME', value=7),
            'Manufacturer Code': J1939SPN(spn=2838, start='3-6', length=11, scale=1, offset=0,
                                          description='Manufacturer Code from NAME', value=2047),
            'Identity Number': J1939SPN(spn=2837, start='1-1', length=21, scale=1, offset=0,
                                        description='Identity Number from NAME', value=0x1fffff)
        }

    def get_name(self):
        raw = 0
        for child in self.children:
            raw += self.children[child].scaled_value << NAME_INDEX[child]
        return raw


def calculate_sp_value(msg, sp):
    """
    For continuous SP arrangement
    """
    word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1
    value = 0
    if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
        value = (msg.data[word] & ((2 ** sp.length - 1) * (2 ** index))) * (0.5 ** index)
    elif sp.length + index <= 16:  # need to split data into 2 bytes
        value = (msg.data[word] & ((2 ** (8 - index) - 1) * (2 ** index))) * (0.5 ** index)
        value += (msg.data[word + 1] & (2 ** (sp.length - 8 + index) - 1)) * (2 ** (8 - index))
    elif sp.length + index <= 24:  # need to split data into 3 bytes
        value = (msg.data[word] & ((2 ** sp.length - 1) * (2 ** index))) * (0.5 ** index)
        value += (msg.data[word + 1] & ((2 ** 8 - 1) * (2 ** 8)))
        value += (msg.data[word + 2] & (2 ** (sp.length - 16 + index) - 1)) * (2 ** (16 - index))
    elif sp.length + index <= 32:  # need to split data into 4 bytes
        value = (msg.data[word] & ((2 ** sp.length - 1) * (2 ** index))) * (0.5 ** index)
        value += (msg.data[word + 1] & ((2 ** 8 - 1) * (2 ** 8)))
        value += (msg.data[word + 2] & ((2 ** 8 - 1) * (2 ** 16)))
        value += (msg.data[word + 3] & (2 ** (sp.length - 24 + index) - 1)) * (2 ** (24 - index))
    return value

def construct_sp_value(msg_out, values, sp):
    word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1

    if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
        msg_out.data[word] += values[sp.label] << index
    elif sp.length + index <= 16:  # need to split data into 2 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        msg_out.data[word + 1] += (values[sp.label] - (first_half >> index)) >> (8 - index)
    elif sp.length + index <= 24:  # need to split data into 3 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(2):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
    elif sp.length + index <= 32:  # need to split data into 4 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(3):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
    elif sp.length + index <= 40:  # need to split data into 5 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(4):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
    elif sp.length + index <= 48:  # need to split data into 6 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(5):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
    elif sp.length + index <= 56:  # need to split data into 7 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(6):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
    elif sp.length + index <= 64:  # need to split data into 8 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(7):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
    return msg_out

def construct_dm_value(msg_out, values, sp):
    word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1

    if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
        msg_out.data[word] += values[sp.label] << index
    elif sp.length + index <= 16:  # need to split data into 2 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        msg_out.data[word + 1] += ((values[sp.label] - (first_half >> index)) >> (8 - index)) << (16 - sp.length - index)
    elif sp.length + index <= 24:  # need to split data into 3 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(1):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
        msg_out.data[word + 2] += ((values[sp.label] & ((2 ** (sp.length - 16 + index) - 1) <<
                                                        (16 - index))) >> (16 - index)) << (24 - sp.length - index)
        # msg_out.data[word + 1] += (values[sp.label] & (255 << (8 - index))) >> 8
        # msg_out.data[word + 2] += ((values[sp.label] - (first_half >> index)) >> (8 - index)) << (24 - sp.length - index)
    elif sp.length + index <= 32:  # need to split data into 4 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(2):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
        msg_out.data[word + 3] += ((values[sp.label] & ((2 ** (sp.length - 24 + index) - 1) <<
                                                        (24 - index))) >> (24 - index)) << (32 - sp.length - index)
    elif sp.length + index <= 40:  # need to split data into 5 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(3):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
        msg_out.data[word + 4] += ((values[sp.label] & ((2 ** (sp.length - 32 + index) - 1) <<
                                                        (32 - index))) >> (32 - index)) << (40 - sp.length - index)
    elif sp.length + index <= 48:  # need to split data into 6 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(4):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
        msg_out.data[word + 5] += ((values[sp.label] & ((2 ** (sp.length - 40 + index) - 1) <<
                                                        (40 - index))) >> (40 - index)) << (48 - sp.length - index)
    elif sp.length + index <= 56:  # need to split data into 7 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(5):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
        msg_out.data[word + 6] += ((values[sp.label] & ((2 ** (sp.length - 48 + index) - 1) <<
                                                        (48 - index))) >> (48 - index)) << (56 - sp.length - index)
    elif sp.length + index <= 64:  # need to split data into 8 bytes
        first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
        msg_out.data[word] += first_half
        for i in range(6):
            msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
                                                               (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
        msg_out.data[word + 3] += ((values[sp.label] & ((2 ** (sp.length - 56 + index) - 1) <<
                                                        (56 - index))) >> (56 - index)) << (64 - sp.length - index)
    return msg_out

def calculate_dm_value(msg, sp):
    """
    For floating MSB SP arrangement
    """
    word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1
    value = 0
    if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
        value = (msg.data[word] & ((2 ** sp.length - 1) * (2 ** index))) * (0.5 ** index)
    elif sp.length + index <= 16:  # need to split data into 2 bytes
        value = (msg.data[word] & ((2 ** (8 - index) - 1) * (2 ** index))) * (0.5 ** index)
        value += (msg.data[word + 1] & ((2 ** (sp.length - 8 + index) - 1) * (2 ** (16 - sp.length - index))))
    elif sp.length + index <= 24:  # need to split data into 3 bytes
        value = (msg.data[word] & ((2 ** sp.length - 1) * (2 ** index))) * (0.5 ** index)
        value += (msg.data[word + 1] & ((2 ** 8 - 1) * (2 ** 8)))
        value += (msg.data[word + 2] & ((2 ** (sp.length - 16 + index) - 1) * (2 ** (24 - sp.length - index))))
    elif sp.length + index <= 32:  # need to split data into 4 bytes
        value = (msg.data[word] & ((2 ** sp.length - 1) * (2 ** index))) * (0.5 ** index)
        value += (msg.data[word + 1] & ((2 ** 8 - 1) * (2 ** 8)))
        value += (msg.data[word + 2] & ((2 ** 8 - 1) * (2 ** 16)))
        value += (msg.data[word + 3] & ((2 ** (sp.length - 24 + index) - 1) * (2 ** (32 - sp.length - index))))
    return value


class J1939com(CANcom):

    def __init__(
            self,
            tree,
            can_port="PCAN_USBBUS1",
            bit_rate=500000,
            can_id=0xef,
            device='BAC',
            parameters="dyno_v2/Parameter Files/J1939_BAC.xml"
    ):
        super().__init__(can_port, bit_rate, can_id, False)
        self.device = device
        self.parameter_file = parameters
        self.pgn_threads = {}
        self.pgn_threads_enabled = False
        self.sa = 0xfd
        self.asi_parameters = {}
        self.etree = tree

        logging.info("Generating parameter object")
        for section in self.etree.findall('Parameters'):
            for element in section.findall('ParameterDescription'):
                parameter = Parameter()
                parameter.set_using_xml_element(element)
                self.asi_parameters[parameter.Name] = parameter

        self.specific_parameters = {self.sa: {}}
        self.j1939_parameters = {self.sa: {}}
        self.sa_on_network = {}
        self.id = []
        self.name = J1939Name()

        root = ET.parse(self.parameter_file).getroot()

        logging.info("Generating J1939 PGNs for DUT")
        for section in root.findall('ParameterGroup'):
            for element in section.findall('Parameter'):
                pgn = J1939PGN()
                pgn.set_using_xml_element(element)
                self.specific_parameters[self.sa][pgn.pgn] = pgn

        root = ET.parse(f"{ROOT_DIR}/dyno_v2/Parameter Files/J1939_PGN.xml").getroot()

        logging.info("Generating J1939 Pre-defined PGNs for DUT")
        for section in root.findall('ParameterGroup'):
            for element in section.findall('Parameter'):
                pgn = J1939PGN()
                pgn.set_using_xml_element(element)
                self.j1939_parameters[self.sa][pgn.label] = pgn

        if not self.claim_address():
            print('Diagnostic tool failed to claim an address')
            return
        self._register_devices_on_network()
        # self.startListening()

    def __del__(self):
        self.reset_pgn_threads()
        super().__del__()

    def _register_devices_on_network(self):
        for _ in range(2000):
            msg_in = self.CANBus.recv(0.001)
            if msg_in:
                self.add_device(msg_in.arbitration_id & 255)

    def add_device(self, sa):
        if sa in self.id:
            logging.debug(f"Device {sa} already registered")
            return
        self.id.append(sa)
        self.specific_parameters[sa] = {}
        self.j1939_parameters[sa] = {}

        if sa == 39:
            root = ET.parse('dyno_v2/Parameter Files/J1939_VCM.xml').getroot()
        elif 0xa0 <= sa <= 0xa7 or 0xef <= sa <= 0xf2:
            root = ET.parse('dyno_v2/Parameter Files/J1939_BAC.xml').getroot()
        elif 0xb0 <= sa <= 0xb3:
            root = ET.parse('dyno_v2/Parameter Files/J1939_Throttle.xml').getroot()
        else:
            return

        logging.info(f"Generating J1939 PGNs for device at Source Address {sa}")
        for section in root.findall('ParameterGroup'):
            for element in section.findall('Parameter'):
                pgn = J1939PGN()
                pgn.set_using_xml_element(element)
                self.specific_parameters[sa][pgn.pgn] = pgn

        root = ET.parse("dyno_v2/Parameter Files/J1939_PGN.xml").getroot()

        logging.info(f"Generating J1939 Pre-defined PGNs for device at Source Address {sa}")
        for section in root.findall('ParameterGroup'):
            for element in section.findall('Parameter'):
                pgn = J1939PGN()
                pgn.set_using_xml_element(element)
                self.j1939_parameters[sa][pgn.label] = pgn
        self.sa_on_network[sa] = 'device'

    def remove_device(self, sa):
        self.id.remove(sa)

    def reset_pgn_threads(self):
        self.pgn_threads_enabled = False
        self.pgn_threads = {}

    def claim_address(self, event=None):
        """
        Claiming address as a debug device with filler NAME
        """
        msg = can.Message(arbitration_id=0x18eeff00 + self.sa, data=self.get_name())
        claimed = False
        try:
            self.CANBus.send(msg)
        except can.interfaces.pcan.pcan.PcanCanOperationError as e:
            logging.error(f"PCAN Operation Error: {e}")
            return claimed
        else:
            while not claimed:
                for i in range(250):
                    address_claimed = self.CANBus.recv(timeout=0.001)
                    if address_claimed and (address_claimed.arbitration_id & 0xff) == self.sa:
                        self.sa += 1
                        msg.arbitration_id += 1
                        self.CANBus.send(msg)
                        break
                    if i == 249:
                        claimed = True
            return claimed

    def get_name(self, in_array=True):
        if in_array:
            ans = [0] * 8
            name_raw = self.name.get_name()
            for i in range(8):
                ans[i] = (name_raw & (255 << 8 * (7 - i))) >> (8 * (7 - i))
            return ans
        else:
            for sp in self.name.children:
                print(self.name.children[sp])

    def pgn_msg_builder(self, name, device, values):
        """
        Constructor for PGN Messages with a source address as target

        Args:
            name - PGN Label
            device - Source Address
            values - Dictionary {SP Label: Value}

        """
        msg_out = can.Message(data=[0] * self.specific_parameters[device][name].length)
        msg_out.arbitration_id = self.specific_parameters[device][name].priority << 26
        msg_out.arbitration_id += self.specific_parameters[device][name].pgn << 8
        msg_out.arbitration_id += device
        for sp in self.specific_parameters[device][name].spg:
            sp = self.specific_parameters[device][name].spg[sp]
            msg_out = construct_sp_value(msg_out, values, sp)
            # word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1
            #
            # if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
            #     msg_out.data[word] += values[sp.label] << index
            # elif sp.length + index <= 16:  # need to split data into 2 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     msg_out.data[word + 1] += (values[sp.label] - (first_half >> index)) >> (8 - index)
            # elif sp.length + index <= 24:  # need to split data into 3 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     msg_out.data[word + 1] += values[sp.label] & (255 << (8 - index))
            #     msg_out.data[word + 2] += (values[sp.label] - (first_half >> index)) >> (8 - index)
            # elif sp.length + index <= 32:  # need to split data into 4 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(3):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 40:  # need to split data into 5 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(4):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 48:  # need to split data into 6 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(5):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 56:  # need to split data into 7 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(6):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 64:  # need to split data into 8 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(7):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)

        # print(msg_out)
        return msg_out

    def protocol_msg_builder(self, name, device, target, values):
        """
        Constructor for PGN Messages with a source address as target

        Args:
            name - PGN Label
            device - Source Address
            values - Dictionary {SP Label: Value}

        """
        msg_out = can.Message(data=[0] * self.j1939_parameters[device][name].length)
        msg_out.arbitration_id = self.j1939_parameters[device][name].priority << 26
        msg_out.arbitration_id += (self.j1939_parameters[device][name].pgn + target) << 8
        msg_out.arbitration_id += device
        for sp in self.j1939_parameters[device][name].spg:
            sp = self.j1939_parameters[device][name].spg[sp]
            if sp.spn in [1640, 1649]:
                msg_out = construct_dm_value(msg_out, values, sp)
            else:
                msg_out = construct_sp_value(msg_out, values, sp)
            # word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1
            #
            # if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
            #     msg_out.data[word] += values[sp.label] << index
            # elif sp.length + index <= 16:  # need to split data into 2 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     # msg_out.data[word + 1] += (values[sp.label] & (2 ** (sp.length - 8 + index) - 1)) << (16 - sp.length - index)
            #     for i in range(1):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 24:  # need to split data into 3 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(2):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 32:  # need to split data into 4 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(3):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 40:  # need to split data into 5 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(4):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 48:  # need to split data into 6 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(5):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 56:  # need to split data into 7 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(6):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)
            # elif sp.length + index <= 64:  # need to split data into 8 bytes
            #     first_half = (values[sp.label] & (2 ** (8 - index) - 1)) << index
            #     msg_out.data[word] += first_half
            #     for i in range(7):
            #         msg_out.data[word + i + 1] += (values[sp.label] & ((2 ** (sp.length - 8 * (1 + i) + index) - 1) <<
            #                                                            (8 * (1 + i) - index))) >> (8 * (1 + i) - index)

        # print(msg_out)
        return msg_out

    def pgn_msg_handle(self, msg: can.Message):
        msg_pgn = (msg.arbitration_id & (0xffff << 8)) >> 8
        msg_sa = msg.arbitration_id & 255
        try:
            self.specific_parameters[msg_sa][msg_pgn]
        except KeyError:
            pass
        else:
            msg_priority = (msg.arbitration_id & (7 << 26)) >> 26
            # msg_ps = get_ps(msg_pgn)
            msg_edp = get_edp(msg_pgn)
            msg_dp = get_dp(msg_pgn)
            if self.specific_parameters[msg_sa][msg_pgn].pgn == msg_pgn and \
                    self.specific_parameters[msg_sa][msg_pgn].priority == msg_priority and \
                    self.specific_parameters[msg_sa][msg_pgn].get_edp() == msg_edp and \
                    self.specific_parameters[msg_sa][msg_pgn].get_dp() == msg_dp and \
                    msg_sa in self.id:
                for sp in self.specific_parameters[msg_sa][msg_pgn].spg:
                    sp = self.specific_parameters[msg_sa][msg_pgn].spg[sp]
                    value = calculate_sp_value(msg, sp)
                    sp.scaled_value = value * sp.scale + sp.offset
                return True
        # msg_ps = get_ps(msg_pgn)
        msg_pf = get_pf(msg_pgn)
        msg_pgn = msg_pf << 8
        try:
            self.specific_parameters[msg_sa][msg_pgn]
        except KeyError:
            return False
        else:
            msg_priority = (msg.arbitration_id & (7 << 26)) >> 26
            msg_edp = get_edp(msg_pgn)
            msg_dp = get_dp(msg_pgn)
            if self.specific_parameters[msg_sa][msg_pgn].get_pf() == msg_pf and \
                    self.specific_parameters[msg_sa][msg_pgn].get_pf() not in [0xff] and \
                    self.specific_parameters[msg_sa][msg_pgn].priority == msg_priority and \
                    self.specific_parameters[msg_sa][msg_pgn].get_edp() == msg_edp and \
                    self.specific_parameters[msg_sa][msg_pgn].get_dp() == msg_dp and \
                    msg_sa in self.id:
                for sp in self.specific_parameters[msg_sa][msg_pgn].spg:
                    sp = self.specific_parameters[msg_sa][msg_pgn].spg[sp]
                    value = calculate_sp_value(msg, sp)
                    sp.scaled_value = value * sp.scale + sp.offset
                return True
            return False

    def protocol_msg_handle(self, msg: can.Message):
        msg_priority = (msg.arbitration_id & (7 << 26)) >> 26
        msg_pgn = (msg.arbitration_id & (0xff00 << 8)) >> 8
        msg_target = ((msg.arbitration_id & (0xff << 8)) >> 8)
        msg_edp = (msg.arbitration_id & (1 << 24)) >> 24
        msg_dp = (msg.arbitration_id & (1 << 25)) >> 25
        msg_sa = msg.arbitration_id & 255
        self.add_device(msg_sa)

        for pgn in self.j1939_parameters[msg_sa]:
            if self.j1939_parameters[msg_sa][pgn].pgn == msg_pgn and \
                self.j1939_parameters[msg_sa][pgn].priority == msg_priority and \
                self.j1939_parameters[msg_sa][pgn].get_edp() == msg_edp and \
                self.j1939_parameters[msg_sa][pgn].get_dp() == msg_dp:
                if self.sa == msg_target:
                    for sp in self.j1939_parameters[msg_sa][pgn].spg:
                        sp = self.j1939_parameters[msg_sa][pgn].spg[sp]
                        if sp.spn in [1640, 1649]:
                            value = calculate_dm_value(msg, sp)
                        else:
                            value = calculate_sp_value(msg, sp)
                        # word, index = int(sp.start.split('-')[0]) - 1, int(sp.start.split('-')[1]) - 1
                        # value = 0
                        # if sp.length + index <= 8:  # when the sp is contained with in a byte, no need to split data
                        #     value = (msg.data[word] & ((2 ** sp.length - 1) << index)) >> index
                        # elif sp.length + index <= 16:  # need to split data into 2 bytes
                        #     value = (msg.data[word] & (2 ** (8 - index) - 1) << index) >> index
                        #     value += (msg.data[word + 1] & (2 ** (sp.length - 8 + index) - 1)) << (8 - index)
                        # elif sp.length + index <= 24:  # need to split data into 3 bytes
                        #     value = (msg.data[word] & (2 ** sp.length - 1) << index) >> index
                        #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 8))
                        #     value += (msg.data[word + 2] & ((2 ** (sp.length - 16 + index) - 1) << (16 - index)))
                        # elif sp.length + index <= 32:  # need to split data into 4 bytes
                        #     value = (msg.data[word] & (2 ** sp.length - 1) << index) >> index
                        #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 8))
                        #     value += (msg.data[word + 1] & ((2 ** 8 - 1) << 16))
                        #     value += (msg.data[word + 3] & ((2 ** (sp.length - 24 + index) - 1) << (24 - index)))
                        sp.scaled_value = value * sp.scale + sp.offset
                    return self.j1939_parameters[msg_sa][pgn], msg_sa
                elif msg_target == 0xff:
                    return False, False
        return False, False

    def read(self, name, index=0, length=1):
        try:
            address = int(self.asi_parameters[name].Address)
        except KeyError:
            logging.error(f"Bad parameter name: {name}")
            return
        else:
            names = []
            for i in range(length):
                names.append(self.etree.find(f".//ParameterDescription[Address='{address + i}']").find('Name').text)

        request_values = MEMORY_ACCESS_REQUEST_TEMPLATE
        request_values['Number of Requests'] = length
        request_values['Command'] = 1  # Read
        request_values['Pointer'] = address
        msg = self.protocol_msg_builder('Memory Access Request', self.sa, index, request_values)

        request_values['Command'] = 3  # Status
        status_msg = self.protocol_msg_builder('Memory Access Request', self.sa, index, request_values)
        self.msg_buffer.append(msg)
        sleep(0.005)

        if length <= 3:
            response = None
            counter = 0
            while not response and counter < 5:
                try:
                    response = self.out.popleft()
                except IndexError:
                    # self.msg_buffer.append(msg)
                    sleep(0.005)
                    response = None
                    counter += 1
                else:
                    parsed, parsed_sa = self.protocol_msg_handle(response[1])
            if counter == 5:
                raise J1939TimeoutError
            # Wait for proceed
            while not (parsed and parsed.label == 'Memory Access Response' and parsed_sa == index
                       and parsed.spg['Status'].scaled_value == 0):
                self.msg_buffer.append(status_msg)
                status_response = None
                while not status_response:
                    try:
                        status_response = self.out.popleft()
                    except IndexError:
                        sleep(0.001)
                parsed, parsed_sa = self.protocol_msg_handle(status_response[1])
            # Wait for binary packets
            sleep(0.001)
            binary_response = None
            counter = 0
            while not binary_response and counter < 30:
                try:
                    binary_response = self.out.popleft()
                except IndexError:
                    sleep(0.001)
                    counter += 1
                else:
                    parsed_binary, binary_sa = self.protocol_msg_handle(binary_response[1])
                    if parsed_binary and parsed_binary.label == 'Binary Data Transfer' and binary_sa == index:
                        return_list = []
                        for i in range(length):
                            raw_value = signed(
                                int(parsed_binary.spg[f'Raw Byte Data {1 + 2 * i}'].scaled_value +
                                    (int(parsed_binary.spg[
                                             f'Raw Byte Data {2 + 2 * i}'].scaled_value) << 8)))
                            scale = get_scale_value(self.asi_parameters[names[i]].Scale)
                            value = raw_value / scale
                            if self.asi_parameters[names[i]].Scale == 'hex' and value < 0:
                                value += 65536
                            self.asi_parameters[names[i]].Value = value
                            return_list.append(self.asi_parameters[names[i]].Value)

                        got_response = False
                        while not got_response:
                            try:
                                response = self.out.popleft()
                            except IndexError:
                                sleep(0.001)
                            else:
                                got_response = True
                        return return_list
                    else:
                        binary_response = None
                        counter += 1
            logging.warning(f'Timed Out waiting for binary response')
        elif length <= 892:
            tp_value = CONNECTION_MANAGEMENT_TEMPLATE
            # Build End of Message Acknowledgment
            tp_value['Control byte'] = 19  # End of Message Acknowledgment
            tp_value['Total Message Size, number of bytes'] = length * 2 + 1  # Total message size, number of bytes
            tp_value['Total Number of Packets'] = math.ceil((length * 2 + 1) / 7)  # Total number of packets
            tp_value['Maximum Number of Packets'] = 0xff  # Reserved, always 0xFF
            temp_pgn = self.j1939_parameters[index]['Binary Data Transfer']
            # binary_pgn = temp_pgn.priority << 18
            # binary_pgn += (temp_pgn.pgn + index)
            binary_pgn = temp_pgn.pgn
            tp_value['Number of Packets that can be sent'] = binary_pgn & 0xff
            tp_value['Next Packet Number to be Sent'] = (binary_pgn & (0xff << 8)) >> 8
            tp_value['Sequence Number'] = (binary_pgn & (0xff << 16)) >> 16
            ack_msg = self.protocol_msg_builder('Transport Protocol - Connection Management', self.sa, index, tp_value)
            # msg_per_cts = 0
            response = None
            counter = 0
            while not response and counter < 3:
                try:
                    response = self.out.popleft()
                except IndexError:
                    self.msg_buffer.append(msg)
                    sleep(0.001)
                    response = None
                    counter += 1
            if counter == 3:
                raise J1939TimeoutError
            parsed, parsed_sa = self.protocol_msg_handle(response[1])
            # Wait for proceed
            while not (parsed and parsed.label == 'Memory Access Response' and parsed_sa == index
                       and parsed.spg['Status'].scaled_value == 0):
                self.msg_buffer.append(status_msg)
                status_response = None
                while not status_response:
                    try:
                        status_response = self.out.popleft()
                    except IndexError:
                        sleep(0.001)
                parsed, parsed_sa = self.protocol_msg_handle(status_response[1])
            # Wait for Request to Send
            while not (parsed and parsed.label == 'Transport Protocol - Connection Management' and parsed_sa == index
                       and parsed.spg['Number of Packets that can be sent'].scaled_value == tp_value['Number of Packets that can be sent']
                       and parsed.spg['Next Packet Number to be Sent'].scaled_value == tp_value['Next Packet Number to be Sent']
                       and parsed.spg['Sequence Number'].scaled_value == tp_value['Sequence Number']
                       and parsed.spg['Control byte'].scaled_value == 16):
                       # and parsed.spg['Total Message Size, number of bytes'].scaled_value == tp_value['Total Message Size, number of bytes'] + 1):
                # self.msg_buffer.append(status_msg)
                sleep(0.001)
                status_response = None
                while not status_response:
                    try:
                        status_response = self.out.popleft()
                    except IndexError:
                        sleep(0.005)

                parsed, parsed_sa = self.protocol_msg_handle(status_response[1])
            msg_per_cts = int(parsed.spg['Maximum Number of Packets'].scaled_value)
            return_list = []
            carry_over = 0
            # Build Clear to Send Message
            tp_value['Control byte'] = 17  # Clear to Send
            tp_value['Total Number of Packets'] = 0xff  # Reserved, always 0xFF
            tp_value['Maximum Number of Packets'] = 0xff  # Reserved, always 0xFF
            if msg_per_cts < 0xff:  # Multipacket in separated CTS
                for i in range(int(math.ceil(length * 2 / 7) / msg_per_cts)):
                    tp_value['Total Message Size, number of bytes'] = msg_per_cts
                    tp_value['Total Message Size, number of bytes'] += (i * msg_per_cts + 1) << 8
                    cts_msg = self.protocol_msg_builder('Transport Protocol - Connection Management', self.sa, index,
                                                        tp_value)
                    self.msg_buffer.append(cts_msg)
                    sleep(0.001)
                    for j in range(int(msg_per_cts)):
                        binary_response = None
                        while not binary_response:
                            try:
                                binary_response = self.out.popleft()
                            except IndexError:
                                sleep(0.001)
                            else:
                                parsed_binary, binary_sa = self.protocol_msg_handle(binary_response[1])
                                if (parsed_binary.label == 'Transport Protocol - Data Transfer' and binary_sa == index
                                    and parsed_binary.spg['Sequence Number'].scaled_value == (
                                                i * msg_per_cts + j + 1)):
                                    pass
                                else:
                                    parsed_binary = None

                        if j % 2 == 1:
                            for k in range(3):
                                raw_value = signed(
                                    int(parsed_binary.spg[f'Raw Byte Data {1 + 2 * k}'].scaled_value +
                                        (int(parsed_binary.spg[
                                                 f'Raw Byte Data {2 + 2 * k}'].scaled_value) << 8)))
                                scale = get_scale_value(self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Scale)
                                value = raw_value / scale
                                if self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Scale == 'hex' and value < 0:
                                    value += 65536
                                self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Value = value
                                return_list.append(self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Value)
                            carry_over = parsed_binary.spg['Raw Byte Data 7'].scaled_value
                        elif j == 0:
                            for k in range(3):
                                raw_value = signed(
                                    int(parsed_binary.spg[f'Raw Byte Data {2 + 2 * k}'].scaled_value +
                                        (int(parsed_binary.spg[
                                                 f'Raw Byte Data {3 + 2 * k}'].scaled_value) << 8)))
                                scale = get_scale_value(self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Scale)
                                value = raw_value / scale
                                if self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Scale == 'hex' and value < 0:
                                    value += 65536
                                self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Value = value
                                return_list.append(self.asi_parameters[names[i * msg_per_cts + j * 3 + k]].Value)
                        elif j % 2 == 0:
                            # Stitch up carried over value
                            raw_value = carry_over + (parsed_binary.spg['Raw Byte Data 1'].scaled_value << 8)
                            raw_value = signed(raw_value)
                            scale = get_scale_value(
                                self.asi_parameters[names[i * msg_per_cts + j * 7 + 3]].Scale)
                            value = raw_value / scale
                            if self.asi_parameters[names[i * msg_per_cts + j * 7 + 3]].Scale == 'hex' and value < 0:
                                value += 65536
                            self.asi_parameters[names[i * msg_per_cts + j * 7 + 3]].Value = value
                            return_list.append(self.asi_parameters[names[i * msg_per_cts + j * 7 + 3]].Value)
                            # Rest of the message
                            for k in range(3):
                                raw_value = signed(
                                    int(parsed_binary.spg[f'Raw Byte Data {2 + 2 * k}'].scaled_value +
                                        (int(parsed_binary.spg[
                                                 f'Raw Byte Data {3 + 2 * k}'].scaled_value) << 8)))
                                scale = get_scale_value(
                                    self.asi_parameters[names[i * msg_per_cts + j * 7 + 3 + k]].Scale)
                                value = raw_value / scale
                                if self.asi_parameters[
                                    names[i * msg_per_cts + j * 7 + 4 + k]].Scale == 'hex' and value < 0:
                                    value += 65536
                                self.asi_parameters[names[i * msg_per_cts + j * 7 + 4 + k]].Value = value
                                return_list.append(self.asi_parameters[names[i * msg_per_cts + j * 7 + 4 + k]].Value)
            else:
                tp_value['Total Message Size, number of bytes'] = msg_per_cts
                tp_value['Total Message Size, number of bytes'] += 1 << 8
                cts_msg = self.protocol_msg_builder('Transport Protocol - Connection Management', self.sa, index,
                                                    tp_value)
                self.msg_buffer.append(cts_msg)
                sleep(0.001)
                for j in range(int(math.ceil(length * 2 / 7))):
                    binary_response = None
                    while not binary_response:
                        try:
                            binary_response = self.out.popleft()
                        except IndexError:
                            sleep(0.001)
                    parsed_binary, parsed_sa = self.protocol_msg_handle(binary_response[1])
                    if j == 0:
                        for k in range(3):
                            if parsed_binary.spg[f'Raw Byte Data {2 + 2 * k}'].scaled_value == 0xff and \
                                    parsed_binary.spg[f'Raw Byte Data {3 + 2 * k}'].scaled_value == 0xff:
                                continue
                            raw_value = signed(
                                int(parsed_binary.spg[f'Raw Byte Data {2 + 2 * k}'].scaled_value +
                                    (int(parsed_binary.spg[
                                             f'Raw Byte Data {3 + 2 * k}'].scaled_value) << 8)))
                            # try:
                            scale = get_scale_value(self.asi_parameters[names[k]].Scale)
                            value = raw_value / scale
                            if self.asi_parameters[names[k]].Scale == 'hex' and value < 0:
                                value += 65536
                            self.asi_parameters[names[k]].Value = value
                            return_list.append(self.asi_parameters[names[k]].Value)
                            # except IndexError:
                            #     pass
                    elif j > 0 and j % 2 == 0:
                        # Stitch up carried over value
                        raw_value = carry_over + (int(parsed_binary.spg['Raw Byte Data 1'].scaled_value) << 8)
                        raw_value = signed(raw_value)
                        scale = get_scale_value(
                            self.asi_parameters[names[j * 3]].Scale)
                        value = raw_value / scale
                        if self.asi_parameters[names[j * 3]].Scale == 'hex' and value < 0:
                            value += 65536
                        self.asi_parameters[names[j * 3]].Value = value
                        return_list.append(self.asi_parameters[names[j * 3]].Value)
                        for k in range(3):
                            if parsed_binary.spg[f'Raw Byte Data {2 + 2 * k}'].scaled_value == 0xff and \
                                    parsed_binary.spg[f'Raw Byte Data {3 + 2 * k}'].scaled_value == 0xff:
                                continue
                            raw_value = signed(
                                int(parsed_binary.spg[f'Raw Byte Data {2 + 2 * k}'].scaled_value +
                                    (int(parsed_binary.spg[
                                             f'Raw Byte Data {3 + 2 * k}'].scaled_value) << 8)))
                            try:
                                scale = get_scale_value(self.asi_parameters[names[j * 3 + k + 1]].Scale)
                                value = raw_value / scale
                                if self.asi_parameters[names[j * 3 + k + 1]].Scale == 'hex' and value < 0:
                                    value += 65536
                                self.asi_parameters[names[j * 3 + k + 1]].Value = value
                                return_list.append(self.asi_parameters[names[j * 3 + k + 1]].Value)
                            except IndexError:
                                pass
                    elif j % 2 == 1:
                        # Rest of the message
                        for k in range(3):
                            if parsed_binary.spg[f'Raw Byte Data {1 + 2 * k}'].scaled_value == 0xff and \
                                    parsed_binary.spg[f'Raw Byte Data {2 + 2 * k}'].scaled_value == 0xff:
                                continue
                            raw_value = signed(
                                int(parsed_binary.spg[f'Raw Byte Data {1 + 2 * k}'].scaled_value +
                                    (int(parsed_binary.spg[
                                             f'Raw Byte Data {2 + 2 * k}'].scaled_value) << 8)))
                            try:
                                scale = get_scale_value(
                                    self.asi_parameters[names[j * 3 + k]].Scale)
                                value = raw_value / scale
                                if self.asi_parameters[
                                    names[j * 3 + k]].Scale == 'hex' and value < 0:
                                    value += 65536
                                self.asi_parameters[names[j * 3 + k]].Value = value
                                return_list.append(self.asi_parameters[names[j * 3 + k]].Value)
                            except IndexError:
                                pass
                        carry_over = int(parsed_binary.spg['Raw Byte Data 7'].scaled_value)

            self.msg_buffer.append(ack_msg)
            got_response = False
            while not got_response:
                try:
                    response = self.out.popleft()
                except IndexError:
                    sleep(0.001)
                else:
                    got_response = True
            return return_list
        # got_response = False
        # while not got_response:
        #     try:
        #         response = self.out.popleft()
        #     except IndexError:
        #         sleep(0.001)
        #     else:
        #         got_response = True

        # sleep(0.001)
        # if parsed.label == 'Memory Access Response' and parsed_sa == index:
        #     if parsed.spg['Status'].scaled_value == 1:  # Proceed
        #         sleep(0.001)
        #         got_response = False
        #         while not got_response:
        #             try:
        #                 binary_response = self.out.popleft()
        #             except IndexError:
        #                 sleep(0.001)
        #             else:
        #                 got_response = True
        #         parsed_binary, binary_sa = self.protocol_msg_handle(binary_response[1])
        #         if parsed_binary.label == 'Binary Data Transfer' and binary_sa == index:
        #             return_list = []
        #             for i in range(length):
        #                 raw_value = signed(int(parsed_binary.spg[f'Raw Byte Data {1 + 2 * i}'].scaled_value +
        #                                        (int(parsed_binary.spg[f'Raw Byte Data {2 + 2 * i}'].scaled_value) << 8)))
        #                 scale = get_scale_value(self.asi_parameters[names[i]].Scale)
        #                 value = raw_value / scale
        #                 if self.asi_parameters[names[i]].Scale == 'hex' and value < 0:
        #                     value += 65536
        #                 self.asi_parameters[names[i]].Value = value
        #                 return_list.append(self.asi_parameters[names[i]].Value)
        #             sleep(0.001)
        #             got_response = False
        #             while not got_response:
        #                 try:
        #                     response = self.out.popleft()
        #                 except IndexError:
        #                     sleep(0.001)
        #                 else:
        #                     got_response = True
        #             return return_list
        return [0]

    def write(self, name, value, index=0, length=1):
        scaled = True
        try:
            address = int(self.asi_parameters[name].Address)
        except KeyError:
            if isinstance(name, int):
                address = name
                scaled = False
            else:
                logging.error(f"Bad parameter name: {name}")
                return
        names = []
        for i in range(length):
            names.append(self.etree.find(f".//ParameterDescription[Address='{address + i}']").find('Name').text)

        # Preparing J1939 messages
        request_values = MEMORY_ACCESS_REQUEST_TEMPLATE
        request_values['Number of Requests'] = length
        request_values['Command'] = 2  # Write
        request_values['Pointer'] = address
        msg = self.protocol_msg_builder('Memory Access Request', self.sa, index, request_values)
        request_values['Command'] = 3  # Status
        status_msg = self.protocol_msg_builder('Memory Access Request', self.sa, index, request_values)
        self.msg_buffer.append(msg)
        sleep(0.005)

        if length <= 3:
            binary_values = BINARY_DATA_TRANSFER_TEMPLATE
            binary_values['Number of Raw bytes of valid data'] = length * 2
            for i in range(length):
                if scaled:
                    scaled_value = int(value[i] * get_scale_value(self.asi_parameters[name].Scale))
                else:
                    scaled_value = value[i]
                binary_values[f"Raw Byte Data {1 + 2 * i}"] = scaled_value & 0xff
                binary_values[f"Raw Byte Data {2 + 2 * i}"] = (scaled_value & (0xff << 8)) >> 8
            binary_msg = self.protocol_msg_builder('Binary Data Transfer', self.sa, index, binary_values)

            got_response = False
            counter = 0
            while not got_response and counter < 5:
                try:
                    response = self.out.popleft()
                except IndexError:
                    # self.msg_buffer.append(msg)
                    sleep(0.005)
                    counter += 1
                else:
                    got_response = True
            if counter == 5:
                raise J1939TimeoutError
            parsed, parsed_sa = self.protocol_msg_handle(response[1])
            sleep(0.001)
            # Wait for proceed
            while not (parsed and parsed.label == 'Memory Access Response' and parsed_sa == index
                       and parsed.spg['Status'].scaled_value == 0):
                self.msg_buffer.append(status_msg)
                status_response = None
                while not status_response:
                    try:
                        status_response = self.out.popleft()
                    except IndexError:
                        sleep(0.005)
                parsed, parsed_sa = self.protocol_msg_handle(status_response[1])

            self.msg_buffer.append(binary_msg)
            sleep(0.001)
            binary_response = None
            while not binary_response:
                try:
                    binary_response = self.out.popleft()
                except IndexError:
                    sleep(0.001)

            parsed_binary, binary_sa = self.protocol_msg_handle(binary_response[1])
            if parsed_binary.label == 'Memory Access Response' and binary_sa == index:
                return True
            return False
        elif length <= 892:
            tp_value = CONNECTION_MANAGEMENT_TEMPLATE
            # Build Request to Send Message
            msg_per_cts = 0xff
            total_packets = math.ceil((length * 2 + 1) / 7)
            tp_value['Control byte'] = 16  # Clear to Send
            tp_value['Maximum Number of Packets'] = msg_per_cts
            tp_value['Total Message Size, number of bytes'] = length * 2 + 1  # Total message size, number of bytes
            tp_value['Total Number of Packets'] = total_packets  # Total number of packets
            tp_value['Maximum Number of Packets'] = 0xff  # Reserved, always 0xFF
            temp_pgn = self.j1939_parameters[index]['Binary Data Transfer']
            # binary_pgn = temp_pgn.priority << 18
            # binary_pgn += (temp_pgn.pgn + index)
            binary_pgn = temp_pgn.pgn
            tp_value['Number of Packets that can be sent'] = binary_pgn & 0xff
            tp_value['Next Packet Number to be Sent'] = (binary_pgn & (0xff << 8)) >> 8
            tp_value['Sequence Number'] = (binary_pgn & (0xff << 16)) >> 16
            request_msg = self.protocol_msg_builder('Transport Protocol - Connection Management', self.sa, index, tp_value)
            # print(request_msg)
            response = None
            counter = 0
            while not response and counter < 3:
                try:
                    response = self.out.popleft()
                except IndexError:
                    self.msg_buffer.append(msg)
                    sleep(0.001)
                    response = None
                    counter += 1
            if counter == 3:
                raise J1939TimeoutError
            parsed, parsed_sa = self.protocol_msg_handle(response[1])
            # Wait for proceed
            while not (parsed and parsed.label == 'Memory Access Response' and parsed_sa == index
                       and parsed.spg['Status'].scaled_value == 0):
                self.msg_buffer.append(status_msg)
                status_response = None
                while not status_response:
                    try:
                        status_response = self.out.popleft()
                    except IndexError:
                        sleep(0.005)
                parsed, parsed_sa = self.protocol_msg_handle(status_response[1])
            # print('Proceed')
            self.msg_buffer.append(request_msg)

            # Wait for Clear to Send
            counter = 0
            while not (parsed and parsed.label == 'Transport Protocol - Connection Management' and parsed_sa == index
                       and parsed.spg['Number of Packets that can be sent'].scaled_value == tp_value['Number of Packets that can be sent']
                       and parsed.spg['Next Packet Number to be Sent'].scaled_value == tp_value['Next Packet Number to be Sent']
                       and parsed.spg['Sequence Number'].scaled_value == tp_value['Sequence Number']
                       and parsed.spg['Control byte'].scaled_value == 17
                       and (int(parsed.spg['Total Message Size, number of bytes'].scaled_value) & (0xff << 8)) >> 8 == 1
                       and parsed.spg['Total Number of Packets'].scaled_value == 0xff
                       and parsed.spg['Maximum Number of Packets'].scaled_value == 0xff):
                # and parsed.spg['Total Message Size, number of bytes'].scaled_value == tp_value['Total Message Size, number of bytes'] + 1):
                # self.msg_buffer.append(status_msg)
                sleep(0.001)
                status_response = None
                while not status_response:
                    try:
                        status_response = self.out.popleft()
                    except IndexError:
                        sleep(0.005)
                        counter += 1
                    finally:
                        if counter > 10:
                            return False

                parsed, parsed_sa = self.protocol_msg_handle(status_response[1])
            # print('Clear to send')
            msg_per_cts = int(parsed.spg['Total Message Size, number of bytes'].scaled_value) & 0xff
            carry_over = 0

            binary_values = DATA_TRANSFER_TEMPLATE
            binary_values['Sequence Number'] = 1
            binary_values['Raw Byte Data 1'] = 0xff

            if msg_per_cts < 0xff:  # Multipacket in separated CTS
                for i in range(int(total_packets / msg_per_cts)):
                    for j in range(int(msg_per_cts)):
                        if j % 2 == 1:
                            binary_values['Sequence Number'] = i * msg_per_cts + j + 1
                            for k in range(3):
                                try:
                                    raw_value = value[i * msg_per_cts + int(j * 3.5) + k]
                                except IndexError:
                                    binary_values[f'Raw Byte Data {1 + 2 * k}'] = 0xff
                                    binary_values[f'Raw Byte Data {2 + 2 * k}'] = 0xff
                                    continue
                                if scaled:
                                    self.asi_parameters[names[i * msg_per_cts + int(j * 3.5) + k]].Value = raw_value
                                    scale = get_scale_value(self.asi_parameters[names[i * msg_per_cts + int(j * 3.5) + k]].Scale)
                                    raw_value = raw_value * scale
                                if raw_value > 32768:
                                    raw_value = raw_value - 65536
                                binary_values[f'Raw Byte Data {1 + 2 * k}'] = int(raw_value) & 0xff
                                binary_values[f'Raw Byte Data {2 + 2 * k}'] = (int(raw_value) & (0xff << 8)) >> 8
                            try:
                                raw_value = value[i * msg_per_cts + int(j * 3.5) + 3]
                            except IndexError:
                                binary_values[f'Raw Byte Data 7'] = 0xff
                            else:
                                if scaled:
                                    self.asi_parameters[names[i * msg_per_cts + int(j * 3.5) + 3]].Value = raw_value
                                    scale = get_scale_value(self.asi_parameters[names[i * msg_per_cts + int(j * 3.5) + 3]].Scale)
                                    raw_value = raw_value * scale
                                if raw_value > 32768:
                                    raw_value = raw_value - 65536
                                binary_values['Raw Byte Data 7'] = int(raw_value) & 0xff
                                carry_over = (int(raw_value) & (0xff << 8)) >> 8
                        elif j == 0:
                            for k in range(3):
                                try:
                                    raw_value = value[i * msg_per_cts + k]
                                except IndexError:
                                    binary_values[f'Raw Byte Data {2 + 2 * k}'] = 0xff
                                    binary_values[f'Raw Byte Data {3 + 2 * k}'] = 0xff
                                    continue
                                if scaled:
                                    self.asi_parameters[names[i * msg_per_cts + k]].Value = raw_value
                                    scale = get_scale_value(self.asi_parameters[names[i * msg_per_cts + k]].Scale)
                                    raw_value = raw_value * scale
                                if raw_value > 32768:
                                    raw_value = raw_value - 65536
                                binary_values[f'Raw Byte Data {2 + 2 * k}'] = int(raw_value) & 0xff
                                binary_values[f'Raw Byte Data {3 + 2 * k}'] = (int(raw_value) & (0xff << 8)) >> 8
                        elif j % 2 == 0:
                            binary_values['Sequence Number'] = i * msg_per_cts + j + 1
                            # Stitch up carried over value
                            binary_values['Raw Byte Data 1'] = carry_over
                            carry_over = 0
                            # Rest of the message
                            for k in range(3):
                                try:
                                    raw_value = value[i * msg_per_cts + int(j * 3.5) + k + 1]
                                except IndexError:
                                    binary_values[f'Raw Byte Data {2 + 2 * k}'] = 0xff
                                    binary_values[f'Raw Byte Data {3 + 2 * k}'] = 0xff
                                    continue
                                if scaled:
                                    self.asi_parameters[names[i * msg_per_cts + int(j * 3.5) + k + 1]].Value = raw_value
                                    scale = get_scale_value(self.asi_parameters[names[i * msg_per_cts + int(j * 3.5) + k + 1]].Scale)
                                    raw_value = raw_value * scale
                                if raw_value > 32768:
                                    raw_value = raw_value - 65536
                                binary_values[f'Raw Byte Data {2 + 2 * k}'] = int(raw_value) & 0xff
                                binary_values[f'Raw Byte Data {3 + 2 * k}'] = (int(raw_value) & (0xff << 8)) >> 8

                        self.msg_buffer.append(self.protocol_msg_builder('Transport Protocol - Data Transfer', self.sa,
                                                                         index, binary_values))

                    # Wait for Clear to Send
                    while not (parsed.label == 'Transport Protocol - Connection Management' and parsed_sa == index
                               and parsed.spg['Number of Packets that can be sent'].scaled_value == tp_value[
                                   'Number of Packets that can be sent']
                               and parsed.spg['Next Packet Number to be Sent'].scaled_value == tp_value[
                                   'Next Packet Number to be Sent']
                               and parsed.spg['Sequence Number'].scaled_value == tp_value['Sequence Number']
                               and parsed.spg['Control byte'].scaled_value == 17
                               and (int(parsed.spg['Total Message Size, number of bytes'].scaled_value) &
                                    (0xff << 8)) >> 8 == (i + 1) * msg_per_cts + 1
                               and parsed.spg['Total Number of Packets'].scaled_value == 0xff
                               and parsed.spg['Maximum Number of Packets'].scaled_value == 0xff):
                        # and parsed.spg['Total Message Size, number of bytes'].scaled_value == tp_value['Total Message Size, number of bytes'] + 1):
                        # self.msg_buffer.append(status_msg)
                        sleep(0.001)
                        status_response = None
                        while not status_response:
                            try:
                                status_response = self.out.popleft()
                            except IndexError:
                                sleep(0.005)

                        parsed, parsed_sa = self.protocol_msg_handle(status_response[1])
            else:
                for j in range(int(total_packets)):
                    if j % 2 == 1:
                        binary_values['Sequence Number'] = j + 1
                        for k in range(3):
                            try:
                                raw_value = value[int(j * 3.5) + k]
                            except IndexError:
                                binary_values[f'Raw Byte Data {1 + 2 * k}'] = 0xff
                                binary_values[f'Raw Byte Data {2 + 2 * k}'] = 0xff
                                continue
                            if scaled:
                                self.asi_parameters[names[int(j * 3.5) + k]].Value = raw_value
                                scale = get_scale_value(self.asi_parameters[names[int(j * 3.5) + k]].Scale)
                                raw_value = raw_value * scale
                            if raw_value > 32768:
                                raw_value = raw_value - 65536
                            binary_values[f'Raw Byte Data {1 + 2 * k}'] = int(raw_value) & 0xff
                            binary_values[f'Raw Byte Data {2 + 2 * k}'] = (int(raw_value) & (0xff << 8)) >> 8
                        try:
                            raw_value = value[int(j * 3.5) + 3]
                        except IndexError:
                            binary_values[f'Raw Byte Data 7'] = 0xff
                        else:
                            if scaled:
                                self.asi_parameters[names[int(j * 3.5) + 3]].Value = raw_value
                                scale = get_scale_value(self.asi_parameters[names[int(j * 3.5) + 3]].Scale)
                                raw_value = raw_value * scale
                            if raw_value > 32768:
                                raw_value = raw_value - 65536
                            binary_values['Raw Byte Data 7'] = int(raw_value) & 0xff
                            carry_over = (int(raw_value) & (0xff << 8)) >> 8
                    elif j == 0:
                        for k in range(3):
                            try:
                                raw_value = value[k]
                            except IndexError:
                                binary_values[f'Raw Byte Data {2 + 2 * k}'] = 0xff
                                binary_values[f'Raw Byte Data {3 + 2 * k}'] = 0xff
                                continue
                            if scaled:
                                self.asi_parameters[names[k]].Value = raw_value
                                scale = get_scale_value(self.asi_parameters[names[k]].Scale)
                                raw_value = raw_value * scale
                            if raw_value > 32768:
                                raw_value = raw_value - 65536
                            binary_values[f'Raw Byte Data {2 + 2 * k}'] = int(raw_value) & 0xff
                            binary_values[f'Raw Byte Data {3 + 2 * k}'] = (int(raw_value) & (0xff << 8)) >> 8
                    elif j % 2 == 0:
                        binary_values['Sequence Number'] = j + 1
                        # Stitch up carried over value
                        binary_values['Raw Byte Data 1'] = carry_over
                        carry_over = 0
                        # Rest of the message
                        for k in range(3):
                            try:
                                raw_value = value[int(j * 3.5) + k]
                            except IndexError:
                                binary_values[f'Raw Byte Data {2 + 2 * k}'] = 0xff
                                binary_values[f'Raw Byte Data {3 + 2 * k}'] = 0xff
                                continue
                            if scaled:
                                self.asi_parameters[names[int(j * 3.5) + k]].Value = raw_value
                                scale = get_scale_value(self.asi_parameters[names[int(j * 3.5) + k]].Scale)
                                raw_value = int(raw_value * scale)
                            if raw_value > 32768:
                                raw_value = raw_value - 65536
                            binary_values[f'Raw Byte Data {2 + 2 * k}'] = raw_value & 0xff
                            binary_values[f'Raw Byte Data {3 + 2 * k}'] = (raw_value & (0xff << 8)) >> 8

                    self.msg_buffer.append(self.protocol_msg_builder('Transport Protocol - Data Transfer', self.sa,
                                                                     index, binary_values))
            # Wait for End of Message Acknowledge
            got_response = False
            while not got_response:
                try:
                    response = self.out.popleft()
                except IndexError:
                    sleep(0.001)
                else:
                    got_response = True
            # Wait for Operation Complete
            got_response = False
            while not got_response:
                try:
                    response = self.out.popleft()
                except IndexError:
                    sleep(0.001)
                else:
                    got_response = True
            # first_packet = BINARY_DATA_TRANSFER_FIRST_TEMPLATE
            # for i in range(3):
            #     first_packet[f"Raw Byte Data {1 + 2 * i}"] = value[i] & 0xff
            #     first_packet[f"Raw Byte Data {2 + 2 * i}"] = (value[i] & (0xff << 8)) >> 8
            # first_msg = self.protocol_msg_builder('Binary Data Transfer', self.sa, index, first_packet)
            # mid_packets = []
            # carry_over = 0
            # for i in range(total_packets):
            #     temp = BINARY_DATA_TRANSFER_MIDDLE_TEMPLATE
            #     if i % 2 == 0:
            #         for j in range((length - 3) - 3 * i - 1):
            #             temp[f"Raw Byte Data {1 + 2 * i}"] = value[i * 3 + j + 3] & 0xff
            #             temp[f"Raw Byte Data {2 + 2 * i}"] = (value[i * 3 + j + 3] & (0xff << 8)) >> 8
            #         temp['Raw Byte Data 7'] = value[(i / 2 + 1) * 7 - 1] & 0xff
            #         carry_over = (value[(i / 2 + 1) * 7 - 1] & (0xff << 8)) >> 8
            #     else:
            #         temp['Raw Byte Data 1'] = carry_over
            #         for j in range((length - 3) - 3 * i - 1):
            #             temp[f"Raw Byte Data {2 + 2 * i}"] = value[i * 3 + j + 3] & 0xff
            #             temp[f"Raw Byte Data {3 + 2 * i}"] = (value[i * 3 + j + 3] & (0xff << 8)) >> 8
            #         carry_over = 0
            #
            #     mid_msg = self.protocol_msg_builder('Binary Data Transfer', self.sa, index, temp)
            #     mid_packets.append(mid_msg)
            #     final_packet = BINARY_DATA_TRANSFER_MIDDLE_TEMPLATE
            #     for i in range(int(((length - 3) * 2) % 7)):
            #         final_packet[f"Raw Byte Data {1 + 2 * i}"] = value[i] & 0xff
            #         final_packet[f"Raw Byte Data {2 + 2 * i}"] = (value[i] & (0xff << 8)) >> 8
            return True
        return False

    def _parse_msg(self, msg_in, msg_out):
        # try:
        if self.pgn_msg_handle(msg_in):
            return
        self.out.append((msg_out, msg_in))
        # except KeyError:
        #     pass
