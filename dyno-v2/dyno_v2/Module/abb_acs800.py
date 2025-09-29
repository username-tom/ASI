import logging
import dyno_v2.Module.BACmodbus as BACmodbus
from dyno_v2.Module.TTLcom import TTLcom
from dyno_v2.Module.DynoABCs import DynoBrake
from dyno_v2.Module.util import parse_etree
from time import sleep
from threading import Thread


MAX_COM_LOSS = 3


class AbbAcs800(DynoBrake):

    def __init__(
            self,
            port='COM12',
            baud=19200,
            auto=True,
            root='',
            mode='torque',
            direction='forward',
            object_dictionary=f"dyno_v2/ABB Parameters.xml",
            log_params_file="dyno_v2/Parameter Files/abb.csv"
    ):

        # NOTE: it seems modbus parameters are 0-indexed while controller manual is 1-indexed
        # this leads to the lovely property that modbus addr 1000 is ABB parameter 10.01, 1001 = 10.02, etc
        # isn't that fantastic? Doesn't that make referencing the manual super easy and not at all error-prone?
        # ...
        # be aware.

        # Parameter setup - just create data structure, nothing written to instrument
        # self.SSDir1 = BACmodbus.Parameter("EXT1 Start/Stop/Dir", 1000, 1, "", 2, 10)
        # self.SSDir2 = BACmodbus.Parameter("EXT2 Start/Stop/Dir control", 1001, 1, "", 7, 10)
        # self.SvsT = BACmodbus.Parameter("Keypad Speed or Torque", 1100, 1, "", 2, 2)
        # self.Tref = BACmodbus.Parameter("Torque signal source", 1101, 1, "", 8, 8)
        # self.extSref = BACmodbus.Parameter("External Speed signal source", 1102, 1, "", 3, 20)
        # self.extTref = BACmodbus.Parameter("External Torque signal source", 1105, 1, "", 3, 20)
        # self.RunCMD = BACmodbus.Parameter("Run command signal source", 1600, 1, "", 1, 8)
        # self.Ref1 = BACmodbus.Parameter("Ref1 0-10000", 1, 1, "")
        # self.Ref2 = BACmodbus.Parameter("Ref2 0-10000", 2, 1, "")
        # self.StatusWord = BACmodbus.Parameter("Status word", 3, 1, "")
        # self.CtrlWord = BACmodbus.Parameter("Control Word", 0, 1, "")
        # self.CommFault = BACmodbus.Parameter("Comms Fault Handling", 3017, 1, "", 2, 2)
        # self.Direction = BACmodbus.Parameter("Direction", 1002, 1, "", 1, 1)
        # self.FaultReset = BACmodbus.Parameter("Fault Reset", 1603, 1, "", 1, 8)
        # self.min_speed = BACmodbus.Parameter("Minimal Speed", 2000, 1, "")
        # self.max_speed = BACmodbus.Parameter("Maximum Speed", 2001, 1, "")
        self.connected = False
        self.run_parameters = {}

        self.root_dir = f"{root}"
        self.cur_torque = 0
        self.cur_rpm = 0

        with open(f"{self.root_dir}/{log_params_file}", "r") as f:
            f.readline()

            for line in f.readlines():
                name, address, scale, unit, manual, autoT = line.strip().split(",")

                param = BACmodbus.Parameter(name, int(address), int(scale), unit,
                                            int(manual) if manual != '' else None,
                                            int(autoT) if autoT != '' else None)
                self.run_parameters[name] = param

        self.log_params = {}

        self.CWSpeller = CtrlWordSpeller()
        self.mode = mode

        self.etree = parse_etree(object_dictionary)

        for section in self.etree.findall('Parameters'):
            for element in section.findall('ParameterDescription'):
                parameter = BACmodbus.Parameter(
                    name=element.find('Name').text,
                    unit=element.find('Units').text
                )
                self.log_params[parameter.Name] = parameter

        # initiate modbus connection to instrument
        self.port = port
        self.baud = baud
        self.com_id = 1
        self.device = BACmodbus.BAC(1, port, baud)
        if hasattr(self.device, 'modbus'):
            # self.device.modbus.serial.timeout = 1  # Change from default 0.05s
            self.connected = True
        self.stop()

        # write shared setup params to instrument
        if self.mode == 'torque':
            self.torque_mode()
        else:
            self.speed_mode()
        self.init_ABB(auto)
        self.set_abb_direction(direction)

    def __repr__(self):
        template = f"ABB Dyno on {self.port} @ {self.baud}"
        return template

    def __del__(self):
        if hasattr(self.device, 'modbus'):
            self.stop()
            self.device.modbus.serial.close()
            self.connected = False

    def init_ABB(self, auto=True):
        # write auto/manual specific params
        if auto:
            self.noisyWrite(self.run_parameters["EXT1 Start/Stop/Dir"].autoT,
                            self.run_parameters["EXT1 Start/Stop/Dir"])  # set control bits to look at modbus CTRL WRD
            self.noisyWrite(self.run_parameters["EXT2 Start/Stop/Dir"].autoT,
                            self.run_parameters["EXT2 Start/Stop/Dir"])  # set control bits to look at modbus CTRL WRD
            self.noisyWrite(self.run_parameters["Keypad Speed or Torque"].autoT,
                            self.run_parameters["Keypad Speed or Torque"])
            self.noisyWrite(self.run_parameters["Torque signal source"].autoT,
                            self.run_parameters["Torque signal source"])
            self.noisyWrite(self.run_parameters["External Speed signal source"].autoT,
                            self.run_parameters["External Speed signal source"])  # set EXT1 (speed ref) to Fieldbus REF1
            self.noisyWrite(self.run_parameters["External Torque signal source"].autoT,
                            self.run_parameters["External Torque signal source"])  # set EXT2 (torque ref) to Fieldbus REF2
            self.noisyWrite(self.run_parameters["Run command signal source"].autoT,
                            self.run_parameters["Run command signal source"])  # set run to be enabled/disabled via bit 3 of CTRL WRD
            self.noisyWrite(self.run_parameters["Comms Fault Handling"].autoT,
                            self.run_parameters["Comms Fault Handling"])
            self.noisyWrite(self.run_parameters["Direction"].autoT,
                            self.run_parameters["Direction"])
            self.noisyWrite(self.run_parameters["Fault Reset"].autoT,
                            self.run_parameters["Fault Reset"])  # allows fault resetting through CTRL WRD
            self.remote = True
        else:
            self.noisyWrite(self.run_parameters["EXT1 Start/Stop/Dir"].manual,
                            self.run_parameters["EXT1 Start/Stop/Dir"])  # set control bits to look at keypad
            self.noisyWrite(self.run_parameters["EXT2 Start/Stop/Dir"].manual,
                            self.run_parameters["EXT2 Start/Stop/Dir"])  # set control bits to look at keypad
            self.noisyWrite(self.run_parameters["Keypad Speed or Torque"].manual,
                            self.run_parameters["Keypad Speed or Torque"])
            self.noisyWrite(self.run_parameters["Torque signal source"].manual,
                            self.run_parameters["Torque signal source"])
            self.noisyWrite(self.run_parameters["External Speed signal source"].manual,
                            self.run_parameters["External Speed signal source"])  # set EXT1 (speed ref) to keypad
            self.noisyWrite(self.run_parameters["External Torque signal source"].manual,
                            self.run_parameters["External Torque signal source"])  # set EXT2 (torque ref) to keypad
            self.noisyWrite(self.run_parameters["Run command signal source"].manual,
                            self.run_parameters["Run command signal source"])  # set run to be enabled/disabled via keypad
            self.noisyWrite(self.run_parameters["Comms Fault Handling"].manual,
                            self.run_parameters["Comms Fault Handling"])
            self.noisyWrite(self.run_parameters["Direction"].manual,
                            self.run_parameters["Direction"])
            self.noisyWrite(self.run_parameters["Fault Reset"].manual,
                            self.run_parameters["Fault Reset"]) # allows fault resetting through keypad
            self.remote = False
    ################### implementation for Dyno Brake
    # Methods
    def set_torque(self, target: float = 0.0):
        logging.debug(f"ABB BRK set torque to {target}")
        self.noisyWrite(round(target * 100.0, 1), self.run_parameters["Ref2"])
        self.cur_torque = target

    def ramp_to(self, target=0, step=10, period=5):
        if step < 1:
            step = 1
        if period <= 0:
            period = 0.01
        scope = target - self.cur_torque
        sleep(period / step)
        for _ in range(int(step)):
            self.set_torque(self.cur_torque + scope / step)
            sleep(period / step)

    def set_rpm(self, target: float = 0.):
        logging.debug(f"ABB BRK set speed to {target}")
        self.noisyWrite(int(target / 0.075), self.run_parameters["Ref1"])
        self.cur_rpm = target

    def set_limits(self, direction="f"):
        if direction in ["f", 1, "forward"]:
            self.noisyWrite(5700, self.run_parameters["Maximum Speed"])
            self.noisyWrite(0, self.run_parameters["Minimal Speed"])
        elif direction in ["r", 0, "reverse", "backward"]:
            self.noisyWrite(-5700, self.run_parameters["Minimal Speed"])
            self.noisyWrite(0, self.run_parameters["Maximum Speed"])
        elif direction in ["b", 2, "both"]:
            self.noisyWrite(5700, self.run_parameters["Maximum Speed"])
            self.noisyWrite(-5700, self.run_parameters["Minimal Speed"])

    def set_abb_direction(self, direction):
        if direction in ["f", 1, "forward"]:
            self.noisyWrite(1,
                            self.run_parameters["Direction"])
            # self.set_limits()
        elif direction in ["r", 2, "reverse", "backward"]:
            self.noisyWrite(2,
                            self.run_parameters["Direction"])
            # self.set_limits('r')
        elif direction in ["b", 3, "both", "request"]:
            self.noisyWrite(3,
                            self.run_parameters["Direction"])
            # self.set_limits('b')

    def start(self):
        print("ABB Brake starting!")
        # self.noisyWrite( self.CWSpeller.setEnableBit(), self.run_parameters["Control Word"])
        # print(bin(self.CWSpeller.setEnableBit()))
        if self.CWSpeller.get_external_control_bit() == 0:
            # speed mode EXT1
            turnOnABB_CMD = [6, 1030, 1142, 1143, 1151]
            #    6 = 0000000000000110
            # 1030 = 0000010000000110
            # 1142 = 0000010001110110
            # 1143 = 0000010001110111
            # 1151 = 0000010001111111
            # bit:   5432109876543210

        else:
            # torque mode EXT2
            turnOnABB_CMD = [6, 3078, 3190, 3191, 3199]
            #    6 = 0000000000000110
            # 3078 = 0000110000000110
            # 3190 = 0000110001110110
            # 3191 = 0000110001110111
            # 3199 = 0000110001111111
            # bit:   5432109876543210

        for i in range(len(turnOnABB_CMD)):
            self.noisyWrite(turnOnABB_CMD[i], self.run_parameters["Control Word"])

    def stop(self):
        print("ABB Brake stopping!")
        # self.noisyWrite( self.CWSpeller.setEnableBit(), self.run_parameters["Control Word"])
        # print(bin(self.CWSpeller.setEnableBit()))
        if self.CWSpeller.get_external_control_bit() == 0:
            # speed mode EXT1
            turnOffABB_CMD = [1143, 1142, 1030, 6]
            #    6 = 0000000000000110
            # 1030 = 0000010000000110
            # 1142 = 0000010001110110
            # 1143 = 0000010001110111
            # 1151 = 0000010001111111

        else:
            # torque mode EXT2
            turnOffABB_CMD = [3191, 3190, 3078, 6]
            #    6 = 0000000000000110
            # 3078 = 0000110000000110
            # 3190 = 0000110001110110
            # 3191 = 0000110001110111
            # 3199 = 0000110001111111

        for i in range(len(turnOffABB_CMD)):
            self.noisyWrite(turnOffABB_CMD[i], self.run_parameters["Control Word"])

    def torque_mode(self):
        self.set_limits('r')
        self.set_abb_direction('f')
        self.noisyWrite(2, self.run_parameters["Keypad Speed or Torque"])  # make keypad output on REF2 (torque %)
        # self.noisyWrite(9, self.run_parameters["Torque signal source"])  # point drive at EXT2 for external torque ref
        self.CWSpeller.set_external_control_bit('EXT2')
        self.clearFault()
        self.mode = 'torque'
        print("ABB in TORQUE mode")

    def speed_mode(self):
        # self.set_limits('b')
        self.noisyWrite(1, self.run_parameters["Keypad Speed or Torque"])  # make keypad output on REF1 (speed RPM)
        # self.noisyWrite(9, self.run_parameters["Torque signal source"])  # point drive at EXT1 for external torque ref
        self.CWSpeller.set_external_control_bit('EXT1')
        self.clearFault()
        self.mode = 'speed'
        print("ABB in SPEED mode")

    def getStatus(self):
        return bin(int(self.device.readParameter(self.run_parameters["Status Word"])))

    def clearFault(self):
        self.noisyWrite(self.CWSpeller.setFaultBit(), self.run_parameters["Control Word"])
        self.noisyWrite(self.CWSpeller.clearFaultBit(), self.run_parameters["Control Word"])

    # NC 2021-11-22 - Readback had rounding issues, haven't yet seen any bad writes so removed check
    # TW 2022-07-21 - Set timeout solves com issues line 40
    # TW 2022-12-02 - BACmodbus ~= TTLcom
    def noisyWrite(self, value, parameter):
        # while self.device.readParameter(parameter) != value:
        self.device.writeValueForParameter(value, parameter)
        if self.device.com_loss > MAX_COM_LOSS:
            self.connected = False

    def noisyRead(self, parameter):
        ans = self.device.readParameter(parameter)
        if self.device.com_loss > MAX_COM_LOSS:
            self.connected = False
        return ans

    def read(self, param: str):
        if param == "Speed":
            return self.cur_rpm
        elif param == "Torque":
            return self.cur_torque
        else:
            return self.noisyRead(self.run_parameters[param])


class CtrlWordSpeller:
    def __init__(self):
        self.bits: list[int] = [0] * 16
        # Operation Enable/Stop Flags
        self.bits[0] = 1  # OFF1, PRESTART ON/OFF TOGGLE, 0 means can't switch on
        self.bits[1] = 1  # COAST OFF, 0 means coast to stop
        self.bits[2] = 1  # EMERGE OFF, 0 means brake to stop fast
        self.bits[3] = 0  # INHIBIT OPERATION: MAIN ON/OFF TOGGLE, 1 means motor starts
        # Ramp Generator Flags
        self.bits[4] = 0  # Ramp generator: leave off
        self.bits[5] = 0  # Ramp generator: leave off
        self.bits[6] = 0  # Ramp generator: leave off

        self.bits[7] = 0  # FAULT RESET: 0->1 will reset a fault state, then need to set back to 0

        self.bits[8] = 0  # INCHING, unused
        self.bits[9] = 0  # INCHING, unused

        self.bits[10] = 1  # Fieldbus control enable, always leave at 1 or the instrument will start ignoring you

        self.bits[11] = 1  # set external control to EXT2. 0 means EXT1.

        self.bits[12] = 0  # unused
        self.bits[13] = 0  # unused
        self.bits[14] = 0  # unused
        self.bits[15] = 0  # unused

    # compose the bitstring, reverse it to match ABB LSB notation, and return the binary number as a base10 integer
    def word(self) -> int:
        val = int("".join(str(x) for x in self.bits)[::-1], base=2)
        print(f"Composed Control Word: {val}")
        return val

    def setFaultBit(self) -> int:
        self.bits[7] = 1  # FAULT RESET: 0->1 will reset a fault state, then need to set back to 0
        return self.word()

    def clearFaultBit(self) -> int:
        self.bits[7] = 0  # FAULT RESET: 0->1 will reset a fault state, then need to set back to 0
        return self.word()

    def setEnableBit(self) -> int:
        self.bits[3] = 1  # INHIBIT OPERATION: MAIN ON/OFF TOGGLE, 1 means motor starts
        return self.word()

    def clearEnableBit(self) -> int:
        self.bits[3] = 0  # INHIBIT OPERATION: MAIN ON/OFF TOGGLE, 1 means motor starts
        return self.word()

    def set_external_control_bit(self, bit=None) -> None:
        if bit is None:
            self.bits[11] = 1 - self.bits[11]
        elif bit in [0, 1]:
            self.bits[11] = bit
        elif isinstance(bit, str):
            if bit.lower() == 'ext1':
                self.bits[11] = 0
            elif bit.lower() == 'ext2':
                self.bits[11] = 1
            else:
                print(f"Bad input: {bit}\nPlease specify EXT1 or EXT2\nTry again")

    def get_external_control_bit(self) -> int:
        # print(f"External Control - {'EXT1' if self.bits[11] == 0 else 'EXT2'}")
        return self.bits[11]

# speller = CtrlWordSpeller()
# value: int = speller.word()
# print(value)
# print(bin(value))
