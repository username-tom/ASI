"""asi_controller: Module for ASI Controller"""

import logging
import csv
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from os import makedirs
from pathlib import Path
from threading import Thread, Lock
from time import sleep
from tkinter import simpledialog, Toplevel
from tkinter.ttk import Progressbar

import can

# pylint: disable=import-error
from dyno_v2.Module.CANcom import CANcom
from dyno_v2.Module.ComABC import ComABC
from dyno_v2.Module.DynoABCs import DynoBrake, DynoPoller
from dyno_v2.Module.TTLcom import TTLcom
from dyno_v2.Module.j1939 import *
from dyno_v2.Module.Parameter import Parameter
from dyno_v2.Module.util import signed, parse_etree, load_using_param_names, get_scale_value, indent
from dyno_v2.Module.exceptions import *
try:
    from dyno_v2.Module.dyno_parameters import ASI_FOLDBACKS
except ImportError:
    ASI_FOLDBACKS = {}

U = 0  # Phase U
V = 1  # Phase V
W = 2  # Phase W
PHASE = ["Phase U", "Phase V", "Phase W"]
MAX_COM_LOSS = 3


class ASIController(DynoPoller, DynoBrake, ComABC):
    """ASIController: ASI Controller class"""

    remote_mode = {}

    def __init__(
            self,
            com_port='COM5',
            baud_rate=115200,
            mb_address=1,
            is_can=False,
            all_params=False,
            log_file="error",
            root='',
            secondary=None,
            can_bus=None,
            j1939=False,
            object_dictionary=f"ASIObjectDictionary.xml",
            log_params_file="Parameters to log/controller.csv",
            run_params_file="Parameter Files/Run parameters for ASI controller default.csv"
    ):
        self.connected = False
        self.run_parameters = {}
        self.can = is_can
        self.com_id = mb_address
        self.baud_rate = baud_rate
        self.port_name = com_port
        self.heavy_duty = all_params
        self.root_dir = f"{root}"
        self.checksum_retry = 4
        self.io_lock = Lock()
        self.is_j1939 = j1939

        if self.can:
            if secondary is not None and can_bus is not None:
                self.can_bus = can_bus
                if len(self.can_bus.id) == 1:
                    self.can_bus.id.append(int(secondary))
                self.com_id = int(secondary)
                self.secondary = True
            else:
                self.secondary = False
                try:
                    self.can_bus = CANcom(can_port=self.port_name, bit_rate=self.baud_rate, can_id=self.com_id)
                except (ConnectionInterruptedError, CommLossError) as e:
                    logging.error(f"Connection Failed: {e}")
                    raise ConnectionError
            self.pdo_parameters = {}
        elif self.is_j1939:
            self.etree = parse_etree(f"{self.root_dir if self.root_dir else ''}/dyno_v2/{object_dictionary}")
            self.j1939_device = J1939com(tree=self.etree, bit_rate=self.baud_rate,
                                         parameters=f'{self.root_dir if self.root_dir else ""}/dyno_v2/Parameter Files/J1939_BAC.xml')
            self.j1939_device.startListening()
        else:
            self.modbus = TTLcom(com_port=self.port_name, baud_rate=self.baud_rate, mbAddress=self.com_id)

        try:
            self.etree = parse_etree(f"{self.root_dir if self.root_dir else ''}/{object_dictionary}")
        except OSError:
            self.root_dir = f"{root}/dyno_v2"
            self.etree = parse_etree(f"{self.root_dir if self.root_dir else ''}/{object_dictionary}")
        finally:
            self.dictionary_file = f"{self.root_dir if self.root_dir else ''}/{object_dictionary}"

        """
        KS 1/6/2022, self._log_params is used everywhere else in this file to set self.log_params here 
                    the '_' is important
                    if self._log_params is used here, it will set this to be a string and not read the file given to it
        """
        self.log_params = f"{self.root_dir if self.root_dir else ''}/{log_params_file}"
        self.load_run_params(f"{self.root_dir if self.root_dir else ''}/{run_params_file}")
        self.run_params_file = run_params_file

        self.firmware = 0
        try:
            self._version_check()
        except (CommLossError, ConnectionError):
            return
        if self.firmware == 0 or self.firmware is None:  # quicker return from bad connection
            return

        self._version_fork()
        self._com_prep(secondary)
        self._init_fault_descriptions()

        # self.errorpath = Path("C:/ASI_Controller_Log/Error Log/")
        # self._errordir = self.errorpath / datetime.now().strftime('%Y-%m-%d-%H-%M')
        # # self._errordir.mkdir(parents=True, exist_ok=True)
        # # set up logging param defaults
        # self._errorfile = self._errordir / f"{log_file.replace('.csv', '')}.csv"

        self.poll_enabled = False
        self.polling_thread = None
        self._poll_interval = 1
        self.cur_torque = 0

        # self.auto_TPDO = True if self.read("Communications Configuration Vector") & (1 << 5) == 1 else False
        # self.auto_RPDO = True if self.read("Communications Configuration Vector") & (1 << 6) == 1 else False

        # update parameter

        self.barcode = {"label_id": None,
                        "mfg_code": None,
                        "part_num": None,
                        "hardware": None,
                        "revision": None,
                        "firmware": None,
                        "parameter": None,
                        "serial_num": None,
                        "part#": None}

        self.brk_dir = 0
        self.subprocess = None
        self.can_move = False
        self.motor_discovering = False
        self.discovery_channel = None

        """
        Some of our parameter files, like 92-279 use these locks
        If set, values cannot be read from or written to the controller.
        So undo this before doing ANYTHING so that the test script(s) don't have to check if they have these locks,
        KS, 3/18/2022,
        """
        # always get the access level and code based on what's currently on the controller.
        #

        self._get_access_level()
        self.disable_read_write_locks()
        self.can_motor_move()

        self.connected = True

    def __repr__(self):
        template = (f"ASI Controller on {self.port_name} @ {self.baud_rate} with ID: {self.com_id}\n"
                    f"Firmware: {self.firmware if self.firmware != 0 else self.read('software revision level')}\n"
                    f"Polling: {self.poll_enabled}")
        return template

    def __del__(self):
        try:
            self.stop_test()
        except (AttributeError, CommLossError):
            pass
        try:
            if self.poll_enabled:
                self.stop_polling()
        except (AttributeError, CommLossError):
            pass
        try:
            if self.can:
                self.can_bus.can_pdo_handle = self.can_pdo_handle_del
                self.can_bus.listening = False
                self.can_bus.__del__()
            else:
                if hasattr(self.modbus, 'modbus'):
                    self.modbus.modbus.serial.close()
        except (AttributeError, CommLossError):
            pass

    def _version_check(self):
        # if not self.can:
        try:
            self.firmware = self.read("software revision level")
        except CommLossError:
            print("0.000")
            raise CommLossError
        except J1939TimeoutError:
            self.j1939_device.__del__()
            raise ConnectionError
        try:
            print(f"{self.firmware:.3f}")
        except TypeError:
            print("0.000")
            # return

    def _version_fork(self):
        processed = self.firmware
        if processed < 6.013:
            processed = 6.014
        processed = f"{processed:.3f}"
        processed = processed.split('.')
        processed = f"{processed[0]}{processed[1]}"
        if processed.startswith('1'):
            processed = processed[1:]
        self.etree = parse_etree(f"{self.root_dir if self.root_dir else ''}/Dictionary/{processed}_ASIObjectDictionary.xml")
        self.dictionary_file = f"{self.root_dir if self.root_dir else ''}/Dictionary/{processed}_ASIObjectDictionary.xml"
        if self.heavy_duty:
            self.set_object_dictionary(f"{self.root_dir if self.root_dir else ''}"
                                       f"/Dictionary/{processed}_ASIObjectDictionary.xml")

        # Loading appropriate run_parameters
        # Old access codes for <6.021
        try:
            if self.firmware < 6.021:
                self.run_params_file = f"{self.root_dir if self.root_dir else ''}" \
                                       f"/Parameter Files/Run parameters for ASI controller 6019.csv"
                if not self.heavy_duty:
                    self.load_run_params(self.run_params_file)
                self.level_0 = 0
                self.level_1 = 15350
                self.level_2 = 19366
                self.level_3 = 27021
                self.level_4 = 31920

            # 6.021 access codes
            # 2022/07/06 T.Wu
            else:
                if self.firmware >= 6.023:
                    self.run_params_file = f"{self.root_dir if self.root_dir else ''}" \
                                           f"/Parameter Files/Run parameters for ASI controller 6023.csv"
                else:
                    self.run_params_file = f"{self.root_dir if self.root_dir else ''}" \
                                           f"/Parameter Files/Run parameters for ASI controller 6021.csv"
                if not self.heavy_duty:
                    self.load_run_params(self.run_params_file)
                self.level_0 = [0, 0, 0]
                self.level_1 = [0x3BF6, 0, 0]
                self.level_2 = [0xC2B5, 0x9FE5, 0x91A2]
                self.level_3 = [0x1114, 0x8FFC, 0x8250]
                self.level_4 = [0xD58B, 0xB3D0, 0x79C5]
        except TypeError:
            return

    def _com_prep(self, secondary):
        if self.can:
            if secondary is None:
                if not self.can_bus.disconnected:
                    self.can_bus.controller_parameter(self.run_parameters)
                    if self.firmware > 6.019:
                        self.load_PDO()
                    else:
                        self.load_PDO("Parameter Files/Run parameters for ASI controller PDO 6019.csv")
                    self.can_bus.PDO_parameters[0] = self.pdo_parameters
                    self.can_bus.build_pdo()
                else:
                    return
            else:
                self.can_bus.controller_parameter(self.run_parameters, 1)
                if self.firmware > 6.019:
                    self.load_PDO()
                else:
                    self.load_PDO("Parameter Files/Run parameters for ASI controller PDO 6019.csv")
                self.can_bus.PDO_parameters[1] = self.pdo_parameters
                self.can_bus.build_pdo(index=1)
            self.pdo_log = []
            with open(f'{self.root_dir}/Parameters to log/controller_can.csv') as f:
                for line in f.readlines():
                    self.pdo_log.append(line.strip())
        elif self.is_j1939:
            self.j1939_device.controller_parameter(self.run_parameters, self.com_id)
        else:
            self.modbus.controller_parameter(self.run_parameters)

    def _get_access_level(self):
        self.access_level = self.read("user access level")

    # Implementation for DynoBrake:
    ######################################################################################
    # Methods
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

    def start(self, mode=1):
        print(f"ASI Brake starting")
        self.write("Control command source", 0)
        self.write("Speed regulator mode", mode)  # torque for now
        self.write("Regeneration battery current limit", 100)
        self.write("Remote speed command", 0)
        self.write("Remote Speed Command in RPM", 0)
        self.write("Remote maximum motoring current", 0)
        self.write("Remote maximum braking current", 100)
        self.write("Remote torque command", 0)
        self.cur_torque = 0
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
        if self.poll_enabled:
            self.stop_polling()

    def set_direction(self):
        if self.get_rpm() > 0:
            self.brk_dir = 0
        else:
            self.brk_dir = 1

    # Implementation for DynoPoller:
    ######################################################################################
    # Properties
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

                param = Parameter(name, address, scale, unit)
                self._log_params[name] = param

    def poll(self):
        while self.poll_enabled:
            if self.can:
                if self.can_bus.listening:
                    self.connected = True
                else:
                    self.connected = False
                    break
                for param in self._log_params:
                    # if param in self.pdo_log:
                    #     self.log_params[param].Value = self.run_parameters[param].Value
                    # else:
                    self.log_params[param].Value = self.read(param)
                    sleep(self._poll_interval / len(self.log_params) * 0.9)
                # sleep(self._poll_interval)
                # sleep(self._poll_interval * 0.3)
            else:
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
                # T.Wu 2023-04-18 Haven't been used ever
                # faults = self.check_faults()
                # output = [datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f'), faults]
                # with self._errorfile.open(mode='a', newline='') as csvfile:
                #     csv.writer(csvfile).writerow(output)

                sleep(self._poll_interval * 0.6)

    # Methods
    def start_polling(self, pollInterval=1):
        for p in self._log_params:
            logging.debug(self._log_params[p].Name)
        # makedirs(self._errordir, exist_ok=True)
        # self._errorfile = self._errordir / (datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + ".csv")
        #
        # with open(file=self._errorfile, mode="w", newline="") as csvfile:
        #     csv.writer(csvfile).writerow(["Time", "Total Faults", "Total Warnings", "Total Checksums", "Faults"])

        self.polling_thread = Thread(target=self.poll)
        self.polling_thread.daemon = True
        self.poll_interval = pollInterval
        self.poll_enabled = True
        self.polling_thread.start()

    def stop_polling(self):
        if self.poll_enabled:
            self.poll_enabled = False
            self.polling_thread = None

    # Loads parameter data using a csv file of parameter names
    # and an xml element tree object created using an object dictionary eg. "ASIObjectDictionary.xml"
    def load_run_params(self, names):
        self.run_parameters = load_using_param_names(self.etree, names)
        if hasattr(self, '_log_params'):
            for param in self._log_params:
                try:
                    self.run_parameters[self._log_params[param].Name]
                except (KeyError, IndexError):
                    self.run_parameters[self._log_params[param].Name] = self._log_params[param]

    def load_PDO(self, file="Parameter Files/Run parameters for ASI controller PDO 6021.csv"):
        self.pdo_parameters = load_using_param_names(self.etree, f"{self.root_dir if self.root_dir else ''}/{file}")

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
        if not self.remote_faults_handle("Remote Speed Mode"):
            return
        rated_rpm = self.read('Rated motor speed')
        if self.firmware < 6.019:
            print(f'{datetime.now()} - Remote Speed mode | '
                  f"RPM - {kwargs['speed'] if 'speed' in kwargs.keys() else ''} | "
                  f"Speed Command - "
                  f"{kwargs['speed'] / rated_rpm * 100 if 'speed_command' not in kwargs.keys() else kwargs['speed_command']:.2f}% | "
                  f"Motoring - {kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100}% | "
                  f"Braking - {kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 0}%")
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
            print(f'{datetime.now()} - Remote Speed mode | '
                  f"RPM - {kwargs['speed'] if 'speed' in kwargs.keys() else ''} | "
                  f"Speed Command - "
                  f"{kwargs['speed'] / rated_rpm * 100 if 'speed_command' not in kwargs.keys() else kwargs['speed_command']:.2f}% | "
                  f"Motoring - {kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100}% | "
                  f"Braking - {kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 0}%")
            # if kwargs['speed'] == 0:
            #     kwargs['speed_command'] = 0
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

    remote_mode['speed'] = remote_speed_mode

    def remote_speed_ramp(self, duration=10, **kwargs):
        """
        Ramp speed in Remote speed mode in 10 total_steps

        Parameters:
            duration : float, required. Duration of the entire ramp
            kwargs : dict, required {
                speed : int, required. Remote Speed Command in RPM
                motoring_current : float, optional. Remote maximum motoring current, default to 100
                braking_current : float, optional. Remote maximum braking current, default to 100
                speed_command : float, optional. Remote speed command}
        """
        if duration <= 0:
            self.remote_speed_mode(**kwargs)
            return
        if not self.remote_faults_handle("Remote Speed Ramp"):
            return
        print(f'{datetime.now()} - Remote Speed mode - ramping | '
              f"Target RPM - {kwargs['speed']} | "
              f"Motoring - {kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100}% | "
              f"Braking - {kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 100}% | "
              f"Duration - {duration}s")
        self.remote_speed_mode(speed=0, motoring_current=0, speed_command=0)
        for i in range(10):
            self.write("Remote maximum braking current",
                       i / 10 * (kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100))
            self.write("Remote maximum motoring current",
                       i / 10 * (kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 100))
            self.write("Remote Speed Command in RPM",
                       i / 10 * kwargs['speed'])
            sleep(duration / 10)

    def remote_torque_mode(self, watchdog=None, **kwargs):
        """
        Remotely starts the motor in torque mode

        Parameters:
            watchdog : Thread, optional
            kwargs : dict, required {
                torque : float, required. Remote torque command
                motoring_current : float, optional. Remote maximum motoring current, default to 100
                braking_current : float, optional. Remote maximum braking current, default to 100}
        """
        if not self.remote_faults_handle("Remote Torque Mode"):
            return

        print(f'{datetime.now()} - Remote Torque mode | '
              f"Torque - {kwargs['torque']}\n")
        self.write("Control command source", 0)
        self.write("Speed regulator mode", 1)
        self.write("Remote torque command", kwargs['torque'])
        self.write("Remote maximum braking current",
                   kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 100)
        self.write("Remote maximum motoring current",
                   kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100)
        if watchdog is None:
            self.start_remote_motor()
        else:
            try:
                watchdog.start()
            except RuntimeError:
                pass

    remote_mode['torque'] = remote_torque_mode

    def remote_speed_torque_mode(self, watchdog=None, **kwargs):
        """
        Remotely starts the motor in torque mode

        Parameters:
            watchdog : Thread, optional
            kwargs : dict, required {
                speed : int, required. Remote Speed Command in RPM
                torque : float, required. Remote torque command
                motoring_current : float, required. Remote maximum motoring current, default to 100
                braking_current : float, optional. Remote maximum braking current, default to motoring_current}
        """
        if not self.remote_faults_handle("Remote Torque with Speed Limit Mode"):
            return

        print(f'{datetime.now()} - Remote Torque with Speed Limit mode | '
              f"RPM - {kwargs['speed']} | "
              f"Torque - {kwargs['torque']}% | "
              f"Motoring - {kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100}% | "
              f"Braking - {kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 100}%")
        self.write("Control command source", 0)
        self.write("Speed regulator mode", 2)
        self.write("Remote Speed Command in RPM", kwargs['speed'])
        self.write("Remote torque command", kwargs['torque'])
        self.write("Remote speed command", 0)

        self.write("Remote maximum braking current",
                   kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100)
        self.write("Remote maximum motoring current",
                   kwargs['braking_current'] if 'braking_current' in kwargs.keys() else 100)
        if watchdog is None:
            self.start_remote_motor()
        else:
            try:
                watchdog.start()
            except RuntimeError:
                pass

    remote_mode['speed_torque'] = remote_speed_torque_mode
    remote_mode['torque_speed'] = remote_speed_torque_mode

    def current_mode(self, watchdog=None, **kwargs):
        """
        Starts open loop current mode

        Parameters:
            watchdog : Thread, optional
            kwargs : dict, required {
                current : int, required. Open loop current
                frequency : int, required. Open loop frequency
                motoring_current : float, optional. Remote maximum motoring current, default to 100
                angle : float, optional. Open loop angle, default to 0}
        """
        if not self.remote_faults_handle("Remote Current Mode"):
            return

        print(f'{datetime.now()} - Remote Open Loop Current mode | '
              f"Current - {kwargs['current']}A | "
              f"Frequency - {kwargs['frequency']}Hz | "
              f"Motoring - {kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100}% | "
              f"Angle - {kwargs['angle'] if 'angle' in kwargs.keys() else 0}\u00B0")
        self.write("Test mode", 3)
        self.write("Remote maximum motoring current",
                   kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100)
        self.write("Open loop current", kwargs['current'])
        self.write("Open loop frequency", kwargs['frequency'])
        self.write("Open loop angle", kwargs['angle'] if 'angle' in kwargs.keys() else 0)
        if watchdog is None:
            self.start_remote_motor()
        else:
            try:
                watchdog.start()
            except RuntimeError:
                pass

    remote_mode['current'] = current_mode

    def voltage_mode(self, watchdog=None, **kwargs):
        """
        Starts open loop voltage mode

        Parameters:
            watchdog : Thread, optional
            kwargs : dict, required {
                modulation : int, required. Open loop modulation
                frequency : int, required. Open loop frequency
                motoring_current : float, optional. Remote maximum motoring current, default to 100
                angle : float, optional. Open loop angle, default to 0}
        """
        if not self.remote_faults_handle("Remote Voltage Mode"):
            return

        print(f'{datetime.now()} - Remote Open Loop Voltage mode | '
              f"Modulation - {kwargs['modulation']}pu | "
              f"Frequency - {kwargs['frequency']}Hz | "
              f"Motoring - {kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100}% | "
              f"Angle - {kwargs['angle'] if 'angle' in kwargs.keys() else 0}\u00B0")
        self.write("Test mode", 2)
        self.write("Remote maximum motoring current",
                   kwargs['motoring_current'] if 'motoring_current' in kwargs.keys() else 100)
        self.write("Open loop modulation", kwargs['modulation'])
        self.write("Open loop frequency", kwargs['frequency'])
        self.write("Open loop angle", kwargs['angle'] if 'angle' in kwargs.keys() else 0)
        if watchdog is None:
            self.start_remote_motor()
        else:
            try:
                watchdog.start()
            except RuntimeError:
                pass

    remote_mode['voltage'] = voltage_mode

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

    def open_loop_ramp(self,
                       mode=3,
                       step=5,
                       duration=10,
                       target=1,
                       motoring_current=100,
                       frequency=100,
                       angle=0,
                       **kwargs):
        if 'ramps' in kwargs.keys():
            duration = kwargs['ramps']
        rated_motor_current = self.read('Rated motor current')
        for i in range(step):
            if mode == 3 or mode == 'current':
                self.current_mode(motoring_current=motoring_current,
                                  current=rated_motor_current * target * (i + 1) / 5,
                                  frequency=frequency,
                                  angle=angle)
            elif mode == 2 or mode == 'voltage':
                self.voltage_mode(motoring_current=motoring_current,
                                  modulation=target * (i + 1) / 5,
                                  frequency=frequency,
                                  angle=angle)
            sleep(duration / step)

    def check_faults(self):
        """Checks controller for faults and warnings.
        Returns empty list [] if no faults/warnings detected.
        Returns list [] with detected faults/warnings in <fault name>-<fault description> format,
        i.e. faults-bit 11: Throttle voltage outside range (flash code 2,4)"""

        faults_found = []

        for name in self.faults_parameters:
            descriptions = self.faults_parameters[name]
            try:
                bit_string = self.log_params[name].Value
            except KeyError:
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
                        if (description.lower() not in ["reserved", "obsolete"] and
                            bit == '1'):
                            # eg. if the rated system voltage were too high and the controller triggered the proper fault, description would be:
                            #     "[parameter]-[bit  #]: [description]" ->
                            #     "faults-bit  0: Controller over voltage (flash code 1,1)"
                            faults_found.append(name + '-' + description)
                except IndexError:
                    pass

        return faults_found

    def remote_faults_handle(self, caller):
        any_faults = self.check_faults()
        if any_faults:
            print(f"Fault check: {caller} - {any_faults}")
            print("Attempting to clear faults...")
            self.clear_faults()
            sleep(1)
            uncleared_faults = self.check_faults()
            print(f"Uncleared faults: {caller} - {uncleared_faults}")
            if uncleared_faults:
                counter = 0
                for fault in uncleared_faults:
                    if "FLDBK" in fault or 'warning' in fault:
                        counter += 1
                if counter / len(uncleared_faults) < 1:
                    print(f"Call interrupted - {caller} - CANNOT CLEAR - {uncleared_faults}")
                    return False
                else:
                    print(f"Carry on - {caller} - Only foldbacks or warnings")
            return True
        return True

    def can_motor_move(self):
        parameters = (
            "Rated system voltage",
            "Rated motor current",
            "Rated motor speed",
            "# of motor pole pairs",
            "Gear ratio",
            "Rs",
            "Ls",
            "Hall offset",
            "Current regulator Kp",
            "Current regulator Ki",
            "Speed regulator Kp",
            "Speed regulator Ki"
        )

        # list comprehension

        for name in parameters:
            logging.info(f"Checking parameter: {name}")
            if self.read(name) == 0:
                print(f"FAIL - Parameter, '{name}' has not been set")
                self.can_move = False

        """
            0 = hall-based run,
            1 = hall start + sensorless run,
            2 = Sensorless run,
            If it's a sensorless run, stop here, we don't care about the hall sector values,
            KS, 3/18/2022
        """
        if self.read("Motor position sensor type") == 2:
            self.can_move = True
            return True

        # "Deck" each of the hall values used for motor discovery:
        # print("Checking hall values")
        values = (
            self.read("Hall sector[0]"),
            self.read("Hall sector[1]"),
            self.read("Hall sector[2]"),
            self.read("Hall sector[3]"),
            self.read("Hall sector[4]"),
            self.read("Hall sector[5]"),
            self.read("Hall sector[6]"),
            self.read("Hall sector[7]")
        )

        for v in (0, 1, 2, 3, 4, 5):
            if values[1:7].count(v) > 1:
                print(f"\n\nFAIL - bad halls, value '{str(v)}' is repeated more than once")
                self.can_move = False
                return False

        if (values[0] == -1 and values[7] == -1) is False:
            print("\n\nFAIL - bad halls, -1 is not repeated twice in [0] and [7]")
            self.can_move = False
            return False

        for i, v in enumerate(values[1:7]):
            # interval / chained comparison
            if (0 <= v <= 5) is False:
                self.can_move = False
                print("\n\nFAIL - bad hall value for position[" + str(
                    i) + "], hall sector value is not between 0<->5, value was:" + str(v))
                return False

        print("PASS - Motor is configured properly and hall values are good!")
        self.can_move = True
        return True

    def motor_discovery(self, mode=1, blocking=True, retrieve=True):
        def action():
            self.write("Motor discover mode", mode)
            logging.info(f"Motor discovery mode {mode} message sent")
            if mode == 0:
                self.motor_discovering = False
                return
            self.motor_discovering = True
            if retrieve:
                for _ in range(30):
                    if self.motor_discovering:
                        sleep(0.1)
                    else:
                        return
            if mode == 1:
                pass
            elif mode == 2:
                if retrieve:
                    for _ in range(120):
                        if self.motor_discovering:
                            sleep(0.1)
                        else:
                            return
            elif mode == 9:
                if retrieve:
                    for _ in range(120):
                        if self.motor_discovering:
                            sleep(0.1)
                        else:
                            return
            self.motor_discovering = False

        self.discovery_channel = Thread(target=action, daemon=True)
        self.discovery_channel.start()
        if blocking:
            self.discovery_channel.join()
            if retrieve:
                return self.retrieve_discovery(mode)

    def retrieve_discovery(self, mode):
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
        elif mode == 9:
            return (self.read("autotune Rs"),
                    self.read("autotune Ls"),
                    int(self.read("autotune rated rpm")),
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
        def action():
            logging.info('Interrupting Motor Discovery')
            self.write('Motor discover mode', 0)
            self.motor_discovering = False
            self.discovery_channel = None

        Thread(target=action, daemon=True).start()

    # Python3 of the EOL tester bridge check
    # Tom W Aug 2022
    def bridge_check(self):
        self.write("Open loop modulation", 0)
        self.write("Test mode", 2)
        openCct, turnOnHi, turnOnLo = [0, 0, 0], [0, 0, 0], [0, 0, 0]

        if len(self.check_faults()) == 0:
            self.start_remote_motor()
            sleep(0.1)

            openCircuitWindow = self.read("Open circuit voltage test window ")
            turnOnVoltageWindow = self.read("High/Lowside turn on voltage test window")
            turnOnHi[U] = self.read("motor phase U high voltage POST")
            turnOnLo[U] = self.read("motor phase U low voltage POST")
            turnOnHi[V] = self.read("motor phase V high voltage POST")
            turnOnLo[V] = self.read("motor phase V low voltage POST")
            turnOnHi[W] = self.read("motor phase W high voltage POST")
            turnOnLo[W] = self.read("motor phase W low voltage POST")
            openCct[U] = self.read("motor phase U open circuit voltage POST")
            openCct[V] = self.read("motor phase V open circuit voltage POST")
            openCct[W] = self.read("motor phase W open circuit voltage POST")
            phaseAoffset = self.read("phase A current sensor offset")
            phaseCoffset = self.read("phase C current sensor offset")

            oCctMin = .5 - openCircuitWindow
            oCctMax = .5 + openCircuitWindow
            tOVLoMin = .15 - turnOnVoltageWindow
            tOVLoMax = .15 + turnOnVoltageWindow
            tOVHiMin = .85 - turnOnVoltageWindow
            tOVHiMax = .85 + turnOnVoltageWindow

            isFail = False
            for i in range(3):

                if turnOnHi[i] < tOVHiMin:
                    print(f"Post Dynamic {PHASE[i]} Hi Voltage is too low: {turnOnHi[i]:.2f}")
                    isFail = True

                if turnOnHi[i] > tOVHiMax:
                    print(f"Post Dynamic {PHASE[i]} Hi Voltage is too high: {turnOnHi[i]:.2f}")
                    isFail = True

                if turnOnLo[i] < tOVLoMin:
                    print(f"Post Dynamic {PHASE[i]} Lo Voltage is too low: {turnOnLo[i]:.2f}")
                    isFail = True

                if turnOnLo[i] > tOVLoMax:
                    print(f"Post Dynamic {PHASE[i]} Lo Voltage is too high: {turnOnLo[i]:.2f}")
                    isFail = True

                if openCct[i] < oCctMin:
                    print(f"Post Static Open {PHASE[i]} Voltage is too low: {openCct[i]:.2f}")
                    isFail = True

                if openCct[i] > oCctMax:
                    print(f"Post Static Open {PHASE[i]} Voltage is too high: {openCct[i]:.2f}")
                    isFail = True

            currentMin = .45
            currentMax = .55
            if (phaseAoffset < currentMin or phaseAoffset > currentMax or
                    phaseCoffset < currentMin or phaseCoffset > currentMax):
                print(f"Phase Current A or C is out of Range ({currentMin:.2f} to {currentMax:.2f}) "
                      f"A {phaseAoffset:.2f} or C {phaseCoffset:.2f}")
                isFail = True

            if len(self.check_faults()) > 0:
                isFail = True

            self.stop_remote_motor()
            self.write("Test mode", 0)

            if isFail:
                return False, openCct, turnOnHi, turnOnLo
            else:
                return True, openCct, turnOnHi, turnOnLo
        else:
            self.start_remote_motor()
            sleep(0.1)

            turnOnHi[U] = self.read("motor phase U high voltage POST")
            turnOnLo[U] = self.read("motor phase U low voltage POST")
            turnOnHi[V] = self.read("motor phase V high voltage POST")
            turnOnLo[V] = self.read("motor phase V low voltage POST")
            turnOnHi[W] = self.read("motor phase W high voltage POST")
            turnOnLo[W] = self.read("motor phase W low voltage POST")
            openCct[U] = self.read("motor phase U open circuit voltage POST")
            openCct[V] = self.read("motor phase V open circuit voltage POST")
            openCct[W] = self.read("motor phase W open circuit voltage POST")

            self.stop_remote_motor()
            self.write("Test mode", 0)
            return False, openCct, turnOnHi, turnOnLo

    def in_foldback(self):
        faults = self.check_faults()

        for fault in faults:
            if "ContrlTempFLDBK" in fault or \
                    "MotorTempFLDBK" in fault or \
                    'foldback' in fault.lower():
                logging.warning(f"{self.port_name} - {fault}")
                return True

        return False

    def turn_off_communication_timeout(self):
        self.write("Command timeout threshold", 0)
        self.write("Average Command timeout threshold", 0)

    def get_phase_current(self):
        return (self.read("Ia_rms") + self.read("Ic_rms")) / 2

    def get_rpm(self):
        if self.poll_enabled:
            value = self.log_params['motor rpm'].Value
            if value:
                return value
        return self.read("motor rpm")

    def _get_access_code(self, level):
        if level == 0:
            return self.level_0
        elif level == 1:
            return self.level_1
        elif level == 2:
            return self.level_2
        elif level == 3:
            return self.level_3
        elif level == 4:
            return self.level_4

    def set_access_level(self, level):
        if self.firmware < 6.022:
            self.write("Parameter access code", self._get_access_code(level))
        else:
            code = self._get_access_code(level)
            if self.can:
                self.write("Parameter access code 1", code[0])
                self.write("Parameter access code 2", code[1])
                self.write("Parameter access code 3", code[2])
            else:
                self.write("Parameter access code 1", signed(code[0]))
                self.write("Parameter access code 2", signed(code[1]))
                self.write("Parameter access code 3", signed(code[2]))
        self.access_level = level

    def disable_read_write_locks(self):
        if self.read('Rated system voltage') == 0:
            previous_access_level = self.read("user access level")
            # firmware = self.read("software revision level")
            # print(firmware)

            w_lock1 = "write Access Code"
            w_lock2 = "Flash Parameter Write Access Code"
            r_plock1 = "Parameter read access code 1"
            r_plock2 = "Parameter read access code 2"
            r_plock3 = "Parameter read access code 3"
            r_flock1 = "Flash parameter read access code 1"
            r_flock2 = "Flash parameter read access code 2"
            r_flock3 = "Flash parameter read access code 3"
            r_lock1 = "Parameter read access code"
            r_lock2 = "Flash parameter read access code"

            self.set_access_level(3)

            if self.firmware <= 6.020:
                logging.info("older firmware unlock")
                self.write(w_lock1, self.read(w_lock2))
                self.write(r_lock1, self.read(r_lock2))

            # 6.021 parameters
            # TW, 07/05/2022
            else:
                self.write(r_plock1, self.read(r_flock1))
                self.write(r_plock2, self.read(r_flock2))
                self.write(r_plock3, self.read(r_flock3))

            self.set_access_level(previous_access_level)

    def power_cycle(self):
        # previous_access_level = self.read("user access level")
        # self.set_access_level(4)
        # self.write("MicroElectronics Test Register", 4096)

        # self.set_access_level(previous_access_level)
        if 6.021 <= self.firmware < 7:
            self.write(510, 0x5fff)
        else:
            print("Firmware does not support MCU reset")

    def start_remote_motor(self):
        if self.can_move:
            self.write("Remote state command", value=2)
        else:
            print("Controller missing crucial parameters to operate a motor")

    def stop_remote_motor(self):
        self.write("Remote state command", value=0)

    def idle_remote_motor(self):
        self.write("Remote state command", value=1)

    # Does the same thing as clicking "Reset" in BACDoor.
    def clear_faults(self):
        self.write("Fault clear", value=1)

    # ########## Functions that are helper initialization functions
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

        if self.firmware > 6.021:
            faults3_xpath = "//ParameterDescription[Name='faults3']//Description"
            self.faults_parameters['faults3'] = [description.text for description in tree.findall(faults3_xpath)][::-1]

    def get_foldback(self, foldback):
        """
        Get controller foldback value [1 - foldback gain]

        Parameters:
            foldback : str, required. Accepted values :
                positive battery limit |
                battery i^2t foldback gain |
                low voltage foldback gain |
                low state of charge foldback gain |
                negative battery limit |
                high voltage foldback gain |
                high state of charge foldback gain |
                motor temperature foldback gain |
                inverter temperature foldback gain |
                motoring phase current limit |
                regen phase current limit |
                combined motor foldback |
                Remote Motoring Foldback |
                Remote Regen Foldback
        """
        if foldback in ASI_FOLDBACKS:
            address = self.etree.find(f"//ParameterDescription[Name='{foldback}']")
            return 1 - self.read(address)
        else:
            print(f"Requested foldback: '{foldback}' not found in dictionary")

    def set_object_dictionary(self, object_dictionary="ASIObjectDictionary.xml"):
        logging.info("Instantiate Parameter Object Dictionary")
        root = ET.parse(object_dictionary).getroot()

        logging.info("Generating parameter object")
        for section in root.findall('Parameters'):
            for element in section.findall('ParameterDescription'):
                parameter = Parameter()
                parameter.set_using_xml_element(element)
                self.run_parameters[parameter.Name] = parameter

        logging.info("Populated " + str(len(self.run_parameters)) + " parameters")

    # ########### File Reading And Writing functions that interact with the controller ##########
    def load_firmware(self, firmware):
        """
        Returns: 0 on success, 1 on fail
        Expects full filename as input
        """
        self.write("Load firmware to flash", value=32767)
        self.modbus.modbus.serial.close()
        # self.subprocess = subprocess.Popen(f"C2ProgShell.exe -hex='{firmware}' -port='{self.port_name}'")
        self.subprocess = subprocess.Popen(["C2ProgShell.exe", f"-hex={firmware}", f"-port={self.port_name}"])
        (output, err) = self.subprocess.communicate()
        logging.debug(output)
        logging.debug(err)
        exit_code = self.subprocess.wait()
        self.modbus.modbus.serial.open()
        return exit_code

    # Took this SaveToFlash function from common.py on EOLTester and modified it.
    # Kent, 11-3-2021
    # This function has problems, try not to use it.
    # TW 2022-07-13 Problem seems fixed with 3 sec wait time
    def save_to_flash(self, save_code=0x7FFF):
        if save_code == 0x7FFF:
            print("Saving parameters to flash")
        elif save_code == 0x3FFF:
            print("Saving parameters to OTP")
        else:
            print("Bad flash request")
            return False

        retries = 6
        result = False
        count = 0
        # reply = 0
        while (count < retries and
               result != 4096.0):  # 4096 = 0x1000 in hex
            self.write("Write parameters to flash", save_code)
            sleep(3)

            result = self.read("Write parameters to flash")
            print("Result: " + str(result), end="\r")

            count = count + 1
            sleep(0.5)
        print("")
        # if (result != 4096):
        #     raise ("SaveToFlash Save Error")  # RetryException("SaveToFlash Save Error")
        #     return False
        return True

    def otp_serial(self):
        template = "OTP_"
        for i in range(8):
            if self.firmware < 6.023:
                name = f"OTP serial number{i}"
            else:
                name = f"otp serial number{i}"
            template += f"{int(self.read(name)):04X}-"
        return template[:-1]

    def hardware(self):
        if self.is_barcode_empty("hardware"):
            return f"10-{int(self.read('Product Part Number')):06d}"
        else:
            return self.barcode["hardware"]

    def revision(self):
        if self.is_barcode_empty("revision"):
            char = "XABCDEFGHIJKLMNOPQRSTUVWYZ"
            raw = f"{int(self.read('Part Number Revision')):05d}"
            letter = char[int(raw[1])]
            return f"{letter}-{raw[3:]}"
        else:
            return self.barcode["revision"]

    def parameter(self):
        if self.is_barcode_empty("parameter"):
            return f"92-{int(self.read('MFG Customer Parameter File')):06d}"
        else:
            return self.barcode["parameter"]

    def firmware_code(self):
        if self.is_barcode_empty("firmware"):
            return f"90-{int(self.read('MFG Firmware File')):06d}"
        else:
            return self.barcode["firmware"]

    def serial_number(self):
        try:
            if self.is_barcode_empty("serial_num"):
                return f"{int(self.read('MFG PCBA Serial Number 1')):04d}-" \
                       f"{int(self.read('MFG PCBA Serial Number 2')):05d}"
            else:
                return self.barcode["serial_num"]
        except TypeError:
            return '0000-00000'

    def part_number(self):
        if self.is_barcode_empty("part_num"):
            return f"{int(self.read('SMT Serial Number'))}"
        else:
            return self.barcode["part_num"]

    def barcode_scanned(self, barcode=None):
        if barcode is None:
            barcode = simpledialog.askstring("Barcode empty!", "Please try again!").split("~")
        else:
            barcode = barcode.split("~")
        # Retry shouldn't be necessary from DynoController
        # retry = 0
        # while len(barcode) != 8:
        #     print(f"Barcode has invalid length! Retrying...")
        #     barcode = input("Please scan barcode: ").split("~")
        #     retry += 1
        #     if retry > self.checksum_retry:
        #         print("Barcode read failed too many times...")
        #         return False
        if len(barcode) == 8:
            self.barcode = {"label_id": barcode[0],
                            "mfg_code": barcode[1],
                            "part_num": barcode[2],
                            "hardware": barcode[3],
                            "revision": barcode[4],
                            "firmware": barcode[5],
                            "parameter": barcode[6],
                            "serial_num": barcode[7],
                            "part#": None}
        elif len(barcode) == 9:
            self.barcode = {"label_id": barcode[0],
                            "mfg_code": barcode[1],
                            "part_num": barcode[2],
                            "hardware": barcode[3],
                            "revision": barcode[4],
                            "firmware": barcode[5],
                            "parameter": barcode[6],
                            "serial_num": barcode[7],
                            "part#": barcode[8]}
        elif len(barcode) == 6:
            self.barcode = {"label_id": barcode[0],
                            "mfg_code": barcode[1],
                            "part_num": barcode[2],
                            "hardware": barcode[3],
                            "revision": barcode[4],
                            "firmware": None,
                            "parameter": None,
                            "serial_num": barcode[7],
                            "part#": None}

    def is_barcode_empty(self, element=""):
        try:
            if element == "":
                for name in ["label_id",
                             "mfg_code",
                             "part_num",
                             "hardware",
                             "revision",
                             "serial_num"]:
                    if self.barcode[name] is None:
                        return True
            elif element in self.barcode:
                if self.barcode[element] is None:
                    return True
            else:
                print("Request not part of barcode")
        except AttributeError:
            return False

    def backup_parameters(self, XMLFile, all_param: bool=True, master=None):
        print(f"Backing up {'all ' if all_param else ''}parameters to {XMLFile}")
        root = ET.Element("ArrayOfSerializableParameter")
        # self.stop_polling()
        # with open(XMLFile, "w") as f:
            # f.write(f'<?xml version="1.0" encoding="utf-8"?>\n')
            # f.write(f'<!--File Created: {datetime.now()}-->')
            # ControllerParameters = self.run_parameters
        if all_param:
            if master is not None:
                total = len(self.etree.findall('//ParameterDescription'))
                popup = Toplevel(master, background='#ccccff')
                pb = Progressbar(popup, orient='horizontal', mode='determinate', length=300)
                pb.grid(column=0, row=0, columnspan=2, padx=10, pady=20)
            # for section in self.etree.findall('Parameters'):
            start = 0
            length = 0
            params_2_read = []
            for i, element in enumerate(self.etree.findall('/Parameters/ParameterDescription')):
                parameter = Parameter()
                parameter.set_using_xml_element(element)
                if self.can:
                    if parameter.Write == 'true' and parameter.Flash == 'true':
                        serialParameter = ET.SubElement(root, "SerializableParameter")
                        # ET.SubElement(serialParameter, "Key").text = str(parameter.Key)
                        ET.SubElement(serialParameter, "Address").text = str(parameter.Address)
                        value = self.read(int(parameter.Address))
                        if value is None:
                            print("Save to file failed over CAN. Please try again.")
                            if master is not None:
                                pb.stop()
                                popup.destroy()
                            return
                        if value > 0x7fff:
                            value -= 65536
                        ET.SubElement(serialParameter, "Value").text = f'{int(value) if value else 0}'
                        comment = ET.Comment(f'{element.find("Name").text} - {value}')
                        serialParameter.insert(0, comment)
                    if master is not None:
                        pb['value'] = i / total * 100
                else:
                    if parameter.Write == 'true' and parameter.Flash == 'true':
                        length += 1
                        params_2_read.append(parameter)
                        if length == 125:
                            # print(int(params_2_read[0].Address), length)
                            with self.io_lock:
                                values = self.modbus.mass_read(int(params_2_read[0].Address), length)
                                while not values:
                                    values = self.modbus.mass_read(int(params_2_read[0].Address), length)
                            for l in range(length):
                                serialParameter = ET.SubElement(root, "SerializableParameter")
                                ET.SubElement(serialParameter, "Address").text = params_2_read[l].Address
                                value = values[l] - 65536 if values[l] > 0x7fff else values[l]
                                ET.SubElement(serialParameter, "Value").text = f"{value}"
                                comment = ET.Comment(f'{params_2_read[l].Name} - {value}')
                                serialParameter.insert(0, comment)
                            start = start + length
                            length = 0
                            params_2_read = []
                            if master is not None:
                                pb['value'] = i / total * 100
                    else:
                        if length > 0:
                            # print(int(params_2_read[0].Address), length)
                            with self.io_lock:
                                values = self.modbus.mass_read(int(params_2_read[0].Address), length)
                                while not values:
                                    values = self.modbus.mass_read(int(params_2_read[0].Address), length)

                            for l in range(length):
                                serialParameter = ET.SubElement(root, "SerializableParameter")
                                ET.SubElement(serialParameter, "Address").text = params_2_read[l].Address
                                value = values[l] - 65536 if values[l] > 0x7fff else values[l]
                                ET.SubElement(serialParameter, "Value").text = f"{value}"
                                comment = ET.Comment(f'{params_2_read[l].Name} - {value}')
                                serialParameter.insert(0, comment)
                            start = start + length
                            length = 0
                            params_2_read = []
                            if master is not None:
                                pb['value'] = i / total * 100
                        start += 1

            if length > 0:
                # print(int(params_2_read[0].Address), length)
                with self.io_lock:
                    values = self.modbus.mass_read(int(params_2_read[0].Address), length)
                    while not values:
                        values = self.modbus.mass_read(int(params_2_read[0].Address), length)

                for l in range(length):
                    serialParameter = ET.SubElement(root, "SerializableParameter")
                    ET.SubElement(serialParameter, "Address").text = params_2_read[l].Address
                    value = values[l] - 65536 if values[l] > 0x7fff else values[l]
                    ET.SubElement(serialParameter, "Value").text = f"{value}"
                    comment = ET.Comment(f'{params_2_read[l].Name} - {value}')
                    serialParameter.insert(0, comment)

        else:
            if master is not None:
                total = len(self.run_parameters)
                popup = Toplevel(master, background='white')
                pb = Progressbar(popup, orient='horizontal', mode='determinate', length=300)
                pb.grid(column=0, row=0, columnspan=2, padx=10, pady=20)
            for i, parameter in enumerate(self.run_parameters):
                # ControllerParameters[parameter].value = self.read(parameter)
                if self.run_parameters[parameter].Flash == "true":
                    serialParameter = ET.SubElement(root, "SerializableParameter")
                    # ET.SubElement(serialParameter, "Key").text = str(self.run_parameters[parameter].Key)
                    ET.SubElement(serialParameter, "Address").text = str(self.run_parameters[parameter].Address)
                    ET.SubElement(serialParameter, "Value").text = str(int(self.read(parameter) *
                                                                           get_scale_value(self.run_parameters[parameter].Scale)))
                    comment = ET.Comment(f'{parameter}')
                    serialParameter.insert(0, comment)
                    if master is not None:
                        pb['value'] = i / total * 100
        if master is not None:
            pb.stop()
            popup.destroy()
        indent(root)
        tree = ET.ElementTree(root)
        # tree.write(XMLFile)
        tree.write(XMLFile, xml_declaration=True, encoding="utf-8")
        print(f"Backup Parameters Complete!")
        # self.start_polling()

    def load_parameters(self, file, master=None):
        print(f"Loading Parameter file: {file}")
        ps = ET.parse(file).getroot().findall('SerializableParameter')
        if master is not None:
            total = len(ps)
            popup = Toplevel(master, background='white')
            pb = Progressbar(popup, orient='horizontal', mode='determinate', length=300)
            pb.grid(column=0, row=0, columnspan=2, padx=10, pady=20)
        for i, p in enumerate(ps):
            address = int(p.find('Address').text)
            value = int(p.find('Value').text)
            try:
                request_access_lvl = int(p.find('AccessLevel').text)
                if request_access_lvl > 0:
                    self.set_access_level(request_access_lvl)
            except AttributeError:
                request_access_lvl = 0
            if self.can:
                self.write(address, value)
            else:
                self.write(address, value)
            if request_access_lvl > 0:
                self.set_access_level(0)
            logging.debug(f"[{i + 1}/{len(ps)}] Updating address {address} with value {value}")
            if master is not None:
                pb['value'] = i / total * 100
        print(f"\nParameters loaded!")
        if master is not None:
            popup.destroy()

    def add_run_parameter(self, param):
        if isinstance(param, str):
            name = param
        elif isinstance(param, int):
            element = self.etree.find(f"//ParameterDescription[Address='{param}']")
            p = Parameter()
            p.set_using_xml_element(element)
            name = p.Name
        elif isinstance(param, Parameter):
            name = param.Name
        else:
            return False

        try:
            self.run_parameters[name]
        except KeyError:
            with open(self.run_params_file, mode="a", newline="") as csvRun:
                csv.writer(csvRun).writerow([name])
            self.load_run_params(self.run_params_file)
        else:
            logging.debug(f"{name} already in Run Parameters")
        finally:
            if self.can:
                self.can_bus.controller_parameter(self.run_parameters)
            else:
                self.modbus.controller_parameter(self.run_parameters)
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

    # ######### Basic calls to minimalmodbus that all communications are built on #################
    def write(self, name, value, log=False):
        with self.io_lock:  # only 1 program or script should read or write to the controller at any time.
            if self.is_j1939:
                try:
                    self.j1939_device.write(name, [value], self.com_id, 1)
                except J1939TimeoutError:
                    print("J1939 TIMEOUT ERROR")
                    self.j1939_device.__del__()
                    self.connected = False
                    return
                self.run_parameters[name].Value = value
                self.j1939_device.controller_parameter(self.run_parameters, self.com_id)
            elif self.can:
                # self.can_bus.controller_parameter(self.run_parameters)
                if hasattr(self, 'secondary') and self.secondary:
                    self.can_bus.controller_parameter(self.run_parameters, 1)
                    try:
                        if self.can_bus.write(name, value, index=1):
                            if isinstance(name, str):
                                self.run_parameters[name].Value = value
                                self.controller_parameter()
                    except NotInRunParameterError:
                        self.add_run_parameter(name)
                        self.can_bus.controller_parameter(self.run_parameters, 1)
                        if self.can_bus.write(name, value, index=1):
                            if isinstance(name, str):
                                self.run_parameters[name].Value = value
                                self.controller_parameter()
                else:
                    self.can_bus.controller_parameter(self.run_parameters)
                    try:
                        if self.can_bus.write(name, value):
                            if isinstance(name, str):
                                self.run_parameters[name].Value = value
                                self.controller_parameter()
                    except NotInRunParameterError:
                        self.add_run_parameter(name)
                        self.can_bus.controller_parameter(self.run_parameters)
                        if self.can_bus.write(name, value):
                            if isinstance(name, str):
                                self.run_parameters[name].Value = value
                                self.controller_parameter()
                if self.can_bus.disconnected:
                    self.connected = False
            else:
                self.modbus.controller_parameter(self.run_parameters)
                try:
                    if self.modbus.write(name, value):
                        if isinstance(name, str):
                            self.run_parameters[name].Value = value
                            self.controller_parameter()
                except NotInRunParameterError:
                    self.add_run_parameter(name)
                    self.modbus.controller_parameter(self.run_parameters)
                    if self.modbus.write(name, value):
                        if isinstance(name, str):
                            self.run_parameters[name].Value = value
                            self.controller_parameter()

    def read(self, name):
        with self.io_lock:  # only 1 program or script should read or write from an asi controller at any time.
            if self.is_j1939:
                self.j1939_device.controller_parameter(self.run_parameters, self.com_id)
                try:
                    response = self.j1939_device.read(name, self.com_id, 1)[0]
                except J1939TimeoutError:
                    print("J1939 TIMEOUT ERROR")
                    self.j1939_device.__del__()
                    self.connected = False
                    return
            elif self.can:
                try:
                    if hasattr(self, 'secondary') and self.secondary:
                        self.can_bus.controller_parameter(self.run_parameters, 1)
                        response = self.can_bus.read(name, index=1)
                    else:
                        self.can_bus.controller_parameter(self.run_parameters)
                        response = self.can_bus.read(name)
                except (NotInPDOParameterError, CommLossError):
                    self.connected = False
                    return
            else:
                self.modbus.controller_parameter(self.run_parameters)
                try:
                    response = self.modbus.read(name)
                except NotInRunParameterError:
                    logging.warning(f"{name} not in run parameters")
                    self.add_run_parameter(name)
                    response = self.modbus.read(name)
                except CommLossError:
                    self.connected = False
                    raise CommLossError

            if isinstance(response, float) or isinstance(response, int):
                if isinstance(name, str):
                    self.run_parameters[name].Value = response
                    self.controller_parameter()
                return response
            else:
                return self.run_parameters[name].Value

    def controller_parameter(self, params=None):
        if self.can:
            if hasattr(self, 'secondary') and self.secondary:
                self.run_parameters = self.can_bus.run_parameters[1]
            else:
                self.run_parameters = self.can_bus.run_parameters[0]
        elif self.is_j1939:
            self.run_parameters = self.j1939_device.run_parameters[self.com_id]
        else:
            self.run_parameters = self.modbus.run_parameters

    def can_pdo_handle(self, msg: can.Message, index=0) -> bool:
        rt, idx = self.can_bus.is_PDO(msg, index)
        if idx:
            if rt == 'T':
                tpdo = self.can_bus.TPDO[index][idx]
                for i, idx in enumerate(tpdo.idx_map):
                    if i < tpdo.size:
                        try:
                            self.log_params[idx].Value = (signed(msg.data[i * 2 + 1] * 0x100 + msg.data[i * 2])
                                                          / get_scale_value(self.run_parameters[idx].Scale))
                        except KeyError:
                            pass
                return True
        return False

    def can_pdo_handle_del(self, msg: can.Message, index=0) -> bool:
        rt, idx = self.can_bus.is_PDO(msg, index)
        if idx:
            if rt == 'T':
                return True
        return False



if __name__ == '__main__':
    dut = ASIController("COM3", 115200, 1)

    # dut.remote_speed_mode(torque=25, speed=80, clear_faults=True)
    # dut.remote_speed_mode(torque=50, speed=80, clear_faults=True)

    # dut.load_parameters("Remote Mode.xml")
    dut.turn_off_communication_timeout()

    # dut.load_firmware("90-000306 BAC_Application_28035_6020.ehx")
    # dut.remote_torque_mode(torque=35)
    # dut.remote_speed_mode(motoring_current=25, speed=10)
    print(dut.bridge_check())

    # try:
    #     dut.start_polling(1)
    #     sleep(5)
    #     dut.stop_polling()
    #
    # except KeyboardInterrupt as k_e:
    #     print(k_e)
    #     dut.stop_polling()
    #
    # print("Polling and Logging those parameters")
    # input()
