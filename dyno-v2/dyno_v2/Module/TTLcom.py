from time import sleep
import minimalmodbus
import serial
import logging
from dyno_v2.Module.ComABC import ComABC
from dyno_v2.Module.Parameter import Parameter
from dyno_v2.Module.util import *
from dyno_v2.Module.exceptions import *


class TTLcom(ComABC):

    def __init__(
            self,
            com_port='COM5',
            baud_rate=115200,
            mbAddress=1
    ):
        self.portName = str(com_port)
        self.bit_rate = int(baud_rate)
        self.id = int(mbAddress)

        print(f"Connecting to instrument @: port {self.portName} baud {self.bit_rate}, ID: {self.id}")
        try:
            self.modbus = minimalmodbus.Instrument(port=self.portName, slaveaddress=self.id)
        except serial.serialutil.SerialException:
            print("Error: Bad Connection!")
            return
        self.modbus.serial.baudrate = baud_rate
        self.modbus.serial.timeout = 1

        self.run_parameters = None

        self.warnings = 0
        self.faults = 0
        self.checksums = 0
        self.com_loss = 0
        self.checksum_retry = 4
        self.checksum_retry_interval = 0.0001  # seconds; haven't attempted lower intervals

        self.pointerTableParameters = []

    def clearPointerTable(self):
        self.pointerTableParameters = []
        self.modbus.write_registers(0x600, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def writePointerTable(self):
        self.modbus.write_registers(0x600, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        if 0 < len(self.pointerTableParameters) <= 10:
            # We have a valid number of parameters, poke them into place
            ptableAddresses = []
            for param in self.pointerTableParameters:
                ptableAddresses.append(param.Address)

            self.modbus.write_registers(0x600, ptableAddresses)

    def addParameterToPointerTable(self, parameter: Parameter):
        if len(self.pointerTableParameters) < 10:
            # We have room in the pointer table
            self.pointerTableParameters.append(parameter)

            # Now set up the pointer table in the BAC
            self.writePointerTable()

    def removeParameterFromPointerTable(self, parameter: Parameter):
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
            pTableValues[i] /= get_scale_value(self.pointerTableParameters[i].Scale)

            returnList.append((self.pointerTableParameters[i], pTableValues[i]))

        return returnList

    def controller_parameter(self, params):
        self.run_parameters = params

    def read(self, name):
        if isinstance(name, str):
            try:
                param = self.run_parameters[name]
            except KeyError:
                logging.warning(f"TTL Read: {name} not in run parameters")
                raise NotInRunParameterError
            previous_value = param.Value
            if previous_value is None:
                previous_value = 0
            try:
                address = int(param.Address)
            except TypeError:
                return previous_value
            scale = param.Scale
            scale = get_scale_value(scale)
        elif isinstance(name, int):
            address = name
        else:
            raise TypeError(f"Wrong name type: {type(name)} not str or int")

        try:
            value = signed(int(self.modbus.read_register(address)))

        except KeyboardInterrupt:
            print(f"\n\n\n\n\n\n\nInterrupted")
            if isinstance(name, str):
                return previous_value
            else:
                return 0
        except AttributeError:
            if isinstance(name, str):
                return previous_value
            else:
                return 0
        except (TypeError, minimalmodbus.InvalidResponseError,
                serial.serialutil.SerialException) as e:
            error = e
            logging.warning(f"{self.portName} - {e}")
            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                self.checksums += 1
                # print("")
                attempt = 0
                while "Checksum error" in str(error) or "WriteFile failed" in str(error):
                    attempt += 1
                    if attempt < self.checksum_retry:
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: Read attempt {attempt} for {name}")
                        try:
                            value = signed(int(self.modbus.read_register(address)))
                        except (TypeError, OSError, ValueError, AttributeError,
                                minimalmodbus.InvalidResponseError,
                                serial.serialutil.SerialException) as e:
                            error = e
                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                self.checksums += 1
                            continue
                        except KeyboardInterrupt as k:
                            if isinstance(name, str):
                                return previous_value
                            else:
                                return 0
                        else:
                            if isinstance(name, str):
                                value = value / scale
                                if param.Scale == 'hex' and value < 0:
                                    value += 65536
                                param.Value = value
                                return value
                            else:
                                return value

                    else:
                        logging.warning(f"\n{self.portName} Reading {name} failed")
                        if isinstance(name, str):
                            return previous_value
                        else:
                            return 0
        except minimalmodbus.NoResponseError as e:
            error = e
            if "No communication" in str(error):
                logging.warning(f"{self.portName} when Reading {name} - {error}")
                self.com_loss += 1
                logging.info(f"{self.portName} COM LOSS: {self.com_loss}")

                # print("")
                attempt = 0
                while "No communication" in str(error):
                    if attempt < self.checksum_retry:
                        attempt += 1
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: Reconnect attempt {attempt} when reading {name}")

                        try:
                            self.modbus.serial.close()
                            sleep(0.1)
                            self.modbus.serial.open()
                            value = signed(int(self.modbus.read_register(address)))
                        except minimalmodbus.NoResponseError as e:
                            logging.warning(f"{self.portName} - TTL: {e}")
                            self.com_loss += 1
                            logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                            continue
                        except (TypeError, minimalmodbus.InvalidResponseError,
                                serial.serialutil.SerialException) as e:
                            logging.warning(f"{self.portName} - TTL: {e}")
                            error = e
                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                self.checksums += 1
                                attempt = 0
                                while "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                    if attempt < self.checksum_retry:
                                        attempt += 1
                                        sleep(self.checksum_retry_interval)
                                        logging.warning(f"{self.portName}: Read attempt {attempt} for {name}")
                                        try:
                                            value = signed(int(self.modbus.read_register(address)))
                                        except (TypeError, OSError, ValueError, AttributeError,
                                                minimalmodbus.InvalidResponseError,
                                                serial.serialutil.SerialException) as e:
                                            error = e
                                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                                self.checksums += 1
                                            continue
                                        except KeyboardInterrupt as k:
                                            if isinstance(name, str):
                                                return previous_value
                                            else:
                                                return 0
                                        else:
                                            if isinstance(name, str):
                                                value = value / scale
                                                if param.Scale == 'hex' and value < 0:
                                                    value += 65536
                                                param.Value = value
                                                return value
                                            else:
                                                return value
                                    else:
                                        if isinstance(name, str):
                                            return previous_value
                                        else:
                                            return 0
                            continue
                        except KeyboardInterrupt:
                            if isinstance(name, str):
                                return previous_value
                            else:
                                return 0
                        else:
                            self.com_loss = 0
                            if isinstance(name, str):
                                value = value / scale
                                if param.Scale == 'hex' and value < 0:
                                    value += 65536
                                param.Value = value
                                return value
                            else:
                                return value
                    else:
                        self.com_loss += 1
                        print(f"\n{self.portName} - Connection lost...")
                        # del self.modbus
                        raise CommLossError
                if isinstance(name, str):
                    return previous_value
                else:
                    return 0
        else:
            self.com_loss = 0
            if isinstance(name, str):
                value = value / scale
                if param.Scale == 'hex' and value < 0:
                    value += 65536
                param.Value = value
                return value
            else:
                return value

    def write(self, name, value):
        if isinstance(name, str):
            try:
                param = self.run_parameters[name]
            except KeyError:
                logging.warning(f"TTL Write: {name} not in run parameters")
                raise NotInRunParameterError
            try:
                address = int(param.Address)
            except TypeError:
                return False

            scale = param.Scale

            if value > 32768:
                value = value - 65536

            if scale:
                scale = get_scale_value(scale)
                value = value * scale
        elif isinstance(name, int):
            address = name
        else:
            return False

        try:
            self.modbus.write_register(address, value, 0, 16, True)
        except KeyboardInterrupt:
            print(f"\n\n\n\n\n\n\nInterrupted")
            return False
        except AttributeError:
            return False
        except (minimalmodbus.InvalidResponseError,
                serial.serialutil.SerialException) as e:
            error = e
            logging.warning(f"\n{self.portName} - {e}\n")
            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                self.checksums += 1
                # print("")
                attempt = 0
                while "Checksum error" in str(error) or "WriteFile failed" in str(error):
                    if attempt < self.checksum_retry:
                        attempt += 1
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: Write attempt {attempt} for {name}")
                        try:
                            self.modbus.write_register(address, value,
                                                       number_of_decimals=0,
                                                       functioncode=16,
                                                       signed=True)
                        except (TypeError, OSError, ValueError, AttributeError,
                                minimalmodbus.InvalidResponseError,
                                serial.serialutil.SerialException) as e:
                            error = e
                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                self.checksums += 1
                            continue
                        except KeyboardInterrupt as k:
                            return False
                        else:
                            if isinstance(name, str):
                                if value / scale == self.read(name):
                                    param.Value = value / scale
                            return True
                    else:
                        logging.warning(f"\n{self.portName} Write to {name} failed")
                        return False
        except (OSError, ValueError, minimalmodbus.NoResponseError) as e:
            error = e
            if "No communication" in str(error):
                logging.warning(f"\n{self.portName} when Writing {name} - {error}")
                self.com_loss += 1
                logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                attempt = 0
                while "No communication" in str(error):
                    attempt += 1
                    if attempt < self.checksum_retry:
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: Reconnect attempt {attempt} when writing {name}")

                        try:
                            self.modbus.serial.close()
                            sleep(0.1)
                            self.modbus.serial.open()
                            self.modbus.write_register(address, value, number_of_decimals=0,
                                                       functioncode=16, signed=True)
                        except minimalmodbus.NoResponseError as e:
                            logging.warning(f"{self.portName} - TTL: {e}")
                            self.com_loss += 1
                            logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                            continue
                        except (OSError, ValueError,
                                minimalmodbus.InvalidResponseError,
                                serial.serialutil.SerialException) as e:
                            error = e
                            logging.warning(f"\n{self.portName} - {e}\n")
                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                self.checksums += 1
                                # print("")
                                attempt = 0
                                while "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                    if attempt < self.checksum_retry:
                                        attempt += 1
                                        sleep(self.checksum_retry_interval)
                                        logging.warning(f"{self.portName}: Write attempt {attempt} for {name}")
                                        try:
                                            self.modbus.write_register(address, value,
                                                                       number_of_decimals=0,
                                                                       functioncode=16,
                                                                       signed=True)
                                        except (TypeError, OSError, ValueError, AttributeError,
                                                minimalmodbus.InvalidResponseError,
                                                serial.serialutil.SerialException) as e:
                                            error = e
                                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                                self.checksums += 1
                                            continue
                                        except KeyboardInterrupt as k:
                                            return False
                                        else:
                                            if isinstance(name, str):
                                                if value / scale == self.read(name):
                                                    param.Value = value / scale
                                            return True
                                    else:
                                        logging.warning(f"\n{self.portName} Write to {name} failed")
                                        return False
                            continue
                        except KeyboardInterrupt:
                            return False
                        else:
                            if isinstance(name, str):
                                if value / scale == self.read(name):
                                    param.Value = value / scale
                            self.com_loss = 0
                            return True
                    else:
                        self.com_loss += 1
                        print(f"\n{self.portName} - Connection lost...")
                        # del self.modbus
                        raise CommLossError

                return False
        else:
            self.com_loss = 0
            if isinstance(name, str):
                param.Value = value
            return True

    def mass_read(self, address, length=1):

        try:
            values = self.modbus.read_registers(address, length)

        except (TypeError, minimalmodbus.InvalidResponseError,
                serial.serialutil.SerialException) as e:
            error = e
            logging.warning(f"{self.portName} - {e}")
            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                self.checksums += 1
                # print("")
                attempt = 0
                while "Checksum error" in str(error) or "WriteFile failed" in str(error):
                    attempt += 1
                    if attempt < self.checksum_retry:
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: "
                                        f"Mass read attempt {attempt} for address {address} and length {length}")
                        try:
                            values = self.modbus.read_registers(address, length)
                        except (TypeError, OSError, ValueError, AttributeError,
                                minimalmodbus.InvalidResponseError,
                                serial.serialutil.SerialException) as e:
                            error = e
                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                self.checksums += 1
                            continue
                        else:
                            return values

                    else:
                        print(f"\n{self.portName} Mass reading address {address} and length {length} failed")
                        return [0] * length
        except minimalmodbus.NoResponseError as e:
            error = e
            if "No communication" in str(error):
                logging.warning(f"{self.portName} when Mass reading address {address} and length {length} - {error}")
                self.com_loss += 1
                logging.info(f"{self.portName} COM LOSS: {self.com_loss}")

                attempt = 0
                while "No communication" in str(error):
                    if attempt < self.checksum_retry:
                        attempt += 1
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: "
                                        f"Reconnect attempt {attempt} when "
                                        f"Mass reading address {address} and length {length}")

                        try:
                            self.modbus.serial.close()
                            sleep(0.1)
                            self.modbus.serial.open()
                            values = self.modbus.read_registers(address, length)
                        except minimalmodbus.NoResponseError as e:
                            logging.warning(f"{self.portName} - TTL: {e}")
                            self.com_loss += 1
                            logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                            continue
                        except (TypeError, minimalmodbus.InvalidResponseError,
                                serial.serialutil.SerialException) as e:
                            logging.warning(f"{self.portName} - TTL: {e}")
                            error = e
                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                self.checksums += 1
                                attempt = 0
                                while "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                    if attempt < self.checksum_retry:
                                        attempt += 1
                                        sleep(self.checksum_retry_interval)
                                        logging.warning(f"{self.portName}: "
                                                        f"Mass read attempt {attempt} for "
                                                        f"address {address} and length {length}")
                                        try:
                                            values = self.modbus.read_registers(address, length)
                                        except (TypeError, OSError, ValueError, AttributeError,
                                                minimalmodbus.InvalidResponseError,
                                                serial.serialutil.SerialException) as e:
                                            error = e
                                            if "Checksum error" in str(error) or "WriteFile failed" in str(error):
                                                self.checksums += 1
                                            continue
                                        else:
                                            return values
                                    else:
                                        return [0] * length
                            continue
                        else:
                            self.com_loss = 0
                            return values
                    else:
                        self.com_loss += 1
                        print(f"\n{self.portName} - Connection lost...")
                        # del self.modbus
                        raise CommLossError
                return [0] * length
        else:
            self.com_loss = 0
            return values