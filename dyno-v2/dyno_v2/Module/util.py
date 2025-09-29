"""util.py: Utility static methods for DynoController"""

__version__ = '0.0.1'

from dyno_v2.Module.Parameter import Parameter
from lxml import etree
import logging
from socket import gethostname, gethostbyname_ex

logging.basicConfig(level=logging.WARNING)
# Helper methods


def signed(value):
    if value & (1 << 15) > 0:
        # This is a negative number
        value -= (1 << 16)
    return value


def get_scale_value(scale):
    if (scale == "enum" or
            scale == "bit vector" or
            scale == "hex"):
        scale = 1

    elif isinstance(scale, str):
        try:
            scale = float(scale)
        except ValueError:
            scale = 1

    return scale


def load_using_param_names(tree, names):
    dictionary = {}
    with open(names) as f:
        f.readline()
        for line in f.readlines():
            if line == "\n":
                continue

            name = line.strip()
            if name == "Open circuit voltage test window":
                name = "Open circuit voltage test window "
            element = tree.find("//ParameterDescription[Name='%s']" % name)
            # There can be situations where some Object Dictionaries have a parameter and others don't
            # Eg. Object dictionaries released from 6.020 onward don't have "Flash Write Parameter Access Code",
            #     but ones released with 6.019 do., KS, 3/09/2022
            try:
                parameter = Parameter()
                parameter.set_using_xml_element(element)

            except AttributeError as a_e:
                logging.debug(name, a_e)

            dictionary[name] = parameter
    return dictionary


def parse_etree(object_dictionary):
    try:
        tree = etree.parse(object_dictionary)
        return tree
    except FileNotFoundError as f_e:
        print(f_e)
        print(
            "There needs to be an object dictionary for ASIController to load bit descriptions for faults(258), "
            "faults2(299), warnings(277), and warnings2(359)")
        # sys.exit()

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def _get_ip():
    all_ip = [ip for ip in gethostbyname_ex(gethostname())[2] if ip.startswith("192.168.1.")]
    found = [0]
    for ip in all_ip:
        found.append(ip.split('.')[-1])
    return found
