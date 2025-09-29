from datetime import datetime
import math
import _queue
import can
from can.interfaces.pcan import pcan
from can.interfaces.pcan.pcan import PcanBus
from can.interface import Bus
from time import sleep
from dyno_v2.Module.ComABC import ComABC
from dyno_v2.Module.Parameter import Parameter
from dyno_v2.Module.exceptions import *
from dyno_v2.Module.util import *
from threading import Thread
from collections import deque
import logging




class CANcom(ComABC):

    def __init__(
            self,
            can_port="PCAN_USBBUS1",
            bit_rate=250000,
            can_id=42,
            listening=True
    ):
        self.port = str(can_port)
        self.bit_rate = int(bit_rate)
        if isinstance(can_id, int) or isinstance(can_id, float):
            self.id = [int(can_id)]
        elif isinstance(can_id, list):
            self.id = can_id
        else:
            self.id = [int(can_id)]

        # print(f"Connecting to instrument @: port {self.port} baud {self.bit_rate}, ID: {self.id}")
        try:
            raw = open('can_params.txt', mode='r')
        except FileNotFoundError:
            raw = open('..\\..\\can_params.txt', mode='r')
        lines = raw.readlines()
        self.TIMEOUT = int(lines[0].strip().split(',')[1]) * 0.001
        self.READ_TIMEOUT = int(lines[1].strip().split(',')[1])
        self.WRITE_TIMEOUT = int(lines[2].strip().split(',')[1])
        raw.close()

        try:
            if "default" in self.port:
                print(f"Connecting to instrument @: {self.port} preset port PCAN_USBBUS1 @ 250K, ID: 42")
                self.CANBus = Bus(context=self.port)
                self.port = "PCAN_USBBUS1"
            elif "PCAN_USBBUS" in self.port:
                print(f"Connecting to instrument @: port {self.port}, bit rate: {self.bit_rate}, ID: {self.id}")
                self.CANBus = PcanBus(channel=self.port, bitrate=self.bit_rate)
        except can.interfaces.pcan.pcan.PcanCanInitializationError as e:
            logging.warning(e)
            self.disconnected = True
            raise ConnectionInterruptedError("PCAN Channel occupied")
        except (can.interfaces.pcan.pcan.PcanCanOperationError,
                can.interfaces.pcan.pcan.PcanError) as e:
            logging.error(e)
            # raise CommLossError


        self.disconnected = False
        # self.TIMEOUT = TIMEOUT
        self.listener_thread = None
        self.retry = 4
        self.retry_interval = 0.01
        self.run_parameters = {}
        self.PDO_parameters = {}
        self.listening = False
        self.ext = False
        self.auto_tpdo = True
        self.auto_rpdo = True
        self.rtr = False
        self.auto_id = False
        self.TPDO = {}
        self.RPDO = {}

        self.msg_buffer = deque()
        self.out = deque()
        self.requests = deque()
        if listening:
            self.startListening()

    def __del__(self):
        if hasattr(self, 'listening') and self.listening:
            self.stopListening()
        if hasattr(self, 'CANBus'):
            try:
                self.CANBus.shutdown()
            except AttributeError:
                pass

    def startListening(self):
        logging.info('CAN bus starts listening')
        self.listening = True
        self.listener_thread = Thread(target=self.listen)
        # self.listener_thread.daemon = True
        self.listener_thread.start()

    def stopListening(self):
        if self.listening:
            logging.info('CAN bus stops listening')
            self.listening = False
            # self.listener_thread = None
            self.listener_thread.join()

    def resumeListening(self):
        self.listener_thread = None
        self.startListening()

    def listen(self):
        msg_out = None
        while self.listening:
            if len(self.msg_buffer) > 0:
                # msg_out = self.msg_buffer.get(block=True, timeout=self.TIMEOUT)
                try:
                    msg_out = self.msg_buffer.popleft()
                except IndexError:
                    msg_out = None
                else:
                    try:
                        self.CANBus.send(msg_out)
                    except (pcan.PcanError, can.interfaces.pcan.pcan.PcanCanOperationError) as e:
                        logging.error('CAN listen on send')
                        logging.error(e)
                        self.reset()
                        try:
                            self.CANBus.send(msg_out)
                        except:
                            self.disconnected = True
                            self.listening = False
                            # raise CommLossError
                            break
                    # finally:
                    #     if self.status() != 0:
                            # self.reconnect()
                            # self.CANBus.send(msg_out)
                # else:
                #     msg_in = self.CANBus.recv(timeout=self.TIMEOUT)
                #     self.out.put((msg_out, msg_in))
            if self.status() in [8, 0x4000000]:
                # print(self.status())
                logging.warning('CAN status terminated')
                self.disconnected = True
                self.listening = False
                break

            try:
                msg_in = self.CANBus.recv(timeout=self.TIMEOUT)

            except can.interfaces.pcan.pcan.PcanCanOperationError as e:
                logging.error(e)
                continue
            except CommLossError as e:
                logging.error('CAN listen on recv')
                logging.error(e)
                # self.listening = False
                print(self.status())
                self.reset()
                try:
                    msg_in = self.CANBus.recv(timeout=self.TIMEOUT)
                except:
                    self.disconnected = True
                    self.listening = False
                    # raise CommLossError
                    break
            finally:
                if msg_in is not None:
                    self._parse_msg(msg_in, msg_out)

    def _parse_msg(self, msg_in, msg_out):
        if self.can_pdo_handle(msg_in):
            # if msg_out is not None:
            #     self.msg_buffer.appendleft(msg_out)
            return
        if len(self.id) > 1:
            if self.can_pdo_handle(msg_in, 1):
                # if msg_out is not None:
                #     self.msg_buffer.appendleft(msg_out)
                return
            if self.can_error(msg_in, 1):
                # if msg_out is not None:
                #     self.msg_buffer.appendleft(msg_out)
                return
            if self.can_heartbeat_handle(msg_in, 1):
                # if msg_out is not None:
                #     self.msg_buffer.appendleft(msg_out)
                return
        if self.can_error(msg_in):
            # if msg_out is not None:
            #     self.msg_buffer.appendleft(msg_out)
            return
        if self.can_heartbeat_handle(msg_in):
            # if msg_out is not None:
            #     self.msg_buffer.appendleft(msg_out)
            return
        self.out.append((msg_out, msg_in))

    def controller_parameter(self, params, index=0):
        self.run_parameters[index] = params

    def read(self, name, index=0):
        if isinstance(name, str):
            try:
                param = self.run_parameters[index][name]
            except KeyError:
                logging.debug(f"CAN read: {name} not in run parameters")
                try:
                    param = self.PDO_parameters[index][name]
                except KeyError:
                    logging.warning(f"{name} not in PDO parameters")
                    raise NotInPDOParameterError

            previous_value = param.Value
            if previous_value is None:
                previous_value = 0
            scale = param.Scale
            scale = get_scale_value(scale)

        msg = self._message_constructor(True, name, index)

        # arbitration_id = 0x600 + self.id[index]
        # can_address = [0, 0]
        # can_address[0], can_address[1], sub_idx = self.can_address(name)
        # if can_address[0] != -1 and can_address[1] != -1 and sub_idx != -1:
        #     msg = can.Message(arbitration_id=arbitration_id, data=[0x40, can_address[1], can_address[0], sub_idx, 0, 0, 0, 0],
        #                       is_extended_id=False, is_remote_frame=False)
        if msg:
            self.msg_buffer.append(msg)
            for _ in range(int(self.READ_TIMEOUT)):
                try:
                    sleep(0.001)
                    a, b = self.out.popleft()
                except IndexError:
                    pass
                else:
                    try:
                        if self.is_sdo_response(a, b, index):
                            break
                    except AttributeError:
                        continue
            try:
                # if self.can2param(a) == self.can2param(msg):
                if a and b:
                    value = self.can_response(a, b, index)
                    if isinstance(value, int):
                        if isinstance(name, str):
                            try:
                                value = signed(int(value))
                            except (TypeError, ValueError, pcan.PcanError) as e:
                                logging.error(e)
                                return previous_value
                            else:
                                value = value / scale
                                if param.Scale == 'hex' and value < 0:
                                    value += 65536
                                param.Value = value
                                self.disconnected = False
                                return value
                        else:
                            return value
                    else:
                        if isinstance(name, int):
                            return 0
                    # else:
                        # print(name, previous_value)
                        # return previous_value

                if self.listening:
                    self.retry -= 1
                    if self.retry >= 0:
                        return self.read(name, index)
                    else:
                        self.retry = 3
                        return previous_value
                        # self.listening = False
                        # self.disconnected = True
                        # raise CommLossError
                else:
                    self.listening = False
                    self.disconnected = True
                    raise CommLossError
            except UnboundLocalError:
                if self.listening:
                    self.retry -= 1
                    if self.retry >= 0:
                        return self.read(name, index)
                    else:
                        self.retry = 3
                        return previous_value
                else:
                    self.listening = False
                    self.disconnected = True
                    raise CommLossError
        else:
            print(f"Invalid can addressing...")
            return previous_value

    def write(self, name, value, index=0):
        can_address = [0, 0]
        if isinstance(name, str):
            can_address[0], can_address[1], sub_idx = self.can_address(name)
            try:
                param = self.run_parameters[index][name]
            except KeyError:
                logging.warning(f"CAN write: {name} not in run parameters")
                raise NotInRunParameterError
            scale = param.Scale

            if scale:
                scale = get_scale_value(scale)
                value_scaled = value * scale

            if value_scaled > 32768:
                value_scaled = value_scaled - 65536
        elif isinstance(name, int):
            can_address[0], can_address[1], sub_idx = self.can_address(name)
            value_scaled = value
        else:
            logging.error(f"Error writing {name}: Bad type: {type(name)}")
            return False
        # value = signed(value)

        msg = self._message_constructor(False, name, index, value_scaled, can_address, sub_idx)

        # arbitration_id = 0x600 + self.id[index]
        #
        # send_command = self.can_send_command(abs(int(value_scaled)))
        # if not send_command:
        #     logging.error(f"\nError Writing {name} - Unable to generate send command")
        #     return False
        #
        # send_data = self.can_send_msg(int(value_scaled))
        # if not send_data:
        #     logging.error(f"\nError Writing {name} - Unable to generate send message")
        #     return False
        #
        # if can_address[0] != -1 and can_address[1] != -1 and sub_idx != -1:
        #     content = [send_command, can_address[1], can_address[0], sub_idx]
        #     for d in send_data:
        #         content.append(d)
        #     msg = can.Message(arbitration_id=arbitration_id, data=content,
        #                       is_extended_id=False, is_remote_frame=False)
        #     # self.can_bus.stop_all_periodic_tasks()
        #     if msg.dlc == 0:
        #         logging.error(f'Bad msg: {msg}')
        #         return False
        if msg:
            self.msg_buffer.append(msg)
            for _ in range(int(self.WRITE_TIMEOUT)):
                try:
                    sleep(0.001)
                    a, b = self.out.popleft()
                except IndexError:
                    pass
                else:
                    break
            try:
                if self.can2param(a) == self.can2param(msg):
                    if "write complete" in str(self.can_response(a, b, index)):
                        if isinstance(name, str):
                            param.Value = value
                        self.disconnected = False
                        return True
                    else:
                        return False
                # elif self.can_error(b):
                #     self.write(name, value, index)

                if self.listening:
                    # self.write(name, value, index)
                    self.retry -= 1
                    if self.retry >= 0:
                        self.write(name, value, index)
                    else:
                        self.retry = 3
                        return False
                    #     self.listening = False
                    #     self.disconnected = True
                    #     raise CommLossError
                else:
                    self.disconnected = True
                    raise CommLossError
            except UnboundLocalError:
                if self.listening:
                    # self.write(name, value, index)
                    self.retry -= 1
                    if self.retry >= 0:
                        self.write(name, value, index)
                    else:
                        self.retry = 3
                        return False
                    #     self.listening = False
                    #     self.disconnected = True
                    #     raise CommLossError
                else:
                    self.disconnected = True
                    raise CommLossError
        else:
            print(f"Invalid can addressing...")
            return False

    # ########## CanOpen Helper #################
    def _message_constructor(self, read: bool, name, index, value_scaled=0, can_address=None, sub_idx=-1):
        if read:
            arbitration_id = 0x600 + self.id[index]
            can_address = [0, 0]
            can_address[0], can_address[1], sub_idx = self.can_address(name)
            if can_address[0] != -1 and can_address[1] != -1 and sub_idx != -1:
                msg = can.Message(arbitration_id=arbitration_id,
                                  data=[0x40, can_address[1], can_address[0], sub_idx, 0, 0, 0, 0],
                                  is_extended_id=False, is_remote_frame=False)
                return msg
            return False
        else:
            arbitration_id = 0x600 + self.id[index]

            send_command = self.can_send_command(abs(int(value_scaled)))
            if not send_command:
                logging.error(f"\nError Writing {name} - Unable to generate send command")
                return False

            send_data = self.can_send_msg(int(value_scaled))
            if not send_data:
                logging.error(f"\nError Writing {name} - Unable to generate send message")
                return False

            if can_address[0] != -1 and can_address[1] != -1 and sub_idx != -1:
                content = [send_command, can_address[1], can_address[0], sub_idx]
                for d in send_data:
                    content.append(d)
                msg = can.Message(arbitration_id=arbitration_id, data=content,
                                  is_extended_id=False, is_remote_frame=False)
                # self.can_bus.stop_all_periodic_tasks()
                if msg.dlc == 0:
                    logging.error(f'Bad msg: {msg}')
                    return False
                return msg
            return False

    def reconnect(self):
        # print(self.retry, self.status(), self.state())
        for i in range(self.retry):
            try:
                self.retry -= 1
                print(f"Reconnecting attempt {i + 1}")
                # self.can_bus = None
                self.reset()
                self.stopListening()
                self.shutdown()

                print(f"Reconnecting to instrument @: port {self.port}, bit rate: {self.bit_rate}")
                self.CANBus = pcan.PcanBus(channel=self.port, bitrate=self.bit_rate)
                valid_data = can.Message(is_extended_id=False, is_remote_frame=False, arbitration_id=0x62A, is_rx=False)
                for _ in range(128):
                    self.CANBus.send(valid_data)
                sleep(1)
                self.reset()
                # sleep(1.5)
                self.resumeListening()
            except AttributeError as a:
                logging.warning(a)
                continue
            except (can.interfaces.pcan.pcan.PcanCanOperationError,
                    can.interfaces.pcan.pcan.PcanCanInitializationError) as e:
                logging.warning(e)
                raise CommLossError
            except KeyboardInterrupt:
                return False
            else:
                # self.can_NMT(0x80)
                if int(self.status()) == 67108864:
                    # print(self.status(), self.state())
                    self.disconnected = True
                    sleep(self.retry_interval)
                else:
                    self.disconnected = False
                    self.CANBus.reset()
                    break
        if self.disconnected:
            try:
                self.stopListening()
                self.shutdown()
                self.disconnected = True
                # self.listening = False
                # raise CommLossError
            except AttributeError:
                pass
        else:
            self.CANBus.reset()
            # raise CommLossError

    def shutdown(self):
        try:
            return self.CANBus.shutdown()
        except AttributeError:
            return

    def reset(self):
        if self.CANBus.reset():
            pass
        else:
            if self.listening:
                self.shutdown()
                self.CANBus = PcanBus(channel=self.port, bitrate=self.bit_rate)

    def state(self):
        return self.CANBus.state

    def status(self):
        # print(self.CANBus.status_string())
        return self.CANBus.status()

    def can_address(self, param):
        """

        Args:
            param: Parameter, parameter name (str) or parameter address (int)

        Returns:
            can Message Index (can Message Data[1] & Data[2]) & Sub Index (can Message Data[3])

        """
        if isinstance(param, str):
            try:
                address = int(self.PDO_parameters[0][param].Address)
            except (KeyError, AttributeError, TypeError):
                address = int(self.run_parameters[0][param].Address)

        elif isinstance(param, int):
            address = param
        elif isinstance(param, Parameter):
            address = param.Address
        else:
            return -1, -1, -1
        idx_1 = (int(math.floor(address / 64) + 8192) & 0xff00) >> 8
        idx_2 = int(math.floor(address / 64) + 8192) & 0xff
        return idx_1, idx_2, address % 64 + 1

    def map2name(self, idx=0, sub=0, index=0):
        if idx == -128 and sub == -1:
            return 'Empty'
        # print(f"{int(idx):04x} | {int(sub):02x} | ")
        address = 0
        address += int(idx)
        address += int(sub)

        for param in self.run_parameters[index]:
            # print(f"{address} | {self.run_parameters[param]}")
            try:
                if self.run_parameters[index][param].Name is not None and \
                        int(self.run_parameters[index][param].Address) == address:
                    return param
            except AttributeError as e:
                pass
        for param in self.PDO_parameters[index]:
            # print(f"{address} | {self.pdo_parameters[param]}")
            if self.PDO_parameters[index][param].Name is not None and \
                    int(self.PDO_parameters[index][param].Address) == address:
                return param
        return False

    def can2param(self, msg, name=True, index=0):
        """

        Args:
            msg: can Message
            name: bool - Return name or address

        Returns:
            Parameter name or address from given can Message address bytes

        """
        if msg is None:
            return f"Invalid Message"
        if msg.dlc >= 4:
            address = (int(msg.data[2]) * 0x100 + int(msg.data[1]) - 8192) * 64
            # if address % 64 + 1 == int(msg.data[3]):
            try:
                param = self.run_parameters[index][self.map2name(address, int(msg.data[3]) - 1)]
            except KeyError:
                try:
                    param = self.PDO_parameters[index][self.map2name(address, int(msg.data[3]) - 1)]
                except KeyError:
                    return "Parameter not in Run"
            if name:
                return param.Name
            else:
                return param.Address
            # else:
            # print(address, int(msg.data[3]), msg)
            # return f"Invalid Sub Index"
        else:
            return f"Message has no address"

    def is_read(self, msg: can.Message, index=0) -> bool:
        if msg.arbitration_id - self.id[index] == 0x580:
            if msg.data[0] in [0x60, 0x23, 0x27, 0x2B, 0x2F, 0x80]:  # write
                return False
            elif msg.data[0] in [0x43, 0x47, 0x4B, 0x4F]:  # read
                return True

        raise ValueError("Not SDO")

    def is_sdo_response(self, msg_out: can.Message, msg_in: can.Message, index=0):
        if msg_out.arbitration_id - self.id[index] == 0x600 and msg_in.arbitration_id - self.id[index] == 0x580:
            if int(msg_in.data[1]) == int(msg_out.data[1]) \
                    and int(msg_in.data[2]) == int(msg_out.data[2]) \
                    and int(msg_in.data[3]) == int(msg_out.data[3]):
                return True
        return False


    def can_response(self, msg_out: can.Message, msg_in: can.Message, index=0):
        """

        Args:
            msg_in: Inbound can Message
            msg_out: Outbound can Message
            index: can device
        Returns:
            Responses from can Message handlers

        """
        # print(msg_out, msg_in)
        if msg_out is not None and msg_in is not None:
            if self.can2param(msg_out) == self.can2param(msg_in):
                return self.can_sdo_handle(msg_in, index)
            # try:
            #     if not self.is_sdo_response(msg_out, msg_in, index):
            #         return self.can_sdo_handle(msg_in, index)
            #     else:
            #         return
                    # else:
                    #     print(response)
                    #     return False
            # except ValueError as e:
            #     logging.debug(f'{e} - {msg_in} - {msg_out}')
            #     return

        # if msg_in is not None:
        #     # logging.info(msg_in)
        #     # response = self.can_sdo_handle(msg_in, index)
        #     # if isinstance(response, str) or not response:
        #     #     return
        #     # elif isinstance(response, int):
        #     #     return response
        #     errors = self.can_error(msg_in, index)
        #     # retry = 0
        #     if not errors:
        #         # response = self.can_sdo_handle(msg_in, index)
        #         # if response == "write complete":
        #         #     return
        #         # else:
        #         #     return response
        #         return self.can_sdo_handle(msg_in, index)
        #     else:
        #         return
            # while errors:
            #     if retry >= self.retry:
            #         print(f"Invalid Response after {self.retry} retries")
            #         return
            #     else:
            #         if msg_in.dlc >= 4:
            #             print(f"Error responding {self.can2param(msg_in, True)}\n{errors}")
            #         else:
            #             print(f"Error responding to message: \n{msg_out}\n{errors}")
            #         sleep(self.retry_interval)
            #         retry += 1
            #         msg_in = self.CANBus.recv(self.TIMEOUT)
            #         errors = self.can_error(msg_in, index)
            #         heartbeat = self.can_heartbeat_handle(msg_in, index)
            #         pdo = self.can_pdo_handle(msg_in, index)
            #         if errors or heartbeat or pdo or msg_in is None:
            #             pass
            #         else:
            #             self.can_response(msg_out, msg_in, index)

        # if msg_out is not None:
        #     self.CANBus.send(msg_out)
        #     msg_in = self.CANBus.recv(timeout=self.TIMEOUT)
        #     self.can_response(msg_out, msg_in)

    def can_sdo_handle(self, msg: can.Message, index=0):
        """

        Args:
            msg: can Message (SDOs 0x580)
            index: can device
        Returns:
            Integer value from return data
            Or Error message

        """
        if msg.arbitration_id - self.id[index] == 0x580:
            if msg.data[0] == 0x4F:  # 79 - 1 byte SDO response
                return msg.data[4]
            elif msg.data[0] == 0x4B:  # 75 - 2 byte SDO response
                return msg.data[4] + msg.data[5] * 0x100
            elif msg.data[0] == 0x47:  # 71 - 3 byte SDO response
                return msg.data[4] + msg.data[5] * 0x100 + msg.data[6] * 0x10000
            elif msg.data[0] == 0x43:  # 67 - 4 byte SDO response
                return msg.data[4] + msg.data[5] * 0x100 + msg.data[6] * 0x10000 + msg.data[7] * 0x1000000
            elif msg.data[0] == 0x60:  # 96 - write complete
                return f"write complete"
            elif msg.data[0] == 0x80:  # 128 - Error response
                if msg.data[4] == 16:
                    return f"Data type does not match length. Length of Service Parameter does not match."
                elif msg.data[4] == 17:
                    return f"Sub Index does not exist."
                elif msg.data[4] == 1:
                    return f"Client/Server command specifier not valid or unknown."
                elif msg.data[6] == 1:
                    return f"Unsupported access to an object."
                elif msg.data[6] == 2:
                    return f"Object does not exist in object dictionary."
        else:
            return False

    def can_heartbeat_handle(self, msg: can.Message, index=0) -> bool:
        """

        Args:
            msg: can Message (Heartbeat Protocol 0x700)
            index: can device
        Returns:
            Heartbeat Status: Boot up/Initializing
                              Stopped
                              Operational
                              Pre-Operational
                              Invalid Heartbeat Status

        """
        if msg.dlc == 1 and msg.arbitration_id - self.id[index] == 0x700:  # Heartbeat Protocol
            if msg.data[0] == 0x00:
                print(f"Heartbeat: Boot/Initializing")
                return True
            elif msg.data[0] == 0x04:
                print(f"Heartbeat: Stopped")
                return True
            elif msg.data[0] == 0x05:
                print(f"Heartbeat: Operational")
                return True
            elif msg.data[0] == 0x7f:
                print(f"Heartbeat: Pre-Operational")
                return True
            else:
                print(f"Invalid Heartbeat State")
                return True
        else:
            return False

    def can_error(self, msg: can.Message, index=0) -> bool:
        """

        Args:
            msg: can Message
            index: can device
        Prints:
            Emergency Code as received

        Returns:
            NoneType - "No Message"
            COB-ID 0x080 - List of Emergency Protocol

        """
        if msg is None:
            return False
        elif msg.is_error_frame and msg.arbitration_id == 8 and msg.dlc == 4 and msg.data[1] == 25:
            self.disconnected = True
            return True
        elif msg.is_error_frame and msg.arbitration_id == 0:
            logging.error(f"Error Count: {msg.data[3]}")
            logging.error(self.status())
            # if self.status() == 8:
            # try:
            #     self.reconnect()
            # except (CommLossError, ConnectionInterruptedError):
            #     self.listening = False
            #     self.disconnected = True
            return True
        elif msg.is_error_frame:
            logging.error(msg)
            return True
        elif msg.arbitration_id < 8:
            return True
        elif msg.arbitration_id - self.id[index] != 0x80:
            return False
        elif msg.arbitration_id - self.id[index] == 0x80:
            if msg.dlc != 8:  # should be a low chance event
                logging.warning("Error Message length invalid")
                return True
            else:
                logging.info(f"Emergency Protocol [Device ID {self.id[index]}]: ")
                if msg.data[0] == 0 and msg.data[1] == 0x10:
                    logging.info("Valid Emergency Code: Manufacturer Defined Error Codes 0x1000")
                    logging.info(f"{msg.data[2]:08b} | {msg.data[3]:08b} | {msg.data[5]:08b}{msg.data[4]:08b} | "
                                 f"{msg.data[7]:08b}{msg.data[6]:08b}")
                    high = int(self.run_parameters[index]["faults2"].Value) & (0xff << 8)
                    self.run_parameters[index]["faults2"].Value = high + msg.data[3]
                    self.run_parameters[index]["faults"].Value = msg.data[5] * 0x100 + msg.data[4]
                    self.run_parameters[index]["warnings"].Value = msg.data[7] * 0x100 + msg.data[6]

                    return_list = {"error register": [], "faults1": [], "faults2": [], "warnings": []}

                    # error register
                    if msg.data[2] & 1:
                        return_list["error register"].append("Bit 0: Generic")
                    if msg.data[2] & (1 << 1):
                        return_list["error register"].append("Bit 1: Current")
                    if msg.data[2] & (1 << 2):
                        return_list["error register"].append("Bit 2: Voltage")
                    if msg.data[2] & (1 << 3):
                        return_list["error register"].append("Bit 3: Temperature")
                    if msg.data[2] & (1 << 4):
                        return_list["error register"].append("Bit 4: Communication")
                    if msg.data[2] & (1 << 5):
                        return_list["error register"].append("Bit 5: Device Profile Specific")
                    if msg.data[2] & (1 << 6):
                        return_list["error register"].append("Bit 6: Reserved (always 0)")
                    if msg.data[2] & (1 << 7):
                        return_list["error register"].append("Bit 7: Manufacturer Specific")

                    # faults2 low byte
                    if msg.data[3] & 1:
                        return_list["faults2"].append("Bit 0: Parameter CRC")
                    if msg.data[3] & (1 << 1):
                        return_list["faults2"].append("Bit 1: Current Scaling")
                    if msg.data[3] & (1 << 2):
                        return_list["faults2"].append("Bit 2: Voltage Scaling")
                    if msg.data[3] & (1 << 3):
                        return_list["faults2"].append("Bit 3: Headlight Under Voltage")
                    if msg.data[3] & (1 << 4):
                        return_list["faults2"].append("Bit 4: Torque Sensor")
                    if msg.data[3] & (1 << 5):
                        return_list["faults2"].append("Bit 5: can Bus")
                    if msg.data[3] & (1 << 6):
                        return_list["faults2"].append("Bit 6: Hall Stall")
                    if msg.data[3] & (1 << 7):
                        return_list["faults2"].append("Bit 7: Bootloader")

                    # faults
                    if msg.data[4] & 1:
                        return_list["faults1"].append("Bit 0: Controller Over Voltage")
                    if msg.data[4] & (1 << 1):
                        return_list["faults1"].append("Bit 1: Phase Over Current")
                    if msg.data[4] & (1 << 2):
                        return_list["faults1"].append("Bit 2: Current Sensor Calibration")
                    if msg.data[4] & (1 << 3):
                        return_list["faults1"].append("Bit 3: Current Sensor Over Current")
                    if msg.data[4] & (1 << 4):
                        return_list["faults1"].append("Bit 4: Controller Over Temperature")
                    if msg.data[4] & (1 << 5):
                        return_list["faults1"].append("Bit 5: Motor Hall Sensor Fault")
                    if msg.data[4] & (1 << 6):
                        return_list["faults1"].append("Bit 6: Controller Under Voltage")
                    if msg.data[4] & (1 << 7):
                        return_list["faults1"].append("Bit 7: POST Static Gating tests")
                    if msg.data[5] & 1:
                        return_list["faults1"].append("Bit 8: Network Communication Timeout")
                    if msg.data[5] & (1 << 1):
                        return_list["faults1"].append("Bit 9: Instantaneous Phase Over Current")
                    if msg.data[5] & (1 << 2):
                        return_list["faults1"].append("Bit 10: Motor Over Temperature")
                    if msg.data[5] & (1 << 3):
                        return_list["faults1"].append("Bit 11: Throttle Voltage Outside Range")
                    if msg.data[5] & (1 << 4):
                        return_list["faults1"].append("Bit 12: Instantaneous Controller Over Voltage")
                    if msg.data[5] & (1 << 5):
                        return_list["faults1"].append("Bit 13: Internal Error")
                    if msg.data[5] & (1 << 6):
                        return_list["faults1"].append("Bit 14: POST Dynamic Gating tests")
                    if msg.data[5] & (1 << 7):
                        return_list["faults1"].append("Bit 15: Instantaneous Under Voltage")

                    # warnings
                    if msg.data[6] & 1:
                        return_list["warnings"].append("Bit 0: Communication Timeout")
                    if msg.data[6] & (1 << 1):
                        return_list["warnings"].append("Bit 1: Hall Sensor")
                    if msg.data[6] & (1 << 2):
                        return_list["warnings"].append("Bit 2: Hall Stall")
                    if msg.data[6] & (1 << 3):
                        return_list["warnings"].append("Bit 3: Wheel Speed Sensor")
                    if msg.data[6] & (1 << 4):
                        return_list["warnings"].append("Bit 4: can Bus")
                    if msg.data[6] & (1 << 5):
                        return_list["warnings"].append("Bit 5: Hall Illegal Sector")
                    if msg.data[6] & (1 << 6):
                        return_list["warnings"].append("Bit 6: Hall Illegal Transition")
                    if msg.data[6] & (1 << 7):
                        return_list["warnings"].append("Bit 7: Vdc Low Foldback")
                    if msg.data[7] & 1:
                        return_list["warnings"].append("Bit 8: Vdc High Foldback")
                    if msg.data[7] & (1 << 1):
                        return_list["warnings"].append("Bit 9: Motor Temperature Foldback")
                    if msg.data[7] & (1 << 2):
                        return_list["warnings"].append("Bit 10: Control Temperature Foldback")
                    if msg.data[7] & (1 << 3):
                        return_list["warnings"].append("Bit 11: Low SOC Foldback")
                    if msg.data[7] & (1 << 4):
                        return_list["warnings"].append("Bit 12: Hi SOC Foldback")
                    if msg.data[7] & (1 << 5):
                        return_list["warnings"].append("Bit 13: I2t Foldback")
                    if msg.data[7] & (1 << 6):
                        return_list["warnings"].append("Bit 14: Reserved (not used)")
                    if msg.data[7] & (1 << 7):
                        return_list["warnings"].append("Bit 15: BMS timeout")

                    logging.info(return_list)

                    return True
                elif msg.data[0] == 0 and msg.data[1] == 0x20:
                    logging.info("Valid Emergency Code: Manufacturer Defined Error Codes 0x2000")
                    logging.info(f"{msg.data[2]:08b} | {msg.data[3]:08b} | {msg.data[5]:08b}{msg.data[4]:08b} | "
                                 f"{msg.data[7]:08b}{msg.data[6]:08b}")
                    low = int(self.run_parameters[index]["faults2"].Value) & 0xff
                    self.run_parameters[index]["faults2"].Value = msg.data[3] * 0x100 + low
                    self.run_parameters[index]["warnings2"].Value = msg.data[5] * 0x100 + msg.data[4]

                    return_list = {"error register": [], "faults2": [], "warnings2": []}

                    # error register
                    if msg.data[2] & 1:
                        return_list["error register"].append("Bit 0: Generic")
                    if msg.data[2] & (1 << 1):
                        return_list["error register"].append("Bit 1: Current")
                    if msg.data[2] & (1 << 2):
                        return_list["error register"].append("Bit 2: Voltage")
                    if msg.data[2] & (1 << 3):
                        return_list["error register"].append("Bit 3: Temperature")
                    if msg.data[2] & (1 << 4):
                        return_list["error register"].append("Bit 4: Communication")
                    if msg.data[2] & (1 << 5):
                        return_list["error register"].append("Bit 5: Device Profile Specific")
                    if msg.data[2] & (1 << 6):
                        return_list["error register"].append("Bit 6: Reserved (always 0)")
                    if msg.data[2] & (1 << 7):
                        return_list["error register"].append("Bit 7: Manufacturer Specific")

                    # faults2 high byte
                    if msg.data[3] & 1:
                        return_list["faults2"].append("Bit 8: Parameter2 CRC")
                    if msg.data[3] & (1 << 1):
                        return_list["faults2"].append("Bit 9: Motor position fault")
                    if msg.data[3] & (1 << 2):
                        return_list["faults2"].append("Bit 10: Dyname torque sensor voltage outside range")
                    if msg.data[3] & (1 << 3):
                        return_list["faults2"].append("Bit 11: Dyname torque sensor statis voltage fault")
                    if msg.data[3] & (1 << 4):
                        return_list["faults2"].append("Bit 12: Remote CAN fault")
                    if msg.data[3] & (1 << 5):
                        return_list["faults2"].append("Bit 13: Accelerometer Side tilt fault")
                    if msg.data[3] & (1 << 6):
                        return_list["faults2"].append("Bit 14: Open phase fault")
                    if msg.data[3] & (1 << 7):
                        return_list["faults2"].append("Bit 15: Analog brake voltage out of range")

                    # warnings2
                    if msg.data[4] & 1:
                        return_list["warnings2"].append("Bit 0: Throttle out of range")
                    if msg.data[4] & (1 << 1):
                        return_list["warnings2"].append("Bit 1: Dual speed sensor missing pulses")
                    if msg.data[4] & (1 << 2):
                        return_list["warnings2"].append("Bit 2: Dual speed sensor no pulses")
                    if msg.data[4] & (1 << 3):
                        return_list["warnings2"].append("Bit 3: Dynamic Flash Full")
                    if msg.data[4] & (1 << 4):
                        return_list["warnings2"].append("Bit 4: Dynamic Flash Read Error")
                    if msg.data[4] & (1 << 5):
                        return_list["warnings2"].append("Bit 5: Dynamic Flash Write Error")
                    if msg.data[4] & (1 << 6):
                        return_list["warnings2"].append("Bit 6: Params 3 missing")
                    if msg.data[4] & (1 << 7):
                        return_list["warnings2"].append("Bit 7: Missed CAN Message")
                    if msg.data[5] & 1:
                        return_list["warnings2"].append("Bit 8: Hot battery Foldback")
                    if msg.data[5] & (1 << 1):
                        return_list["warnings2"].append("Bit 9: Reserved for future use")
                    if msg.data[5] & (1 << 2):
                        return_list["warnings2"].append("Bit 10: Reserved for future use")
                    if msg.data[5] & (1 << 3):
                        return_list["warnings2"].append("Bit 11: Reserved for future use")
                    if msg.data[5] & (1 << 4):
                        return_list["warnings2"].append("Bit 12: Reserved for future use")
                    if msg.data[5] & (1 << 5):
                        return_list["warnings2"].append("Bit 13: Reserved for future use")
                    if msg.data[5] & (1 << 6):
                        return_list["warnings2"].append("Bit 14: Reserved for future use")
                    if msg.data[5] & (1 << 7):
                        return_list["warnings2"].append("Bit 15: Reserved for future use")

                    logging.info(return_list)

                    return True
                else:
                    logging.info(f"Invalid emergency code - {msg}")
                    return True
        return False

    def is_PDO(self, msg: can.Message, index=0):
        """

        Args:
            msg: can Message to be identified
            index: can device
        Returns:
            "R" or "T": RPDO or TPDO
            1-12: Index of the PDO based on arbitration ID
            False: if not PDO

        """
        try:
            if msg.arbitration_id - self.id[index] == 0x180:
                return 'T', 1
            elif msg.arbitration_id - self.id[index] == 0x280:
                return 'T', 2
            elif msg.arbitration_id - self.id[index] == 0x380:
                return 'T', 3
            elif msg.arbitration_id in [0x190, 0x191, 0x192, 0x193, 0x194, 0x195]:
                return 'T', 1
            elif msg.arbitration_id in [0x290, 0x291, 0x292, 0x293, 0x294, 0x295]:
                return 'T', 2
            elif msg.arbitration_id in [0x390, 0x391, 0x392, 0x393, 0x394, 0x395]:
                return 'T', 3
            # Code below might be too slow
            if len(self.TPDO[index]) >= 0:
                # if self.auto_tpdo:
                #     if msg.arbitration_id - self.id[index] == 0x180:
                #         return "T", 1
                #     elif msg.arbitration_id - self.id[index] == 0x280:
                #         return "T", 2
                #     elif msg.arbitration_id - self.id[index] == 0x380:
                #         return "T", 3
                #     elif msg.arbitration_id - self.id[index] == 0x480:
                #         return "T", 4
                #     # elif msg.arbitration_id - self.id[index] == 0x580:
                #     #     return "T", 5
                #     elif msg.arbitration_id - self.id[index] == 0x680:
                #         return "T", 6
                #     elif msg.arbitration_id - self.id[index] == 0x780:
                #         return "T", 7
                #     elif msg.arbitration_id - self.id[index] == 0x880:
                #         return "T", 8
                #     elif msg.arbitration_id - self.id[index] == 0x980:
                #         return "T", 9
                #     elif msg.arbitration_id - self.id[index] == 0xa80:
                #         return "T", 10
                #     elif msg.arbitration_id - self.id[index] == 0xb80:
                #         return "T", 11
                #     elif msg.arbitration_id - self.id[index] == 0xc80:
                #         return "T", 12
                # else:
                for tpdo in self.TPDO:
                    if tpdo.extended_id and msg.arbitration_id - self.id[index] == tpdo.id_hi * 0x1000 + tpdo.id_lo:
                        return f"{'T' if tpdo.tx else 'R'}", tpdo.idx
                    elif not tpdo.extended_id and msg.arbitration_id - self.id[index] == tpdo.id_lo:
                        # logging.info(msg)
                        return f"{'T' if tpdo.tx else 'R'}", tpdo.idx
            if len(self.RPDO[index]) >= 0:
                # if self.auto_rpdo:
                #     if msg.arbitration_id - self.id[index] == 0x100:
                #         return "R", 1
                #     elif msg.arbitration_id - self.id[index] == 0x200:
                #         return "R", 2
                #     elif msg.arbitration_id - self.id[index] == 0x300:
                #         return "R", 3
                #     elif msg.arbitration_id - self.id[index] == 0x400:
                #         return "R", 4
                #     elif msg.arbitration_id - self.id[index] == 0x500:
                #         return "R", 5
                #     # elif msg.arbitration_id - self.id == 0x600:
                #     #     return "R", 6
                #     # elif msg.arbitration_id - self.id == 0x700:
                #     #     return "R", 7
                #     elif msg.arbitration_id - self.id[index] == 0x800:
                #         return "R", 8
                #     elif msg.arbitration_id - self.id[index] == 0x900:
                #         return "R", 9
                #     elif msg.arbitration_id - self.id[index] == 0xa00:
                #         return "R", 10
                #     elif msg.arbitration_id - self.id[index] == 0xb00:
                #         return "R", 11
                #     elif msg.arbitration_id - self.id[index] == 0xc00:
                #         return "R", 12
                # else:
                for rpdo in self.RPDO:
                    if rpdo.extended_id and msg.arbitration_id - self.id[index] == rpdo.id_hi * 0x1000 + rpdo.id_lo:
                        return f"{'T' if rpdo.tx else 'R'}", rpdo.idx
                    elif not rpdo.extended_id and msg.arbitration_id - self.id[index] == rpdo.id_lo:
                        return f"{'T' if rpdo.tx else 'R'}", rpdo.idx
        except (KeyError, AttributeError):
            return False, False

    def can_pdo_handle(self, msg: can.Message, index=0) -> bool:
        """

        Args:
            msg: can Message to be handled
            index: can device
        Returns:
            bool: Whether message is handled as PDO

        """
        rt, idx = self.is_PDO(msg, index)
        if idx:
            # print(f"\33[1A")
            # try:
            # print(f"{rt}PDO{idx}: {msg}")
            # template = (f"{rt}PDO{idx}: "
            #             f"Status: {msg.data[0]}, "
            #             f"Voltage: {(msg.data[3] * 0x100 + msg.data[2]) / 32:.1f} "
            #             f"RPM: {msg.data[5] * 0x100 + msg.data[4]}, "
            #             f"Current: {(msg.data[7] * 0x100 + msg.data[6]) / 32:.2f}")
            # print(f"{template}")
            # except IndexError:
            #     print()
            return True
        return False

    @staticmethod
    def can_send_msg(value):
        """

        Args:
            value: Data to be written

        Returns:
            Data formatted for can Message

        """
        try:
            if value > 0xffffff:
                byte_4 = value & 0xff
                byte_5 = (value & 0xff00) >> 8
                byte_6 = (value & 0xff0000) >> 16
                byte_7 = (value & 0xff000000) >> 24
                return [byte_4, byte_5, byte_6, byte_7]  # 4 byte to write
            elif value > 0xffff:
                byte_4 = value & 0xff
                byte_5 = (value & 0xff00) >> 8
                byte_6 = (value & 0xff0000) >> 16
                return [byte_4, byte_5, byte_6, 0]  # 3 byte to write
            elif value > 0xff:
                byte_4 = value & 0xff
                byte_5 = (value & 0xff00) >> 8
                return [byte_4, byte_5, 0, 0]  # 2 byte to write
            elif 0 <= value < 0x100:
                byte_4 = value
                return [byte_4, 0, 0, 0]  # 1 byte to write
            elif value < 0:
                value = signed(value) + 0x1000000
                if value > 0xffffff:
                    byte_4 = value & 0xff
                    byte_5 = (value & 0xff00) >> 8
                    byte_6 = (value & 0xff0000) >> 16
                    byte_7 = (value & 0xff000000) >> 24
                    return [byte_4, byte_5, byte_6, byte_7]  # 4 byte to write
                elif value > 0xffff:
                    byte_4 = value & 0xff
                    byte_5 = (value & 0xff00) >> 8
                    byte_6 = (value & 0xff0000) >> 16
                    return [byte_4, byte_5, byte_6, 0]  # 3 byte to write
                elif value > 0xff:
                    byte_4 = value & 0xff
                    byte_5 = (value & 0xff00) >> 8
                    return [byte_4, byte_5, 0, 0]  # 2 byte to write
                elif 0 <= value < 0x100:
                    byte_4 = value
                    return [byte_4, 0, 0, 0]  # 1 byte to write
                else:
                    print(f"Invalid value {value}")
                    return False
        except TypeError:
            print(f"Invalid value {value}")
            return False

    @staticmethod
    def can_send_command(value):
        """

        Args:
            value: Data to be written

        Returns:
            Corresponding size command

        """
        if value > 0xffffff:
            return 0x23  # 4 byte to write
        elif value > 0xffff:
            return 0x27
        elif value > 0xff:
            return 0x2B
        elif 0 <= value < 0x100:
            return 0x2F
        else:
            print(f"Invalid value: {value}")
            return False

    def can_NMT(self, command=0x01, device=0):
        """

        Args:
            command: 0x01 - Enter Operational State
                     0x02 - Enter Stopped State
                     0x80 - Enter Pre-Operational State
                     0x81 - Reset Node
                     0x82 - Reset Communication
            device: can device
        Returns:

        """
        valid_command = [0x01, 0x02, 0x80, 0x81, 0x82]
        if str(command) in str(valid_command):
            msg = can.Message(arbitration_id=0, data=[command, self.id[device]],
                              is_extended_id=False, is_remote_frame=False)
            try:
                self.msg_buffer.append(msg)
                self.can_heartbeat(1000)
                if command > 0x80:
                    sleep(0.03)
                    self.stopListening()
                    sleep(0.5)
                    self.resumeListening()
                else:
                    sleep(0.02)
                self.can_heartbeat(0)
            except pcan.PcanError as e:
                # print(e)
                return False
            else:
                return True
        else:
            return False

    def can_heartbeat(self, period=None):
        """
        Disables/Enables can Heartbeat Protocol

        Args:
            period: None - read "can heartbeat period" parameter
                    int >= 0 - Set "can heartbeat period" parameter

        Returns:
            int - "can heartbeat period"
            bool - Valid input

        """
        if period is None:
            return self.read("can heartbeat period")
        elif period >= 0:
            self.write("can heartbeat period", period)
            return self.read("can heartbeat period")
        else:
            return False

    def can_SYNC(self, period=0.01):
        """

        Args:
            period: None or 0 - Stop sending periodic SYNC messages
                    int (non-0) - Set up periodic messages over can with specified period

        Returns:

        """
        if period == 0 or period is None:
            self.CANBus.stop_all_periodic_tasks()
        else:
            msg = can.Message(arbitration_id=0x80, is_extended_id=False, is_remote_frame=False)
            # return self.can_response(msg)
            self.CANBus.send_periodic(msg, period=period)

    def pdo_map_builder(self, params=None):
        """

        Args:
            params: A list of parameters to be mapped onto a PDO (up to 4 parameters)

        Returns:
            return_list: Formatted list of can PDO mapping (up to 4 parameters)

        """
        if params is None:
            return
        if isinstance(params, str):
            params = [params]

        return_list = []
        for p in params:
            idx1, idx2, sub_idx = self.can_address(param=p)
            return_list.append([idx1 + idx2 * 0x100, sub_idx * 0x100 + 0x10])

        return return_list

    def build_pdo(self, index=0):
        if index == 0:
            for param in self.PDO_parameters[index]:
                self.PDO_parameters[index][param].Value = self.read(param, index)
            try:
                com_vector = int(self.PDO_parameters[index]["Communications Configuration Vector"].Value)
            except KeyError:
                com_vector = int(self.PDO_parameters[index]["communications configuration vector"].Value)
            if com_vector & 1:
                self.ext = True
            if com_vector & (1 << 5):
                self.auto_tpdo = True
            if com_vector & (1 << 6):
                self.auto_rpdo = True
            if not com_vector & (1 << 7):
                return
            if com_vector & (1 << 13):
                self.auto_id = True
            if com_vector & (1 << 14):
                self.rtr = True
        else:
            for param in self.PDO_parameters[index]:
                self.PDO_parameters[index][param].Value = self.read(param, index)
            try:
                self.write("Communications Configuration Vector", self.PDO_parameters[0]["Communications Configuration Vector"].Value)
            except KeyError:
                self.write("communications configuration vector", self.PDO_parameters[0]["communications configuration vector"].Value)

        TPDO = {}
        RPDO = {}
        for j in range(12):
            i = j + 1
            try:
                lo = self.PDO_parameters[index][f"TPDO{i} COBID (low word)"].Value
                hi = self.PDO_parameters[index][f"TPDO{i} COBID (high word)"].Value
                s = self.PDO_parameters[index][f"TPDO{i} size (words)"].Value
                timeout = int(self.PDO_parameters[index][f"TPDO{i} event time"].Value)
                if s != 0 or timeout != 0:
                    idx_1 = self.PDO_parameters[index][f"TPDO{i} map1 index"].Value
                    sub_1 = (int(self.PDO_parameters[index][f"TPDO{i} map1 sub index and size"].Value) & 0xFF00) >> 8
                    idx_2 = self.PDO_parameters[index][f"TPDO{i} map2 index"].Value
                    sub_2 = (int(self.PDO_parameters[index][f"TPDO{i} map2 sub index and size"].Value) & 0xFF00) >> 8
                    idx_3 = self.PDO_parameters[index][f"TPDO{i} map3 index"].Value
                    sub_3 = (int(self.PDO_parameters[index][f"TPDO{i} map3 sub index and size"].Value) & 0xFF00) >> 8
                    idx_4 = self.PDO_parameters[index][f"TPDO{i} map4 index"].Value
                    sub_4 = (int(self.PDO_parameters[index][f"TPDO{i} map4 sub index and size"].Value) & 0xFF00) >> 8
                    TPDO[i] = self.PDO(idx=i, id_lo=lo, id_hi=hi, tx=True, timeout=timeout,
                                       idx_map={f'{self.map2name((idx_1 - 8192) * 64, sub_1 - 1, index)}': [idx_1, sub_1],
                                                f'{self.map2name((idx_2 - 8192) * 64, sub_2 - 1, index)}': [idx_2, sub_2],
                                                f'{self.map2name((idx_3 - 8192) * 64, sub_3 - 1, index)}': [idx_3, sub_3],
                                                f'{self.map2name((idx_4 - 8192) * 64, sub_4 - 1, index)}': [idx_4, sub_4]},
                                       rtr=self.rtr, ext=self.ext,
                                       t=int(self.PDO_parameters[index][f"TPDO{i} transmission type"].Value), size=s)
                    # print(f'{self.map2name((idx_1 - 8192) * 64, sub_1 - 1, index)}',
                    #       f'{self.map2name((idx_2 - 8192) * 64, sub_2 - 1, index)}',
                    #       f'{self.map2name((idx_3 - 8192) * 64, sub_3 - 1, index)}',
                    #       f'{self.map2name((idx_4 - 8192) * 64, sub_4 - 1, index)}')

            except KeyError:
                pass
            try:
                lo = self.PDO_parameters[index][f"RPDO{i} COBID (low word)"].Value
                hi = self.PDO_parameters[index][f"RPDO{i} COBID (high word)"].Value
                s = self.PDO_parameters[index][f"RPDO{i} size (words)"].Value
                timeout = int(self.PDO_parameters[index][f"RPDO{i} timeout"].Value)
                if s != 0 or timeout != 0:
                    idx_1 = self.PDO_parameters[index][f"RPDO{i} map1 index"].Value
                    sub_1 = (int(self.PDO_parameters[index][f"RPDO{i} map1 sub index and size"].Value) & 0xFF00) >> 8
                    idx_2 = self.PDO_parameters[index][f"RPDO{i} map2 index"].Value
                    sub_2 = (int(self.PDO_parameters[index][f"RPDO{i} map2 sub index and size"].Value) & 0xFF00) >> 8
                    idx_3 = self.PDO_parameters[index][f"RPDO{i} map3 index"].Value
                    sub_3 = (int(self.PDO_parameters[index][f"RPDO{i} map3 sub index and size"].Value) & 0xFF00) >> 8
                    idx_4 = self.PDO_parameters[index][f"RPDO{i} map4 index"].Value
                    sub_4 = (int(self.PDO_parameters[index][f"RPDO{i} map4 sub index and size"].Value) & 0xFF00) >> 8
                    RPDO[i] = self.PDO(idx=i, id_lo=lo, id_hi=hi, tx=False, timeout=timeout,
                                       idx_map={f'{self.map2name((idx_1 - 8192) * 64, sub_1 - 1, index)}': [idx_1, sub_1],
                                                f'{self.map2name((idx_2 - 8192) * 64, sub_2 - 1, index)}': [idx_2, sub_2],
                                                f'{self.map2name((idx_3 - 8192) * 64, sub_3 - 1, index)}': [idx_3, sub_3],
                                                f'{self.map2name((idx_4 - 8192) * 64, sub_4 - 1, index)}': [idx_4, sub_4]},
                                       rtr=self.rtr, ext=self.ext,
                                       t=self.PDO_parameters[index][f"RPDO{i} transmission type"].Value, size=s)
            except KeyError:
                pass
        self.TPDO[index] = TPDO
        self.RPDO[index] = RPDO

    def set_pdo(self, pdo, index):
        tx = pdo.tx
        if tx:
            try:
                self.TPDO[index][pdo.idx]
            except KeyError:
                self.TPDO[index][pdo.idx] = pdo
            else:
                self.TPDO[index][pdo.idx].update(pdo)

        else:
            try:
                self.RPDO[index][pdo.idx]
            except KeyError:
                self.RPDO[index][pdo.idx] = pdo
            else:
                self.RPDO[index][pdo.idx].update(pdo)

    def get_pdo(self, tx: bool, idx: int, index):
        if tx:
            return self.TPDO[index][idx]
        else:
            return self.RPDO[index][idx]

    class PDO:

        def __init__(self, idx=1, id_lo=0x0, id_hi=0x0, tx=False, timeout=0, idx_map=None,
                     rtr=False, ext=False, t=0, size=0):
            self.idx = idx
            self.id_lo = id_lo
            self.id_hi = id_hi
            self.tx = tx
            self.timeout = timeout
            self.rtr = rtr
            self.extended_id = ext
            if idx_map is not None:
                self.idx_map = idx_map
            else:
                self.idx_map = {}
            self.transmission_type = t
            self.size = size

        def new_map(self, new_map=None):
            if new_map is None:
                print(f"{'T' if self.tx else 'R'}PDO{self.idx} mapping info")
                for i, idx in enumerate(self.idx_map, 1):
                    print(f"Map{i} index: {self.idx_map[idx][0]} | sub index: {self.idx_map[idx][1]}")
                return self.idx_map
            else:
                self.idx_map = new_map

        def __len__(self):
            return len(self.idx_map)

        def __repr__(self):
            template = (f"\n{'T' if self.tx else 'R'}PDO{self.idx}:\n"
                        f"COBID Hi word: 0x{int(self.id_hi):04x} | Lo word: 0x{int(self.id_lo):04x}\n"
                        f"Transition type: {self.transmission_type}\n"
                        f"Size: {self.size}\n"
                        f"Extended ID: {self.extended_id}\n"
                        f"RTR: {self.rtr}\n"
                        f"Timeout: {self.timeout}\n"
                        f"Map: \n")
            for i, idx in enumerate(self.idx_map, 1):
                if i <= self.size:
                    template += (f"Map {i} index: 0x{int(self.idx_map[idx][0]):04X} | "
                                 f"sub-index: 0x{int(self.idx_map[idx][1]):02X} | "
                                 f"{idx}\n")
            return template

        def update(self, pdo):
            self.timeout = pdo.timeout
            self.rtr = pdo.rtr
            self.extended_id = pdo.extended_id
            self.new_map(new_map=pdo.idx_map)
            self.transmission_type = pdo.transmission_type
            self.size = pdo.size
