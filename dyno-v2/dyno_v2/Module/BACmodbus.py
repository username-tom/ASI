import logging
import minimalmodbus
import serial
from time import sleep
from dyno_v2.Module.util import *


# Communication settings
##################################

# PORT_NAME = '/dev/tty.usbserial-FTH84XZ1'	 # Format for macOS
# PORT_NAME = 'COM11'						 # Format for Windows
# BAUD_RATE = 19200
# BAUD_RATE = 115200

##################################


class Parameter:
    def __init__(self, name="Parameter", address=0, scale=1, unit="", manual=None, auto=None):
        self.name = name
        self.address = address
        self.scale = scale
        self.unit = unit
        self.manual = manual
        self.autoT = auto

    def __str__(self):
        # Print a description
        return '[%s, %d]' % (self.name, self.address)

    def __repr__(self):
        return '<Parameter ' + self.__str__() + '>'

    def Add_Manual(self, manual):
        self.manual = manual

    def Add_AutoT(self, autoT):
        self.autoT = autoT


class BAC:
    def __init__(self, mbAddress=1, PORT_NAME='COM11', BAUD_RATE=19200):
        print("Connecting to instrument @: port " + str(PORT_NAME) + " baud " + str(BAUD_RATE))
        self.portName = PORT_NAME  # Format for Windows
        self.baudRate = BAUD_RATE
        try:
            self.modbus = minimalmodbus.Instrument(port=self.portName, slaveaddress=mbAddress)
        except serial.serialutil.SerialException:
            print("Error: Bad Connection!")
            return
        self.modbus.serial.baudrate = self.baudRate
        self.modbus.serial.timeout = 1
        self.mbAddress = mbAddress
        self.attempt = 0
        self.warnings = 0
        self.faults = 0
        self.checksums = 0
        self.com_loss = 0
        self.checksum_retry = 4  # Typically only need 1 retry, also used to retry logging to extra files
        self.checksum_retry_interval = 0.0001  # seconds; haven't attempted lower intervals

        self.pointerTableParameters = []

    def close(self):
        self.modbus.serial.close()

    def readParameter(self, parameter):
        # value = signed(self.modbus.read_register(parameter.address))
        # value /= parameter.scale
        #
        # # print("read %.1f %s from address %d - %s" % (value, parameter.unit, parameter.address, parameter.name))
        #
        # return value
        try:
            address = int(parameter.address)
        except TypeError:
            return 0
        scale = parameter.scale

        try:
            self.attempt += 1
            value = signed(int(self.modbus.read_register(address)))
        except AttributeError:
            return 0
        except (TypeError, minimalmodbus.InvalidResponseError) as e:
            error = e
            print(f"{self.portName} - {e}")
            logging.debug(f"{self.portName} - {e}")
            if "Checksum error" in str(error):
                self.checksums += 1
                attempt = 0
                while "Checksum error" in str(error):
                    attempt += 1
                    if attempt < self.checksum_retry:
                        sleep(self.checksum_retry_interval)
                        logging.debug(f"{self.portName}: read attempt {attempt} for {parameter.name}")
                        try:
                            self.attempt += 1
                            value = signed(int(self.modbus.read_register(address)))
                        except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                            error = e
                            if "Checksum error" in str(error):
                                self.checksums += 1
                            continue
                        else:
                            value = value / scale
                            return value
                    else:
                        print(f"\n{self.portName} Reading {parameter.name} failed")
                        return 0
        except minimalmodbus.NoResponseError as e:
            error = e
            print(error)
            if "No communication" in str(error):
                # self.stop_polling()
                # print(f"\n{self.port_name} when Reading {name} - {error}\n")
                self.com_loss += 1
                logging.info(f"{self.portName} COM LOSS: {self.com_loss}")

                # print("")
                attempt = 0
                while "No communication" in str(error):
                    if attempt < self.checksum_retry:
                        attempt += 1
                        sleep(self.checksum_retry_interval)
                        logging.debug(f"{self.portName}: Reconnect attempt {attempt} when reading {parameter.name}")

                        try:
                            self.modbus.serial.close()
                            sleep(0.25)
                            self.modbus.serial.open()
                            sleep(0.25)
                            value = signed(int(self.modbus.read_register(address)))
                        except minimalmodbus.NoResponseError as e:
                            error = e
                            self.com_loss += 1
                            logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                            continue
                        except (TypeError, minimalmodbus.InvalidResponseError) as e:
                            error = e
                            if "Checksum error" in str(error):
                                self.checksums += 1
                                # attempt = 0
                                while "Checksum error" in str(error):
                                    if attempt < self.checksum_retry:
                                        attempt += 1
                                        sleep(self.checksum_retry_interval)
                                        logging.debug(f"{self.portName}: read attempt {attempt} for {parameter.name}")
                                        try:
                                            self.attempt += 1
                                            value = signed(int(self.modbus.read_register(address)))
                                        except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                                            error = e
                                            if "Checksum error" in str(error):
                                                self.checksums += 1
                                            continue
                                        else:
                                            value = value / scale
                                            return value
                                    else:
                                        return 0
                            continue
                        else:
                            self.com_loss = 0
                            value = value / scale
                            return value
                    else:
                        # self.com_loss += 1
                        print(f"\n{self.portName} - Connection lost...")
                        del self.modbus
                        return 0
                return 0
        else:
            self.com_loss = 0
            value = value / scale
            return value

    def writeValueForParameter(self, value, parameter):
        # writeVal = value * parameter.scale
        # self.modbus.write_register(parameter.address, writeVal, 0, 16, True)
        try:
            address = int(parameter.address)
        except TypeError:
            return False
        scale = parameter.scale

        if scale:
            scale = get_scale_value(scale)
            value = value * scale

        try:
            self.modbus.write_register(address, value, 0, 16, True)
        except AttributeError:
            return False
        except minimalmodbus.InvalidResponseError as e:
            error = e
            logging.debug(f"\n{self.portName} - {e}\n")
            if "Checksum error" in str(error):
                self.checksums += 1
                # print("")
                attempt = 0
                while "Checksum error" in str(error):
                    if attempt < self.checksum_retry:
                        attempt += 1
                        sleep(self.checksum_retry_interval)
                        logging.debug(f"{self.portName}: Write attempt {attempt} for {parameter.name}")
                        try:
                            self.modbus.write_register(address, value, number_of_decimals=0, functioncode=16,
                                                       signed=True)
                        except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                            error = e
                            if "Checksum error" in str(error):
                                self.checksums += 1
                            continue
                        else:
                            if value / scale == self.readParameter(parameter):
                                return True
                    else:
                        print(f"\n{self.portName} Write to {parameter.name} failed")
                        return False
        except (OSError, ValueError, minimalmodbus.NoResponseError) as e:
            error = e
            if "No communication" in str(error):
                logging.debug(f"\n{self.portName} when Writing {parameter.name} - {error}")
                self.com_loss += 1
                logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                attempt = 0
                while "No communication" in str(error):
                    attempt += 1
                    if attempt < self.checksum_retry:
                        sleep(self.checksum_retry_interval)
                        logging.debug(f"{self.portName}: Reconnect attempt {attempt} when reading {parameter.name}")

                        try:
                            self.modbus.serial.close()
                            sleep(0.25)
                            self.modbus.serial.open()
                            sleep(0.25)
                            self.modbus.write_register(address, value, number_of_decimals=0,
                                                       functioncode=16, signed=True)
                        except minimalmodbus.NoResponseError as e:
                            error = e
                            self.com_loss += 1
                            logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                            continue
                        except (OSError, ValueError, minimalmodbus.InvalidResponseError) as e:
                            error = e
                            logging.debug(f"\n{self.portName} - {e}\n")
                            if "Checksum error" in str(error):
                                self.checksums += 1
                                # print("")
                                attempt = 0
                                while "Checksum error" in str(error):
                                    if attempt < self.checksum_retry:
                                        attempt += 1
                                        sleep(self.checksum_retry_interval)
                                        logging.debug(f"{self.portName}: Write attempt {attempt} for {parameter.name}")
                                        try:
                                            self.modbus.write_register(address, value, number_of_decimals=0, functioncode=16,
                                                                       signed=True)
                                        except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                                            error = e
                                            if "Checksum error" in str(error):
                                                self.checksums += 1
                                            continue
                                        else:
                                            if value / scale == self.readParameter(parameter):
                                                return True
                                    else:
                                        print(f"\n{self.portName} Write to {parameter.name} failed")
                                        return False
                            continue
                        else:
                            self.com_loss = 0
                            if value / scale == self.readParameter(parameter):
                                return True
                    else:
                        # self.com_loss += 1
                        print(f"\n{self.portName} - Connection lost...")
                        del self.modbus
                        return False

                return False
        else:
            self.com_loss = 0
            return True

    def clearPointerTable(self):
        self.pointerTableParameters = []
        self.modbus.write_registers(0x600, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def writePointerTable(self):
        self.modbus.write_registers(0x600, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        if 0 < len(self.pointerTableParameters) <= 10:
            # We have a valid number of parameters, poke them into place
            ptableAddresses = []
            for param in self.pointerTableParameters:
                ptableAddresses.append(param.address)

            self.modbus.write_registers(0x600, ptableAddresses)

    def addParameterToPointerTable(self, parameter):
        if len(self.pointerTableParameters) < 10:
            # We have room in the pointer table
            self.pointerTableParameters.append(parameter)

            # Now set up the pointer table in the BAC
            self.writePointerTable()

    def removeParameterFromPointerTable(self, parameter):
        if parameter in self.pointerTableParameters:
            self.pointerTableParameters.remove(parameter)
            self.writePointerTable()

    # Returns a list of tuples (Parameter, value)
    def readPointerTableParameters(self):

        if not 0 < len(self.pointerTableParameters) <= 10:
            # No valid pointer table parameters
            return []  # Send back an empty list

        pTableValues = self.modbus.read_registers(0x600, len(self.pointerTableParameters))

        returnList = []

        for i in range(0, len(self.pointerTableParameters)):
            # Scale the values we received
            pTableValues[i] = signed(pTableValues[i])
            pTableValues[i] /= get_scale_value(self.pointerTableParameters[i].scale)

            returnList.append((self.pointerTableParameters[i], pTableValues[i]))

        return returnList


"""
def example():
    # Create the parameters we will be using
    MB_BatteryVoltage = Parameter("Battery voltage", 265, 32, "V")
    MB_MotorTemperature = Parameter("Motor temperature", 261, 1, "ºC")

    # Create the BAC we will interface with
    controller = BAC()

    # read some parameters
    voltage = controller.readParameter(MB_BatteryVoltage)
    print("read %.1f %s from address %d - %s" % (
        voltage, MB_BatteryVoltage.unit, MB_BatteryVoltage.address, MB_BatteryVoltage.name))

    temperature = controller.readParameter(MB_MotorTemperature)
    print("read %.1f %s from address %d - %s" % (
        temperature, MB_MotorTemperature.unit, MB_MotorTemperature.address, MB_MotorTemperature.name))

    # Set up the pointer table for fast polling
    controller.addParameterToPointerTable(MB_BatteryVoltage)
    controller.addParameterToPointerTable(MB_MotorTemperature)
    controller.removeParameterFromPointerTable(MB_BatteryVoltage)
    pTable = controller.readPointerTableParameters()

    for parameter, value in pTable:
        print("read %.1f %s for %s using the BAC pointer table" % (value, parameter.unit, parameter.name))

# example()
"""

