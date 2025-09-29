from time import sleep
import minimalmodbus
import serial
from Module.ComABC import ComABC
from Module.util import *

class CommError(Exception):
    pass


class TTLcom(ComABC):

    def __init__(self, com_port='COM5', baud_rate=115200, mbAddress=1):
        self.portName = str(com_port)
        self.bit_rate = int(baud_rate)
        self.id = int(mbAddress)

        # print(f"Connecting | Port {self.portName} | Baud {self.bit_rate} | ID: {self.id}")
        try:
            self.modbus = minimalmodbus.Instrument(port=self.portName, slaveaddress=self.id)
        except serial.serialutil.SerialException:
            # print("Error: Bad Connection!")
            return
        self.modbus.serial.baudrate = baud_rate
        self.modbus.serial.timeout = 1

        self.run_parameters = None

        self.warnings = 0
        self.faults = 0
        self.checksums = 0
        self.com_loss = 0
        self.checksum_retry = 5
        self.checksum_retry_interval = 0.001  # seconds; haven't attempted lower intervals

    def controller_parameter(self, params):
        self.run_parameters = params

    def read(self, name: str):
        if self.com_loss > self.checksum_retry:
            return False
        try:
            param = self.run_parameters[name]
        except KeyError:
            logging.warning("Trying to read a parameter not in run")
            return 0
        previous_value = param.Value
        if previous_value is None:
            previous_value = 0
        try:
            address = int(param.Address)
        except TypeError:
            return previous_value
        scale = param.Scale
        scale = get_scale_value(scale)

        try:
            value = signed(int(self.modbus.read_register(address)))
        except serial.serialutil.SerialException:
            return previous_value
        except KeyboardInterrupt:
            return previous_value
        except AttributeError:
            return previous_value
        except (TypeError, minimalmodbus.InvalidResponseError) as e:
            error = e
            logging.warning(f"{self.portName} - {e}")
            if "Checksum error" in str(error):
                self.checksums += 1
                attempt = 0
                while "Checksum error" in str(error):
                    attempt += 1
                    if attempt < self.checksum_retry:
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: Read attempt {attempt} for {name}")
                        try:
                            value = signed(int(self.modbus.read_register(address)))
                        except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                            error = e
                            if "Checksum error" in str(error):
                                self.checksums += 1
                            continue
                        except KeyboardInterrupt:
                            return previous_value
                        else:
                            value = value / scale
                            if param.Scale in ['hex', 'bit vector'] and value < 0:
                                value += 65536
                            param.Value = value
                            return value
                    else:
                        return previous_value
        except minimalmodbus.NoResponseError as e:
            error = e
            if "No communication" in str(error):
                logging.warning(f"{self.portName} when Reading {name} - {error}")
                self.com_loss += 1
                logging.info(f"{self.portName} COM LOSS: {self.com_loss}")

                attempt = 0
                while "No communication" in str(error) and attempt < self.checksum_retry:

                    attempt += 1
                    sleep(self.checksum_retry_interval)
                    logging.warning(f"{self.portName}: Reconnect attempt {attempt} when reading {name}")

                    try:
                        self.modbus.serial.close()
                        sleep(0.25)
                        self.modbus.serial.open()
                        sleep(0.25)
                        value = signed(int(self.modbus.read_register(address)))
                    except minimalmodbus.NoResponseError as e:
                        logging.warning(f"{self.portName} - TTL: {e}")
                        self.com_loss += 1
                        logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                        if self.com_loss > self.checksum_retry:
                            return False
                    except (TypeError, minimalmodbus.InvalidResponseError) as e:
                        logging.warning(f"{self.portName} - TTL: {e}")
                        error = e
                        if "Checksum error" in str(error):
                            self.checksums += 1
                            attempt = 0
                            while "Checksum error" in str(error):
                                if attempt < self.checksum_retry:
                                    attempt += 1
                                    sleep(self.checksum_retry_interval)
                                    logging.warning(f"{self.portName}: Read attempt {attempt} for {name}")
                                    try:
                                        value = signed(int(self.modbus.read_register(address)))
                                    except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                                        error = e
                                        if "Checksum error" in str(error):
                                            self.checksums += 1
                                        continue
                                    except KeyboardInterrupt:
                                        return previous_value
                                    else:
                                        value = value / scale
                                        if param.Scale in ['hex', 'bit vector'] and value < 0:
                                            value += 65536
                                        param.Value = value
                                        return value
                                else:
                                    return previous_value
                        continue
                    except KeyboardInterrupt:
                        return previous_value
                    else:
                        self.com_loss = 0
                        value = value / scale
                        if param.Scale in ['hex', 'bit vector'] and value < 0:
                            value += 65536
                        param.Value = value
                        return value

                return False
            return previous_value
        else:
            self.com_loss = 0
            value = value / scale
            if param.Scale in ['hex', 'bit vector'] and value < 0:
                value += 65536
            param.Value = value
            return value

    def write(self, name, value):
        if self.com_loss > self.checksum_retry:
            return False
        if isinstance(name, str):
            param = self.run_parameters[name]
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
            return False
        except AttributeError:
            return False
        except minimalmodbus.InvalidResponseError as e:
            error = e
            logging.warning(f"\n{self.portName} - {e}\n")
            if "Checksum error" in str(error):
                self.checksums += 1
                attempt = 0
                while "Checksum error" in str(error):
                    if attempt < self.checksum_retry:
                        attempt += 1
                        sleep(self.checksum_retry_interval)
                        logging.warning(f"{self.portName}: Write attempt {attempt} for {name}")
                        try:
                            self.modbus.write_register(address, value, number_of_decimals=0, functioncode=16,
                                                       signed=True)
                        except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                            error = e
                            if "Checksum error" in str(error):
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
                        # print(f"\n{self.portName} write to {name} failed")
                        return False
        except (OSError, ValueError, minimalmodbus.NoResponseError) as e:
            error = e
            if "No communication" in str(error):
                logging.warning(f"\n{self.portName} when Writing {name} - {error}")
                self.com_loss += 1
                logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                attempt = 0
                while "No communication" in str(error) and attempt < self.checksum_retry:
                    attempt += 1
                    sleep(self.checksum_retry_interval)
                    logging.warning(f"{self.portName}: Reconnect attempt {attempt} when writing {name}")

                    try:
                        self.modbus.serial.close()
                        sleep(0.25)
                        self.modbus.serial.open()
                        sleep(0.25)
                        self.modbus.write_register(address, value, number_of_decimals=0,
                                                   functioncode=16, signed=True)
                    except minimalmodbus.NoResponseError as e:
                        logging.warning(f"{self.portName} - TTL: {e}")
                        self.com_loss += 1
                        logging.info(f"{self.portName} COM LOSS: {self.com_loss}")
                        if self.com_loss > self.checksum_retry:
                            return False
                    except (OSError, ValueError, minimalmodbus.InvalidResponseError) as e:
                        error = e
                        logging.warning(f"\n{self.portName} - {e}\n")
                        if "Checksum error" in str(error):
                            self.checksums += 1
                            # print("")
                            attempt = 0
                            while "Checksum error" in str(error):
                                if attempt < self.checksum_retry:
                                    attempt += 1
                                    sleep(self.checksum_retry_interval)
                                    logging.warning(f"{self.portName}: Write attempt {attempt} for {name}")
                                    try:
                                        self.modbus.write_register(address, value, number_of_decimals=0, functioncode=16,
                                                                   signed=True)
                                    except (TypeError, OSError, ValueError, AttributeError, minimalmodbus.InvalidResponseError) as e:
                                        error = e
                                        if "Checksum error" in str(error):
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
                                    # print(f"\n{self.portName} write to {name} failed")
                                    raise CommError
                        continue
                    except KeyboardInterrupt:
                        return False
                    else:
                        self.com_loss = 0
                        if isinstance(name, str):
                            if value / scale == self.read(name):
                                param.Value = value / scale
                        return True

                raise CommError

            return False
        else:
            self.com_loss = 0
            if isinstance(name, str):
                param.Value = value
            return True
