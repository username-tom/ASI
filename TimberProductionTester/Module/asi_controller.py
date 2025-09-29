"""asi_controller: Module for ASI Controller"""

import logging
import tkinter
from threading import Lock
from time import sleep
from Module.ComABC import ComABC
import xml.etree.ElementTree as ET
from Module.TTLcom import TTLcom, CommError
from Module.Parameter import Parameter
from Module.util import parse_etree, load_using_param_names, signed
from Module.DynoABCs import DynoBrake, DynoPoller
from threading import Thread
from tkinter import Toplevel, Label
from tkinter.ttk import Progressbar

U = 0  # Phase U
V = 1  # Phase V
W = 2  # Phase W
PHASE = ["Phase U", "Phase V", "Phase W"]
MAX_COM_LOSS = 3


class ASIController(DynoPoller, DynoBrake, ComABC):
    """ASIController: ASI Controller class"""

    def __init__(self, com_port='COM5', baud_rate=115200, mb_address=1,
                 object_dictionary="Dictionary/6019_ASIObjectDictionary.xml",
                 run_params_file="Parameter Files/Run parameters for ASI controller.csv",
                 log_params_file="controller.csv",):

        self.run_parameters = {}
        self.com_id = mb_address
        self.baud_rate = baud_rate
        self.port_name = com_port
        self.checksum_retry = MAX_COM_LOSS
        self.io_lock = Lock()
        self.connected = False

        self.modbus = TTLcom(com_port=self.port_name, baud_rate=self.baud_rate, mbAddress=self.com_id)
        self.etree = parse_etree(f"{object_dictionary}")

        self.log_params = f"{log_params_file}"
        self.load_run_params(f"{run_params_file}")
        self.run_params_file = run_params_file

        self.firmware = 0
        try:
            self._version_check()
        except (AttributeError, CommError):
            raise CommError
        if self.firmware == 0 or self.firmware is None:  # quicker return from bad connection
            return
        self.connected = True

        self._version_fork()
        self._com_prep()
        self._init_fault_descriptions()


        self.brk_dir = 0
        self.poll_enabled = False
        self.polling_thread = None
        self._poll_interval = 1
        self.cur_torque = 0
        self.motor_discovering = False


    def __repr__(self):
        template = (f"ASI Controller on {self.port_name} @ {self.baud_rate} with ID: {self.com_id}\n"
                    f"Firmware: {self.firmware if self.firmware != 0 else self.read('software revision level')}")
        return template

    def __del__(self):
        try:
            self.stop_test()
        except (AttributeError, OSError):
            pass
        try:
            if hasattr(self.modbus, 'modbus'):
                self.modbus.modbus.serial.close()
        except AttributeError:
            pass

    def _version_check(self):
        self.firmware = self.read("software revision level")

    def _version_fork(self):
        processed = self.firmware
        if processed < 6.013:
            processed = 6.014
        processed = str(processed)
        processed = processed.split('.')
        processed = f"{processed[0]}{processed[1]}"
        if processed.startswith('1'):
            processed = processed[1:]
        self.etree = parse_etree(f"Dictionary/{processed}_ASIObjectDictionary.xml")
        self.dictionary_file = f"Dictionary/{processed}_ASIObjectDictionary.xml"

        if self.firmware < 6.021:
            self.code = 27021
        else:
            self.code = [0x1114, 0x8FFC, 0x8250]

    def _com_prep(self):
        self.modbus.controller_parameter(self.run_parameters)

    def set_torque(self, target: float = 0.0):
        # self.write("Remote torque command", -target)
        any_faults = self.check_faults()
        if any_faults:
            self.clear_faults()

        # self.write("Remote maximum braking current", int(target))
        # Regardless of direction, negative torque = braking, positive torque = boosting
        if self.brk_dir == 0:
            self.write("Remote torque command", -target)
        else:
            self.write("Remote torque command", target)
        self.cur_torque = target
        # self.cur_torque = self.read("Remote torque command")

    def start(self):
        print(f"ASI Brake starting")
        self.write("Control command source", 0)
        self.write("Speed regulator mode", 1)
        self.write("Regeneration battery current limit", 100)
        self.write("Remote speed command", 0)
        self.write("Remote Speed Command in RPM", 0)
        self.write("Remote maximum motoring current", 0)
        self.write("Remote maximum braking current", 100)
        self.write("Remote torque command", 0)
        self.start_remote_motor()
        self.set_direction()

    def stop_switch(self):
        # switching to speed mode to prevent RPM shoot up
        self.write("Remote Speed Command in RPM", 0)
        self.write("Remote speed command", 0)
        self.write("Remote maximum braking current", self.cur_torque)
        self.write("Speed regulator mode", 0)

    def stop(self):
        try:
            self.stop_remote_motor()
        except AttributeError:
            pass

    def stop_test(self):
        self.stop()

    def set_direction(self):
        if self.get_rpm() > 0:
            self.brk_dir = 0
        else:
            self.brk_dir = 1

    def load_run_params(self, names):
        self.run_parameters = load_using_param_names(self.etree, names)
        if hasattr(self, '_log_params'):
            for param in self._log_params:
                try:
                    self.run_parameters[self._log_params[param].Name]
                except (KeyError, IndexError):
                    self.run_parameters[self._log_params[param].Name] = self._log_params[param]

    def remote_speed_mode(self, watchdog=None, **kwargs):
        """
        Remotely starts the motor in speed mode

        Parameters:
            watchdog : Thread, optional
            kwargs : dict, required {
                speed : int, required. Remote Speed Command in RPM
                motoring_current : float, optional. Remote maximum motoring current, default to 100
                braking_current : float, optional. Remote maximum braking current, default to 0
                speed_command : float, optional. Remote speed command}
        """
        if not self.remote_faults_handle():
            return
        rated_rpm = self.read('Rated motor speed')
        if self.firmware < 6.019:
            self.write("Control command source", 0)
            self.write("Speed regulator mode", 0)
            self.write("Remote speed command",
                       kwargs['speed'] / rated_rpm * 100
                       if 'speed_command' not in kwargs.keys() else
                       kwargs['speed_command'])

            # motoring and braking current should be the same for this mode,
            # there is no scenario yet where they would be different
            self.write("Remote maximum braking current",
                       kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 0)
            self.write("Remote maximum motoring current",
                       kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100)
        else:
            self.write("Control command source", 0)
            self.write("Speed regulator mode", 0)
            self.write("Remote Speed Command in RPM", kwargs['speed'] if 'speed' in kwargs.keys() else 0)
            self.write("Remote speed command",
                       kwargs['speed'] / rated_rpm * 100 if 'speed_command' not in kwargs.keys() else kwargs['speed_command'])

            # motoring and braking current should be the same for this mode,
            # there is no scenario yet where they would be different
            self.write("Remote maximum braking current",
                       kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 0)
            self.write("Remote maximum motoring current",
                       kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100)
        # print("Starting speed mode")
        if watchdog is None:
            self.start_remote_motor()
        else:
            try:
                watchdog.start()
            except RuntimeError:
                pass

    def check_faults(self):
        faults_found = []
        for name in self.faults_parameters:
            descriptions = self.faults_parameters[name]
            bit_string = self.read(name)

            if bit_string is None:
                continue
            else:
                # remove "0x" and the "b" at the end from bin()'s output
                bit_string = bin(int(bit_string))[2:]
                bit_string = bit_string.zfill(16)
                try:
                    for i, bit in enumerate(bit_string, 1):
                        description = descriptions[i]

                        # bits that are marked "Reserved" or "Obsolete" we don't care about during operation.
                        if ("Reserved" not in description and
                                "reserved" not in description and
                                "Obsolete" not in description and
                                "obsolete" not in description and
                                bit == '1'):
                            # eg. if the rated system voltage were too high and the controller triggered the proper fault, description would be:
                            #     "[parameter]-[bit  #]: [description]" ->
                            #     "faults-bit  0: Controller over voltage (flash code 1,1)"
                            faults_found.append(name + '-' + description)
                except IndexError:
                    pass

        return faults_found

    def remote_faults_handle(self):
        any_faults = self.check_faults()
        if any_faults:
            return False
        return True

    def motor_discovery(self, mode=1):
        self.motor_discovering = True
        self.write("Motor discover mode", mode)
        logging.info(f"Motor discovery mode {mode} message sent")


    def retrieve_discovery(self, mode):
        if self.motor_discovering:
            self.motor_discovering = False
        else:
            return

        if mode == 0:
            return
        elif mode == 1:
            return self.read("autotune Rs"), self.read("autotune Ls")
        elif mode == 2:
            return (int(self.read("autotune rated rpm")),
                    self.read("autotune hall offset angle"),
                    [int(self.read("autotune hall sector[0]")),
                     int(self.read("autotune hall sector[1]")),
                     int(self.read("autotune hall sector[2]")),
                     int(self.read("autotune hall sector[3]")),
                     int(self.read("autotune hall sector[4]")),
                     int(self.read("autotune hall sector[5]")),
                     int(self.read("autotune hall sector[6]")),
                     int(self.read("autotune hall sector[7]"))])

    def stop_motor_discovery(self):
        logging.info('Interrupting Motor Discovery')
        self.motor_discovering = False
        self.write('Motor discover mode', 0)

    def in_foldback(self):
        faults = self.check_faults()

        for fault in faults:
            if "ContrlTempFLDBK" in fault or "MotorTempFLDBK" in fault or "Wheel speed sensor" in fault:
                return True

        return False

    def get_rpm(self):
        return self.read("motor rpm")

    def ramp_to(self, target=0, step=10, period=5):
        """Brake ramping function"""
        if step < 1:
            step = 1
        if period <= 0:
            period = 0.01
        scope = target - self.cur_torque
        sleep(period / step)
        for _ in range(int(step)):
            self.set_torque(self.cur_torque + scope / step)
            sleep(period / step)

    def start_remote_motor(self):
        self.write("Remote state command", value=2)

    def stop_remote_motor(self):
        self.write("Remote state command", value=0)

    def clear_faults(self):
        self.write("Fault clear", value=1)

    def _init_fault_descriptions(self):
        tree = self.etree
        faults_xpath = "//ParameterDescription[Name='faults']//Description"
        faults2_xpath = "//ParameterDescription[Name='faults2']//Description"
        warnings_xpath = "//ParameterDescription[Name='warnings']//Description"
        warnings2_xpath = "//ParameterDescription[Name='warnings2']//Description"

        self.faults_parameters = {
                "faults": [description.text for description in tree.findall(faults_xpath)][::-1],
                "faults2": [description.text for description in tree.findall(faults2_xpath)][::-1],
                # Need "warnings" to check for motor and controller foldback
                "warnings": [description.text for description in tree.findall(warnings_xpath)][::-1],
                "warnings2": [description.text for description in tree.findall(warnings2_xpath)][::-1]
            }

    def raise_access_level(self):
        if self.firmware < 6.022:
            self.write("Parameter access code", self.code)
        else:
            self.write("Parameter access code 1", signed(self.code[0]))
            self.write("Parameter access code 2", signed(self.code[1]))
            self.write("Parameter access code 3", signed(self.code[2]))

    def reset_access_level(self):
        if self.firmware < 6.022:
            self.write("Parameter access code", 0)
        else:
            self.write("Parameter access code 1", 0)
            self.write("Parameter access code 2", 0)
            self.write("Parameter access code 3", 0)

    def save_to_flash(self):
        retries = 6
        result = False
        count = 0
        while (count < retries and
               result != 4096.0):
            self.write("Write parameters to flash", 0x7FFF)
            sleep(3)

            result = self.read("Write parameters to flash")

            count = count + 1
            sleep(0.5)
        return True

    def param_name(self, param):
        if isinstance(param, int):
            element = self.etree.find(f"//ParameterDescription[Address='{param}']")
            p = Parameter()
            p.set_using_xml_element(element)
            return p.Name
        elif isinstance(param, Parameter):
            return param.Name
        else:
            return False

    def load_parameters(self, file, master=None, indicator='DUT'):
        ps = ET.parse(file).getroot().findall('SerializableParameter')
        if master is not None:
            total = len(ps)
            popup = Toplevel(master, background='white')
            temp = Label(popup, text=indicator, background='white')
            temp.grid(column=0, row=0, columnspan=2)
            pb = Progressbar(popup, orient='horizontal', mode='determinate', length=300)
            pb.grid(column=0, row=1, columnspan=2, padx=10, pady=20)

        for i, p in enumerate(ps):
            address = int(p.find('Address').text)
            value = int(p.find('Value').text)
            self.write(address, value)
            logging.debug(f"[{i + 1}/{len(ps)}] Updating address {address} with value {value}")
            if master is not None:
                pb['value'] = i / total * 100
        if master is not None:
            popup.destroy()

    def write(self, name, value, log=False):
        with self.io_lock:  # only 1 program or script should read or write to the controller at any time.
            self.modbus.controller_parameter(self.run_parameters)
            try:
                if self.modbus.write(name, value):
                    if isinstance(name, str):
                        self.run_parameters[name].Value = value
                        self.controller_parameter()
                else:
                    self.connected = False
            except CommError:
                self.connected = False

    def read(self, name):
        with self.io_lock:  # only 1 program or script should read or write from an asi controller at any time.
            self.modbus.controller_parameter(self.run_parameters)
            try:
                response = self.modbus.read(name)
                if isinstance(response, float) or isinstance(response, int):
                    self.run_parameters[name].Value = response
                    self.controller_parameter()
                    return response
                else:
                    self.connected = False
                    return self.run_parameters[name].Value
            except CommError:
                self.connected = False
                return self.run_parameters[name].Value

    def controller_parameter(self, params=None):
        self.run_parameters = self.modbus.run_parameters

    @property
    def poll_enabled(self):
        if hasattr(self, '_poll_enabled'):
            return self._poll_enabled

    @property
    def poll_interval(self):
        return self._poll_interval

    @property
    def log_params(self):
        return self._log_params

    # Setters
    @poll_enabled.setter
    def poll_enabled(self, val):
        self._poll_enabled = val

    @poll_interval.setter
    def poll_interval(self, val):
        self._poll_interval = val

    # in this implementation, log_params is a file that contains a list of parameter names
    @log_params.setter
    def log_params(self, logParams):
        self._log_params = {}
        with open(logParams, "r") as f:
            f.readline()

            for line in f.readlines():
                name, address, scale, unit = line.strip().split(",")
                # name = line.strip().split(",")[0]

                param = Parameter(name, address, scale, unit)
                self._log_params[name] = param
                # self._log_params[name] = self.run_parameters[name]

    def poll(self):
        while self.poll_enabled:

            if self.modbus.com_loss >= MAX_COM_LOSS:
                self.connected = False
                break
            else:
                self.connected = True
            for param in self._log_params:
                try:
                    self.log_params[param].Value = self.read(param)
                except:
                    break
                sleep(self._poll_interval / len(self.log_params) * 0.3)

            sleep(self._poll_interval * 0.6)

    # Methods
    def start_polling(self, pollInterval=1):
        for p in self._log_params:
            logging.debug(self._log_params[p].Name)

        self.polling_thread = Thread(target=self.poll)
        self.polling_thread.daemon = True
        self.poll_interval = pollInterval
        self.poll_enabled = True
        self.polling_thread.start()

    def stop_polling(self):
        if self.poll_enabled:
            self.poll_enabled = False
            self.polling_thread = None
