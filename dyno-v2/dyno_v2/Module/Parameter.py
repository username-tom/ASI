import logging
import xml.etree.ElementTree as ET


# gets an attribute from an xml element
def get(attribute, xml):
    return xml.find(attribute).text


class Bit:
    def __init__(self, key=None, position=None, name=None, description=None, global_ID=None):
        self.Key = key
        self.Position = position
        self.Name = name
        self.Description = description
        self.Global_ID = global_ID


class Enum:
    def __init__(self, key=None, value=None, description=None, global_id=None):
        self.Key = key
        self.Value = value
        self.Description = description
        self.Global_ID = global_id


class Parameter:
    def __init__(
            self,
            name=None,
            address=None,
            scale=None,
            units=None,
            key=None,
            flash=None,
            access_level=None,
            read=None,
            write=None,
            value=None,
            website=None,
            description=None,
            index=None,
            field=None,
            element=None,
            enumerations=None,
            bits=None
    ):

        # only address and value are used in our parameter files
        self.Name = name
        self.Address = address
        self.Scale = scale
        self.Units = units

        self.Key = key
        self.Flash = flash
        self.AccessLevel = access_level
        self.Read = read

        self.Write = write
        self.Value = value
        self.Website = website
        self.Description = description

        self.index = index
        self.field = field
        self.element = element
        self.Enumerations = {}
        if enumerations is not None:
            self.Enumerations = enumerations
        self.Bits = {}
        if bits is not None:
            self.Bits = bits

    def __str__(self):
        return f'{str(self.Name)} | [{str(self.Address)}] = {str(self.Value)} {self.Units}'

    # not all parameters in an object dictionary have 'Flash' bool, or a 'Website' or 'Units', 
    # so we have to check that they exist first,
    # otherwise, we'll get this error:
    # "AttributeError: 'NoneType' object has no attribute 'text'"
    #
    # Kent, 11/26/2021
    def set_using_xml_element(self, xml):

        self.Address = get('Address', xml)
        key = xml.find('Key')
        if key is not None:
            self.Key = get('Key', xml)

        # got this error message for the units, flash and website lines, so I've changed them accordingly:
        # 'Parameter.py:82: FutureWarning: The behavior of this method will change in future versions. Use specific 'len(elem)' or 'elem is not None' test instead.'
        # KS, 12/20/2021
        flash = xml.find('Flash')
        if flash is not None:
            self.Flash = get('Flash', xml)

        if xml.find('AccessLevel') is not None:
            self.AccessLevel = get('AccessLevel', xml)
        self.Read = get('Read', xml)
        self.Write = get('Write', xml)
        self.Name = get('Name', xml)
        self.Scale = get('Scale', xml)

        units = xml.find('Units')
        if units is not None:
            self.Units = get('Units', xml)

        website = xml.find('Website')
        if website is not None:
            self.Website = get('Website', xml)

        self.Description = get('Description', xml)

        if xml.find('EnumArray') is not None:
            # if 'EnumArray' in xml.find('EnumArray'):
            for enum in xml.find('EnumArray').findall('Enum'):
                key = enum.find('Key')
                value = enum.find('Value')
                description = enum.find('Description')
                global_id = enum.find('GlobalID')

                self.Enumerations[key] = Enum(key, value, description, global_id)

        if xml.find('BitArray') is not None:
            # if 'BitArray' in xml.find('BitArray'):
            for bit in xml.find('BitArray').findall('Bit'):
                key = bit.find('Key')
                position = bit.get('Position')
                name = bit.find('Name')
                description = bit.find('Description')
                global_id = bit.find('GlobalID')

                self.Bits[key] = Bit(key, position, name, description, global_id)
        elif xml.find('BitField') is not None:
            for i, bit in enumerate(xml.find('BitField').findall('string')):
                self.Bits[i] = Bit(position=i, name=bit)