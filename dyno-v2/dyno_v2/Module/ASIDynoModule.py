# ASI Includes
from dyno_v2.Module.DynoABCs import DynoPoller, DynoBrake
from dyno_v2.Module.yokogawa_WT1806 import Yokogawa_WT1806
from dyno_v2.Module.asi_controller import *
from dyno_v2.Module.abb_acs800 import *
from dyno_v2.Module.exceptions import *
from dyno_v2.Module.dyno_parameters import *
from dyno_v2.Module.email_alerts import *

# needed
import logging
from tkinter import messagebox
from os import makedirs
from pathlib import Path
import csv
from time import sleep
from datetime import datetime, timedelta
import pandas as pd
import matplotlib
from matplotlib.tri import Triangulation, TriAnalyzer, \
    UniformTriRefiner, LinearTriInterpolator, CubicTriInterpolator
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
# plt.switch_backend('agg')
import numpy as np
from threading import Thread, Event
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from simple_pid import PID

PA = 'PA'


class ASIDynoModule:
    def __init__(
            self,
            dut="COM10",
            yoko="192.168.1.79",
            brake="COM9",
            config=None,
            root=ROOT_DIR,
            SSTime=10,
            TestTime=45,
            SSTol=0.01,
            tPID=0.5,
            log_folder="C:/DynoResults/",
            enable_email=False,
            enable_int_email=False
    ):
        # operating parameters
        self.TestTime = TestTime  # minutes til test is terminated
        self.curTorque = 0  # % brake torque

        self.root_dir = f"{root}"
        self.configs = config_reader()

        self.devices = {1: None,
                        2: None,
                        PA: None}
        self.dyno_connect(dut, brake, yoko, config)
        print("DynoModule Initialized!")

        self.faults_backup = {
            1: self.devices[1].faults_parameters.copy() if isinstance(self.devices[1], ASIController) else None,
            2: self.devices[2].faults_parameters.copy() if isinstance(self.devices[2], ASIController) else None
        }

        self.config_parameters = {}
        self.load_config()
        # create new timestamped logfile directory
        self.update_log_dir(log_folder)
        self._logfile = self._logdir / "placeholder"  # this file is placeholder; should never be created
        self.extra_files = {}
        self.extra_barcodes = {}
        self._logInterval = 10
        self._logEnabled = False
        self._worker = None
        self.start_time = None
        self.max_log_lines = 172800  # ~48 hours
        self.pid_parameters = {
            'target': 0,
            'kp': 0,
            'ki': 0,
            'kd': 0,
            'monitor': 'motor speed',
            'limits': (0, 100),
            'interval': tPID,
            'start': 0,
            'ss': False,
            'ssTol': SSTol,
            'ssTime': SSTime
        }
        self.pid = None
        self.pid_thread = None
        self.pid_enabled = False
        self.cooldown_parameters = {'cooldown_type': None,
                                    'cooldown': 0,
                                    'cd_on_driver': False}
        self.driver = 1  # 1 - Device 1 | 2 - Device 2
        self.enable_email = enable_email
        self.enable_int_email = enable_int_email
        self.testing = False
        self.stopping = False
        self.status_thread = None
        self.updating = True
        self.update_limits()
        self.current_csv_line = [0] * len(self.update_csv_line(True))
        self.csv_thread = Thread(target=self.update_csv)
        self.test_outputs = {}
        self.watchdog_enabled = False
        self.watchdog = None
        self.watchdog_interval = 0.5
        self.int_event = Event()

        self._start_polling()
        self.start_status_thread()

    def __repr__(self):
        template = f"Device 1: {self.devices[1]}\n" \
                   f"Device 2: {self.devices[2]}\n" \
                   f"PA: {self.devices[PA]}"
        return template

    def dyno_connect(self, dut, brake, yoko, config):
        # init from config file
        if config is not None:
            self.config = self.configs.loc[config]
            try:
                if "CAN" in self.config["dut_port"]:
                    if "CAN" in str(self.config["brk_port"]):
                        self.devices[1] = ASIController(com_port="PCAN_USBBUS1",
                                                 baud_rate=self.config["dut_baud"],
                                                 mb_address=[int(self.config["dut_id"]),
                                                             int(self.config["brk_id"])],
                                                 is_can=True, root=self.root_dir)
                    else:
                        self.devices[1] = ASIController(com_port="PCAN_USBBUS1",
                                                 baud_rate=self.config["dut_baud"],
                                                 mb_address=self.config["dut_id"],
                                                 is_can=True, root=self.root_dir)
                elif "COM" in self.config["dut_port"]:
                    self.devices[1] = ASIController(com_port=self.config["dut_port"],
                                             baud_rate=self.config["dut_baud"],
                                             mb_address=self.config["dut_id"],
                                             root=self.root_dir)
                else:
                    self.devices[1] = None
            except ConnectionError:
                self.devices[1] = None

            try:
                if self.config["brk_controller"] == "ABB":
                    self.devices[2] = AbbAcs800(port=self.config["brk_port"],
                                         baud=self.config["brk_baud"],
                                         auto=True, root=self.root_dir)
                elif pd.isna(self.config["brk_controller"]):
                    self.devices[2] = None
                else:
                    if "CAN" in self.config["brk_port"]:
                        if 'CAN' in str(self.config['dut_port']):
                            self.devices[2] = ASIController(is_can=True, root=self.root_dir,
                                                     baud_rate=self.config["brk_baud"],
                                                     secondary=self.config["brk_id"],
                                                     can_bus=self.devices[1].can_bus)
                        else:
                            self.devices[2] = ASIController(com_port=self.config["brk_port"],
                                                     baud_rate=self.config["brk_baud"],
                                                     mb_address=self.config["brk_id"],
                                                     is_can=True, root=self.root_dir)
                    else:
                        self.devices[2] = ASIController(com_port=self.config["brk_port"],
                                                 baud_rate=self.config["brk_baud"],
                                                 mb_address=self.config["brk_id"],
                                                 root=self.root_dir)
            except ConnectionError:
                self.devices[2] = None

            try:
                if self.config["yoko_ip"] != 0:
                    self.devices[PA] = Yokogawa_WT1806(f"192.168.1.{self.config['yoko_ip']}",
                                              file=f"{self.root_dir}\\dyno_v2\\yoko_parameter_information.csv")
                else:
                    self.devices[PA] = None
            except ConnectionError:
                self.devices[PA] = None

        # Connect to instruments without config file,
        # Each instrument is either a string, a controller or a Yokogawa_WT1806.
        # We use isinstance() for checking if string, because we don't want to exclude any valid combinations

        # Init DUT
        else:
            if isinstance(dut, ASIController):
                self.devices[1] = dut
            elif dut is None:
                self.devices[1] = None
                print("Warning: Running without driver!")
            elif isinstance(dut, str):
                try:
                    if "COM" in dut:
                        self.devices[1] = ASIController(dut.upper(), 115200, 1,
                                                 "", root=self.root_dir)
                    elif "PCAN_USBBUS" in dut:
                        self.devices[1] = ASIController(dut.upper(), baud_rate=250000,
                                                 mb_address=42,
                                                 is_can=True, root=self.root_dir)
                    elif "default" in dut:
                        self.devices[1] = ASIController(dut, baud_rate=250000, mb_address=42,
                                                 is_can=True, root=self.root_dir)
                except ConnectionError:
                    print("Connection to device 1 failed!")
            else:
                raise TypeError(f"Invalid type for device 1, {type(dut)}")

            # Init Yokogawa
            if 'Yokogawa_WT1806' in str(type(yoko)):
                self.devices[PA] = yoko
            elif yoko is None:
                self.devices[PA] = None
                print("Warning: Running without Yokogawa!")
            elif isinstance(yoko, str):
                try:
                    self.devices[PA] = Yokogawa_WT1806(yoko,
                                              file=f"{self.root_dir}\\dyno_v2\\yoko_parameter_information.csv")
                except ConnectionError:
                    self.devices[PA] = None
                    print("Connection to Yokogawa failed!")
                    return
            else:
                raise TypeError("Invalid type for PA device, '", type(yoko), "' ")

            # Init Brake
            if (isinstance(brake, DynoBrake) or
                    brake is None):
                self.devices[2] = brake
            elif isinstance(brake, str):
                try:
                    self.devices[2] = ASIController(brake, 115200, 1,
                                             "", root=self.root_dir)
                except ConnectionError:
                    self.devices[2] = None
                    print('Connection to device 2 failed!')
            else:
                raise TypeError("Invalid type for device 2, '", type(brake), "' ")

        if self.devices[1] is None and self.devices[2] is None and self.devices[PA] is None:
            print("Warning: No devices connected!")

    def update_limits(self):
        if hasattr(self, 'config'):
            self.speed_limit_upper = float(self.config['upper_speed'])
            self.speed_limit_lower = float(self.config['lower_speed'])
            self.torque_limit = float(self.config['max_torque'])
        else:
            self.speed_limit_upper = int(self.configs.loc['default']['upper_speed'])
            self.speed_limit_lower = int(self.configs.loc['default']['lower_speed'])
            self.torque_limit = float(self.configs.loc['default']['max_torque'])

    def start_status_thread(self):
        self.start_time = datetime.now()
        self.status_thread = Thread(target=self.status_update)
        self.status_thread.start()

    def status_update(self):
        while self.updating:
            try:
                if self.devices[1]:
                    if self.devices[1].connected:
                    # Speed check
                        if self.devices[1].get_rpm() > self.speed_limit_upper:
                            logging.warning("Device 1 over Upper Speed Limit")
                            self.testing = False
                            self.stop_test()
                            if self.enable_email and self.enable_int_email:
                                over_speed_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")
                        elif self.devices[1].get_rpm() < self.speed_limit_lower:
                            logging.warning("Device 1 under Lower Speed Limit")
                            self.testing = False
                            self.stop_test()
                            if self.enable_email and self.enable_int_email:
                                over_speed_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")
                    else:
                        logging.info("Device 1 Connection lost")
                        raise CommLossError
            except (CommLossError, AttributeError, TypeError):
                self.devices[1].connected = False
                break

            if self.devices[2] and not self.devices[2].connected:
                logging.info("Device 2 Connection lost")
                raise CommLossError

            try:
                if self.devices[PA]:
                    if self.devices[PA].connected:
                    # Torque limit check
                        if self.devices[PA].getMeasurement('Torque') > self.torque_limit:
                            logging.warning("Torque out of range")
                            self.testing = False
                            self.stop_test()
                            if self.enable_email and self.enable_int_email:
                                over_torque_email(to=AUTHOR_EMAIL, attach=f"{ROOT_DIR}\\Logs\\std-9.log")
                    else:
                        logging.info("PA Device Connection lost")
                        raise CommLossError
            except (AttributeError, TypeError):
                pass

            if self.updating:
                sleep(1)

    def stop_status(self):
        self.updating = False
        self.status_thread = None

    def load_config(self):
        if hasattr(self, 'config'):
            for config in CONFIG_MAP:
                self.config_parameters[config] = self.config[config]
        else:
            for config in CONFIG_MAP:
                self.config_parameters[config] = None
            if self.devices[1]:
                self.config_parameters['dut_port'] = self.devices[1].port_name
                self.config_parameters['dut_baud'] = self.devices[1].baud_rate
                self.config_parameters['dut_id'] = self.devices[1].com_id
            if self.devices[2]:
                self.config_parameters['brk_port'] = self.devices[2].port_name if isinstance(self.devices[2], ASIController) else self.devices[2].port
                self.config_parameters['brk_baud'] = self.devices[2].baud_rate if isinstance(self.devices[2], ASIController) else self.devices[2].baud
                self.config_parameters['brk_id'] = self.devices[2].com_id
        self.update_limits()

    def _start_polling(self):
        # start instruments polling
        if isinstance(self.devices[PA], DynoPoller):
            self.devices[PA].start_polling(1)
        if isinstance(self.devices[1], DynoPoller):
            self.devices[1].start_polling(1)
        if isinstance(self.devices[2], DynoPoller):
            self.devices[2].start_polling(1)

        self.csv_thread.start()

    def _stop_polling(self):
        self.updating = False
        self.csv_thread = None

        if isinstance(self.devices[PA], DynoPoller):
            self.devices[PA].stop_polling()
            # self.devices[PA].close()
        if isinstance(self.devices[1], DynoPoller):
            self.devices[1].stop_polling()
        if isinstance(self.devices[2], DynoPoller):
            self.devices[2].stop_polling()

    def stop_polling(self):
        self._stop_polling()

    def update_log_interval(self, new_interval):
        try:
            float(new_interval)
        except (TypeError, ValueError):
            pass
        else:
            self._logInterval = float(new_interval)
            if isinstance(self.devices[PA], DynoPoller):
                self.devices[PA].poll_interval = float(new_interval)
                # self.devices[PA].close()
            if isinstance(self.devices[1], DynoPoller):
                self.devices[1].poll_interval = float(new_interval)
            if isinstance(self.devices[2], DynoPoller):
                self.devices[2].poll_interval = float(new_interval)
            logging.info(f"Logging Interval Updated to {self._logInterval}")

    def update_log_dir(self, log_folder):
        self.logpath = Path(log_folder)
        self._logdir = self.logpath / datetime.now().strftime('%Y-%m-%d-%H-%M')

    def logging_thread(self):
        counter = 0
        while self._logEnabled:
            if counter == self.max_log_lines:
                counter = 0
                self.plot_basic(f'Partial Result - {datetime.now().strftime("%Y-%m-%d-%H-%M")}')
                csv_name = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')} {self.devices[1].serial_number()}.csv"
                self._logfile = self._logdir / csv_name
                with open(file=self._logfile, mode='w', newline='') as csvfile:
                    csv.writer(csvfile).writerow(self.getcsvline(getnames=True))
            else:
                sleep(self._logInterval)
                with open(file=self._logfile, mode='a', newline='') as csvfile:
                    csv.writer(csvfile).writerow(self.getcsvline())
                counter += 1

    def start_logging(self, logtime=10, run_down=""):
        if not self.is_logging_enabled():
            # begin new timestamped logfile for new datarun
            self.start_time = datetime.now()
            self._logdir = self.logpath / (f"{run_down if run_down == '' else f'{run_down} '}"
                                           f"{self.start_time.strftime('%Y-%m-%d-%H-%M')}")
            makedirs(self._logdir, exist_ok=True)
            if hasattr(self.devices[1], 'barcode') and self.devices[1].serial_number():
                csv_name = f"{self.start_time.strftime('%Y-%m-%d-%H-%M-%S')} {self.devices[1].serial_number()}.csv"
            # elif self.devices[2] or self.devices[PA]:
            else:
                csv_name = f"{self.start_time.strftime('%Y-%m-%d-%H-%M-%S')}.csv"
            # else:
            #     logging.warning("ASIController not properly inititated")
            #     return False
            self._logfile = self._logdir / csv_name

            with open(file=self._logfile, mode='w', newline='') as csvfile:
                csv.writer(csvfile).writerow(self.getcsvline(getnames=True))

            # start logging thread on specified interval
            self._logInterval = logtime
            self._logEnabled = True
            self._worker = Thread(target=self.logging_thread)
            self._worker.daemon = True
            self._worker.start()
            return True
        return False

    def stop_logging(self):
        if self.is_logging_enabled():
            self._logEnabled = False

            # kill lower level threads first, then the higher level Logger thread
            # If we don't kill the logger first,
            # code will hang if you enter "CTRL-C" to stop the script, KS, 1/14/2022
            if self._worker:
                self._worker.join()

            # if self.devices[PA] is not None:
            #     self.devices[PA].close()

    def getcsvline(self, getnames=False):
        if getnames:
            return self.update_csv_line(getnames)
        else:
            return self.current_csv_line

    def appended_csvline(self, to_append, header=False):
        new_line = self.getcsvline(getnames=header).copy()
        if isinstance(to_append, list):
            new_line.extend(to_append)
        else:
            new_line.append(to_append)

        return new_line

    def update_csv(self):
        while self.updating:
            start = datetime.now()
            self.current_csv_line = self.update_csv_line()
            end = datetime.now()
            sleep(1 - (end - start).total_seconds() - 0.001)

    def update_csv_line(self, getnames=False):
        linelist = []

        if getnames:
            time_column = "Time"
            elapsed_column = "Elapsed"
        else:
            time_column = datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f')[:-4]
            try:
                elapsed_column = float(str((datetime.now() - self.start_time).total_seconds())[:-4])
            except (TypeError, ValueError):
                elapsed_column = 0

        linelist.extend([time_column, elapsed_column])

        if self.devices[PA] and isinstance(self.devices[PA], DynoPoller):
            linelist.extend(collectPvals(self.devices[PA].log_params, getnames))
        if self.devices[1] and isinstance(self.devices[1], DynoPoller):
            linelist.extend(collectPvals(self.devices[1].log_params, getnames, indicator="DUT"))
        if self.devices[2]:
            if isinstance(self.devices[2], ASIController):
                linelist.extend(collectPvals(self.devices[2].log_params, getnames, indicator="BRK"))
            elif isinstance(self.devices[2], AbbAcs800):
                if getnames:
                    linelist.append('ABB Torque')
                    linelist.append('ABB Speed')
                else:
                    linelist.append(self.devices[2].read('Torque'))
                    linelist.append(self.devices[2].read('Speed'))

        return linelist

    # Helper function to log into extra csv files with custom data under self.logpath
    # Independant from self._logEnabled and self._logInterval
    # Tom W Aug 2022
    def extra_logging(self, file_name="", header=None, same_folder=True):
        csv_name = f"{file_name.replace('.csv', '')}.csv"

        if csv_name in self.extra_files:
            pass
        else:
            idx = len(self.extra_barcodes)
            self.extra_files[csv_name] = idx
            try:
                self.extra_barcodes[idx] = self.devices[1].barcode
            except AttributeError:
                self.extra_barcodes[idx] = {"label_id": None,
                                            "mfg_code": None,
                                            "part_num": None,
                                            "hardware": None,
                                            "revision": None,
                                            "firmware": None,
                                            "parameter": None,
                                            "serial_num": None,
                                            "part#": None}

        if same_folder:
            datafile = f"{self.logdir}\\{csv_name}"
        else:
            datafile = f"{self.logpath}\\{csv_name}"
        try:
            with open(file=datafile, mode='x', newline='') as csvfile:
                if header is None:
                    csv.writer(csvfile).writerow(self.getcsvline(getnames=True))
                else:
                    csv.writer(csvfile).writerow(header)
        except FileExistsError as e:
            if header is None:
                print(e)  # Assuming overwrite to existing extra default files
                with open(file=datafile, mode='w', newline='') as csvfile:
                    csv.writer(csvfile).writerow(self.getcsvline(getnames=True))
            else:  # Assuming only appending to existing extra custom files
                logging.info("Attention: File already exists, only appending new lines! ")

    def extra_line(self, file_name="", custom=False, data=None, same_folder=True):
        csv_name = f"{file_name.replace('.csv', '')}.csv"
        if same_folder:
            datafile = self._logdir / csv_name
        else:
            datafile = self.logpath / csv_name
        retry = 0
        while retry < self.devices[1].checksum_retry:
            try:
                with open(file=datafile, mode='a', newline='') as csvfile:
                    if custom:
                        csv.writer(csvfile).writerow(data)
                    else:
                        csv.writer(csvfile).writerow(self.getcsvline())
            except PermissionError as p_e:
                print(f"Permission Error! Make sure file is closed!")
                messagebox.showinfo("Attention", "Press enter to re-log...")
                retry += 1
                if retry == self.devices[1].checksum_retry:
                    print(f"Logging to extra file: {csv_name} failed after {retry} retries!")
                    return
                continue
            break

    def summarize_extra_log(self, filename=''):
        summary_csv = f'{filename}{"" if filename.endswith(" ") else " "}summary.csv'
        for i, file_name in enumerate(list(self.extra_files)):
            data = pd.read_csv(f"{self.logdir}/{file_name}")
            row_count = len(data.index)
            row_content = [str(self.extra_barcodes[i]['parameter'])] * row_count
            data.insert(0, 'Parameter File', row_content)
            row_content = [str(self.extra_barcodes[i]['serial_num'])] * row_count
            data.insert(0, 'Serial Number', row_content)
            self.extra_logging(file_name=summary_csv, header=data.columns, same_folder=False)
            one_up = Path(self.logdir).parents[0]
            data.to_csv(f'{one_up / summary_csv}', mode='a', header=False, index=False)
            
    def start_pid(
            self,
            interval=1,
            brake=2,
            kp=0,
            ki=0,
            kd=0,
            monitor='motor speed',
            target=0,
            limits=(0, 100),
            start=0,
            custom=False
    ) -> None:
        """Starts PID thread

        Parameters:
            interval : float, optional. PID loop interval in seconds (default 1)
            brake : str, optional. Braking controller: 1 or 2 (default 2)
            kp : float, optional. Kp (default: 0)
            ki : float, optional. Ki (default: 0)
            kd : float, optional. Kd (default: 0)
            monitor : str, optional. Parameter name to monitor for PID setpoint (default: motor speed)
            target : float, optional. PID target to achieve for monitored parameter (default: 0)
            limits : set, optional. PID output limits (default: (0, 100))
            start : float, optioanl. PID starting value (default: 0)
        """
        if not self.pid_enabled:
            self.pid_parameters['interval'] = interval
            if brake == 1:
                self.driver = 2
            elif brake == 2:
                self.driver = 1
            # self.pid_parameters['brake'] = brake
            self.pid_parameters['kp'] = kp
            self.pid_parameters['ki'] = ki
            self.pid_parameters['kd'] = kd
            self.pid_parameters['monitor'] = monitor
            self.pid_parameters['target'] = target
            self.pid_parameters['limits'] = limits
            self.pid_parameters['start'] = start
            self.pid_parameters['custom'] = custom
            self.pid_parameters['custom_value'] = 0
            self.pid_thread = Thread(target=self.pid_mode)
            self.pid_enabled = True
            self.pid_thread.start()
        
    def stop_pid(self):
        if hasattr(self, 'pid_enabled') and self.pid_enabled:
            self.pid_enabled = False
            self.pid_thread = None
            self.pid = None
            print("PID stopped!")
            
    def pid_mode(self):
        self.pid = PID(Kp=self.pid_parameters['kp'],
                       Ki=self.pid_parameters['ki'],
                       Kd=self.pid_parameters['kd'],
                       setpoint=self.pid_parameters['target'],
                       sample_time=self.pid_parameters['interval'],
                       output_limits=self.pid_parameters['limits'])
        self.pid.set_auto_mode(False)
        self.pid.set_auto_mode(True, self.pid_parameters['start'])

        startTime = datetime.now()
        time_end = startTime + timedelta(minutes=self.TestTime)
        time_ss = startTime + timedelta(minutes=self.pid_parameters['ssTime'])

        monitored_parameter = self.pid_monitor_get()

        while (self.pid_enabled and
               datetime.now() < time_end and
               datetime.now() < time_ss):
            self.pid_update()
            prev = monitored_parameter
            if self.pid_parameters['custom']:
                monitored_parameter = self.pid_parameters['custom_value']
            else:
                monitored_parameter = self.pid_monitor_get()
            try:
                new_setpoint = self.pid(monitored_parameter)
            except TypeError:
                new_setpoint = self.pid(prev)
            if self.pid_parameters['ss']:
                if abs(self.curTorque - new_setpoint) > self.pid_parameters['ssTol']:
                    time_ss = datetime.now() + timedelta(minutes=self.pid_parameters['ssTime'])
            self.pid_set(new_setpoint)
            if self.pid_enabled:
                sleep(self.pid_parameters['interval'])

            if time_end != startTime + timedelta(minutes=float(self.TestTime)):
                time_end = startTime + timedelta(minutes=float(self.TestTime))

        self.pid_enabled = False

    def pid_update(self):
        if isinstance(self.pid, PID):
            if self.pid.Kd != self.pid_parameters['kd']:
                self.pid.Kd = self.pid_parameters['kd']
            if self.pid.Kp != self.pid_parameters['kp']:
                self.pid.Kp = self.pid_parameters['kp']
            if self.pid.Ki != self.pid_parameters['ki']:
                self.pid.Ki = self.pid_parameters['ki']
            if self.pid.sample_time != self.pid_parameters['interval']:
                self.pid.sample_time = self.pid_parameters['interval']
            if self.pid.setpoint != self.pid_parameters['target']:
                self.pid.setpoint = self.pid_parameters['target']
            if self.pid.output_limits != self.pid_parameters['limits']:
                self.pid.output_limits = self.pid_parameters['limits']

    def pid_set(self, setpoint=0):
        self.curTorque = setpoint
        if self.driver == 2 and self.devices[1]:
            self.devices[1].set_torque(setpoint)
        elif self.driver == 1 and self.devices[2]:
            self.devices[2].set_torque(setpoint)

    def pid_monitor_get(self):
        if self.pid_parameters['monitor'] in self.devices[PA].log_params.keys():
            return self.devices[PA].getMeasurement(self.pid_parameters['monitor'])
        if self.driver == 1 and self.devices[1]:
            return self.devices[1].read(self.pid_parameters['monitor'])
        elif self.driver == 2 and self.devices[2]:
            return self.devices[2].read(self.pid_parameters['monitor'])

    def _watchdog_thread(self):
        if self.devices[1]:
            self.devices[1].write(32, 4000 * (self.watchdog_interval + 0.05))  # Set comm loss threshold to 4X(+0.05) watchdog interval
            self.devices[1].write(49, 2000 * (self.watchdog_interval + 0.05))  # Set average comm loss threshold to +0.05 watchdog interval
        if isinstance(self.devices[2], ASIController):
            self.devices[2].write(32, 4000 * (self.watchdog_interval + 0.05))  # Set comm loss threshold to 4X(+0.05) watchdog interval
            self.devices[2].write(49, 2000 * (self.watchdog_interval + 0.05))  # Set average comm loss threshold to +0.05 watchdog interval
        while self.watchdog_enabled:
            if self.devices[1]:
                self.devices[1].write("Remote state command", 258)  # Toggle high bit off
            if isinstance(self.devices[2], ASIController):
                self.devices[2].write("Remote state command", 258)  # Toggle high bit off
            sleep(self.watchdog_interval / 2)
            if self.devices[1]:
                self.devices[1].write("Remote state command", 514)  # Toggle high bit on
            if isinstance(self.devices[2], ASIController):
                self.devices[2].write("Remote state command", 514)  # Toggle high bit on
            sleep(self.watchdog_interval / 2)
        if self.devices[1]:
            self.devices[1].turn_off_communication_timeout()
            self.devices[1].write("Remote state command", 0)
        if isinstance(self.devices[2], ASIController):
            self.devices[2].turn_off_communication_timeout()
            self.devices[2].write("Remote state command", 0)

    def init_watchdog(self):
        self.watchdog = Thread(target=self._watchdog_thread)
        return self.watchdog

    def start_watchdog(self, interval=0.5):
        if not self.watchdog:
            self.init_watchdog()
        self.watchdog_interval = interval
        self.watchdog_enabled = True
        try:
            self.watchdog.start()
        except RuntimeError:
            pass

    def stop_watchdog(self):
        self.watchdog_enabled = False
        self.watchdog = Thread(target=self._watchdog_thread)

    def backup_parameters(self, dut=None, brk=None, master=None):
        if isinstance(self.devices[1], ASIController):
            self.devices[1].backup_parameters(f"{self.logdir}/{dut if dut else 'Device 1'} parameters.xml",
                                              master=master)
        if isinstance(self.devices[2], ASIController):
            self.devices[2].backup_parameters(f"{self.logdir}/{brk if brk else 'Device 2'} parameters.xml",
                                              master=master)

    # Plot for cyclic test
    def plot_cycle(
            self,
            title="Cyclic Test Result",
            start=None,
            end=None,
            output=0
    ):
        if self.devices[1]:
            self.plot_basic(title, start, end, output, device=1)
        if self.devices[2]:
            self.plot_basic(title, start, end, output, device=2)

    # Plot from data logged with preset layout and variables
    def plot_basic(
            self,
            title="Dyno Result",
            start=None,
            end=None,
            output=0,
            device=1
    ):
        data = pd.read_csv(self._logfile)
        fig, ax = plt.subplots(2, 1, sharex="all")
        fig.set_size_inches(10., 6.)
        plt.xticks(rotation=45, ha='right')
        plt.subplots_adjust(bottom=0.22)
        fig.suptitle(f"Device {device} - {title}")
        # Assuming all plots from log share the same x-axis as time
        x = data["Elapsed"]
        # Subplot 1 with RPM on main axis and Torque on secondary axis
        ax1 = ax[0].twinx()

        try:
            y = data["motor rpm"]
        except KeyError:
            if device == 1:
                y = data["DUT motor rpm"]
            elif device == 2:
                y = data["BRK motor rpm"]
        ax[0].plot(x[start:end], y[start:end], "b-", label="RPM")

        try:
            y = data["Torque"]
            ax1.plot(x[start:end], y[start:end], "r-", label="Torque")
            ax1.set_ylabel("Torque[Nm]", c="red")
            ax[0].set_title("RPM & Torque")
        except KeyError:
            if device == 1:
                y = data["DUT motor current"]
            elif device == 2:
                y = data["BRK motor current"]
            ax1.plot(x[start:end], y[start:end], "r-", label="Motor Current")
            ax1.set_ylabel("Motor Current[A]", c="red")
            ax[0].set_title("RPM & Motor Current")

        ax[0].set_ylabel("Speed[RPM]", c="blue")

        # Subplot 2 with controller and motor temp
        try:
            y = data["controller temperature"]
        except KeyError:
            if device == 1:
                y = data["DUT controller temperature"]
            elif device == 2:
                y = data["BRK controller temperature"]
        ax[1].plot(x[start:end], y[start:end], "b-", label="Controller")

        try:
            y = data["motor temperature"]
        except KeyError:
            if device == 1:
                y = data["DUT motor temperature"]
            elif device == 2:
                y = data["BRK motor temperature"]
        ax[1].plot(x[start:end], y[start:end], "r-", label="Motor")
        if len(x) <= 300:
            plt.xticks(ticks=x[::10], labels=x[::10])
        elif len(x) <= 600:
            plt.xticks(ticks=x[::20], labels=x[::20])
        elif len(x) <= 1200:
            plt.xticks(ticks=x[::30], labels=x[::30])
        else:
            plt.xticks()
        ax[1].set_ylabel("Temperature[C]")
        ax[1].set_xlabel("Elapsed Time[second]")
        ax[1].legend(loc="lower right")
        ax[1].set_title("Temperatures")
        ax[0].grid(axis='both', color='gray', linewidth=0.5)
        ax[1].grid(axis='both', color='gray', linewidth=0.5)
        if output == 0:
            plt.savefig(f"{self._logdir}/Device {device} - {title}.png")
            print("Plot saved")
        elif output == 1:
            plt.show()
        else:
            plt.savefig(f"{self._logdir}/Device {device} - {title}.png")
            print("Plot saved")
            plt.show()

    # Plot Speed/Efficiency/Mechanical Power over Torque from saved extra files
    def plot_over_torque(self, title="RPM/Effi/Pm vs Torque"):
        """Plots RPM, Controller Efficiency & Mechanical Power over Torque"""
        for i, file_name in enumerate(self.extra_files):
            data = pd.read_csv(f"{self.logdir}/{file_name}")
            fig, ax = plt.subplots(1, 1)
            fig.set_size_inches(10., 6.)
            fig.subplots_adjust(right=0.75)
            plt.xticks(rotation=90, ha='right')
            sn = self.extra_barcodes[i]
            fig.suptitle(f"{title}-{sn['serial_num']}-{file_name}")
            # Assuming all plots from log share the same x-axis as time
            x = data["Torque"]
            # Subplot 1 with RPM on main axis and Torque on secondary axis
            ax1 = ax.twinx()
            ax2 = ax.twinx()
            ax2.spines.right.set_position(("axes", 1.2))
            # Speed on primary axis
            try:
                y = data["Motor Speed"]
            except KeyError:
                y = data["DUT motor rpm"]
            p1, = ax.plot(x[:], y[:], "b-", label="Speed[RPM]")
            ax.set_xlabel("Torque[N/m]")
            ax.yaxis.label.set_color(p1.get_color())
            ax.set_ylabel("Speed[RPM]")
            # Mechanical power on primary axis
            try:
                y = data["Mechanical Power"]
            except KeyError:
                pass
            p2, = ax1.plot(x[:], y[:], "r-", label="Mechanical Power[W]")
            ax1.yaxis.label.set_color(p2.get_color())
            ax1.set_ylabel("Mechanical Power[W]")
            # Controller Efficiency on secondary axis
            try:
                y = data["Controller Efficiency"]
            except KeyError:
                pass
            p3, = ax2.plot(x[:], y[:], "c-", label="Efficiency[%]")
            ax2.yaxis.label.set_color(p3.get_color())
            ax2.set_ylabel("Efficiency[%]")
            plt.grid(axis='both', color='gray', linewidth=0.5)

            try:
                ax.legend(handles=[p1, p2, p3])
            except ValueError:
                return

            plt.savefig(f"{self._logdir}/{sn['serial_num']} - {file_name}.png")
            print("Plot saved")

    def plot_ctm_result(self, title="ThermalMax Result", start=None, end=None):
        """Plots Controller ThermalMax Test Result"""
        data = pd.read_csv(self._logfile)
        fig, ax = plt.subplots(1, 1)
        fig.set_size_inches(10., 6.)
        fig.subplots_adjust(right=0.75)
        plt.xticks(rotation=90)
        fig.suptitle(f"{title}")
        # Assuming all plots from log share the same x-axis as time
        x = data["Elapsed"]
        # Subplot 1 with RPM on main axis and Torque on secondary axis
        ax1 = ax.twinx()
        ax2 = ax.twinx()
        ax2.spines.right.set_position(("axes", 1.2))
        # Speed on primary axis
        try:
            y = data["Motor Speed"]
        except KeyError:
            y = data["DUT motor rpm"]
        p1, = ax.plot(x[start:end], y[start:end], "b-", label="Speed[RPM]")
        ax.set_xlabel("Elapsed Time[second]")
        ax.yaxis.label.set_color(p1.get_color())
        ax.set_ylabel("Speed[RPM]")
        # Mechanical power on primary axis
        try:
            y = data["motor current"]
        except KeyError:
            y = data["DUT motor current"]
        p2, = ax1.plot(x[start:end], y[start:end], "r-", label="Motor Current[A]")
        ax1.yaxis.label.set_color(p2.get_color())
        ax1.set_ylabel("Motor Current[A]")
        # Controller Efficiency on secondary axis
        try:
            y = data["motor temperature"]
        except KeyError:
            y = data["DUT motor temperature"]
        p3, = ax2.plot(x[start:end], y[start:end], "c-", label="Motor Temp[C]")
        try:
            y = data["controller temperature"]
        except KeyError:
            y = data["DUT controller temperature"]
        p4, = ax2.plot(x[start:end], y[start:end], "g-", label="DUT Temp[C]")
        ax2.yaxis.label.set_color('black')
        ax2.set_ylabel("Temp[C]")
        plt.grid(axis='both', color='gray', linewidth=0.5)

        try:
            ax.legend(handles=[p1, p2, p3, p4])
        except ValueError:
            return

        plt.savefig(f"{self._logdir}/{str(title).replace('.csv', '')}.png")
        print("Plot saved")

    def plot_error(self, error="DUT warnings", output=0):
        STYLES = ["black", "blue", "red", "green", "magenta", "cyan", "yellow", "gray", "sienna",
                  "orange", "gold", "lime", "teal", "skyblue", "navy", "purple", "pink"]
        label = ["No Issues"]
        if error == "DUT warnings":
            if self.devices[1] is not None:
                label.extend(self.devices[1].faults_parameters["warnings"][1:])
            else:
                label.extend(self.faults_backup[1]["warnings"][1:])
        elif error == "DUT warnings2":
            if self.devices[1] is not None:
                label.extend(self.devices[1].faults_parameters["warnings2"][1:])
            else:
                label.extend(self.faults_backup[1]["warnings2"][1:])
        elif error == "DUT faults":
            if self.devices[1] is not None:
                label.extend(self.devices[1].faults_parameters["faults"][1:])
            else:
                label.extend(self.faults_backup[1]["faults"][1:])
        elif error == "DUT faults2":
            if self.devices[1] is not None:
                label.extend(self.devices[1].faults_parameters["faults2"][1:])
            else:
                label.extend(self.faults_backup[1]["faults2"][1:])
        elif error == "BRK warnings":
            if self.devices[2] is not None:
                label.extend(self.devices[2].faults_parameters["warnings"][1:])
            else:
                label.extend(self.faults_backup[2]["warnings"][1:])
        elif error == "BRK warnings2":
            if self.devices[2] is not None:
                label.extend(self.devices[2].faults_parameters["warnings2"][1:])
            else:
                label.extend(self.faults_backup[2]["warnings2"][1:])
        elif error == "BRK faults":
            if self.devices[2] is not None:
                label.extend(self.devices[2].faults_parameters["faults"][1:])
            else:
                label.extend(self.faults_backup[2]["faults"][1:])
        elif error == "BRK faults2":
            if self.devices[2] is not None:
                label.extend(self.devices[2].faults_parameters["faults2"][1:])
            else:
                label.extend(self.faults_backup[2]["faults2"][1:])

        data = pd.read_csv(self._logfile)
        errors = np.zeros((17, len(data["Time"])))  # starting out all hidden
        try:
            temp = data[error]
        except KeyError:
            try:
                temp = data[error.split(' ')[1]]
            except KeyError:
                print(f"Requested {error} not logged")
                return

        for idx, d in enumerate(temp):
            d = int(d)
            if d == 0:
                errors[16][idx] = 1  # no issue -> 1 -> skip to next
                continue
            for i in range(16):  # toggle error bit -> 2-17
                if d & (1 << i):
                    errors[i][idx] = 17 - i

        fig, ax = plt.subplots(1, 1)
        fig.set_size_inches(10., 6.)
        fig.suptitle(error)
        ax.set_ylim(0.5, 17.5)
        lines = []
        for i, col in enumerate(errors):
            line = ax.scatter(x=data["Elapsed"], y=col, c=STYLES[i], s=1)
            lines.append(line)

        if len(data["Elapsed"]) <= 300:
            plt.xticks(ticks=data["Elapsed"][::10], labels=data["Elapsed"][::10], rotation=45, ha='right')
        elif len(data["Elapsed"]) <= 600:
            plt.xticks(ticks=data["Elapsed"][::20], labels=data["Elapsed"][::20], rotation=45, ha='right')
        elif len(data["Elapsed"]) <= 1200:
            plt.xticks(ticks=data["Elapsed"][::30], labels=data["Elapsed"][::30], rotation=45, ha='right')
        else:
            plt.xticks(rotation=45, ha='right')
        try:
            plt.yticks(ticks=range(1, 18, 1), labels=label)
        except ValueError:
            pass
        ax.set_xlabel("Elapsed Time[second]")
        plt.subplots_adjust(bottom=0.22, left=0.45, right=0.95)
        plt.grid(axis='both', color='gray', linewidth=0.5)

        try:
            if output == 0:
                plt.savefig(f"{self._logdir}/{error}.png")
                print("Plot saved")
            elif output == 1:
                plt.show()
            else:
                plt.savefig(f"{self._logdir}/{error}.png")
                print("Plot saved")
                plt.show()
        except matplotlib.MatplotlibDeprecationWarning:
            pass

    def plot_efficiency_map(
            self,
            title="Efficiency Map",
            internal=False,
            # show_3d=False,
            ratio=1,
            # linear_approx=False,
            # use_final=True,
            # cap_use_avg=False,
            # ignore_boundary=False,
            x_data='Motor Speed',
            y_data='Torque',
            z_data='Motor Efficiency',
            cutoff_data='Motor Efficiency',
            cutoff=(0, 100),
            min_circle=0.001,
            levels=EFFICIENCY_MAP_LEVELS,
            tri_interpolation='linear'
    ):
        # levels = np.arange(60, 100, 2)
        data = self.extra_combinator()
        max_efficiency = max(data[z_data])
        data = data.drop(data[data[cutoff_data] >= cutoff[1]].index)
        data = data.drop(data[data[cutoff_data] < cutoff[0]].index)
        # print(max(data['Motor Efficiency']))
        final_csv = list(self.extra_files.keys())[-1]
        try:
            end_rpm = int(final_csv.split('.')[0].split('/')[1])
        except IndexError:
            end_rpm = int(final_csv.split('.')[0])
        data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        fig = plt.figure()
        fig.set_size_inches(10., 6.)
        ax = plt.gca()
        fig.suptitle(f"{title}{' - Internal' if internal else ''}")
        fig.subplots_adjust(right=1.05, top=0.91, bottom=0.11)

        hsv = matplotlib.pyplot.get_cmap('hsv_r', 256)
        newcolors = hsv(np.linspace(0, 1, 300))
        newcolors = newcolors[44:, :]
        new_cmap = ListedColormap(newcolors)

        x = data[x_data] / ratio
        y = data[y_data] * ratio
        z = data[z_data]

        # if use_final:
        #     x_boundary = data_final[data_final['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data_final[data_final['Efficiency Map Flag'] == 2][y_data] * ratio
        # else:
        #     x_boundary = data[data['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data[data['Efficiency Map Flag'] == 2][y_data] * ratio
        # y_cap = data[data['Efficiency Map Flag'] == 3][y_data] * ratio
        # if cap_use_avg:
        #     cap_avg = np.average(y_cap)
        # else:
        #     try:
        #         cap_avg = max(y_cap)
        #     except ValueError:
        #         cap_avg = max(y_boundary)

        # model_x_data = np.linspace(1, max(x), num=int(max(x) + 1))
        # model_y_data = np.linspace(1, max(y), num=int(max(y) * 10 + 1))

        # meshing with Delaunay triangulation
        tri = Triangulation(x, y)

        # masking badly shaped triangles at the border of the triangular mesh.
        mask = TriAnalyzer(tri).get_flat_tri_mask(min_circle)
        tri.set_mask(mask)

        # refining the data
        refiner = UniformTriRefiner(tri)
        tri_refi, z_test_refi = refiner.refine_field(z,
                                                     triinterpolator=LinearTriInterpolator(
                                                         tri, z) if tri_interpolation == 'linear' else
                                                     CubicTriInterpolator(tri, z))
        tcf = ax.tricontourf(tri_refi, z_test_refi, alpha=0.8, cmap=new_cmap,
                             levels=get_efficiency_levels(cutoff), # levels[3:-12],
                             vmin=cutoff[0], vmax=cutoff[1])
        cset1 = ax.tricontour(tri_refi, z_test_refi, colors='k', linewidths=[1, 0.5], levels=levels,
                              vmin=cutoff[0], vmax=cutoff[1])
        ax.clabel(cset1, inline=1)

        # x_range = range(int(max(x) * 0.12), int(max(x) * 0.5), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.2), int(max(y) * 0.6), int(len(x_range) + 1), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # for i, r in enumerate(x_range):
        #     try:
        #         clabel_manual.append((r, y_range[i]))
        #     except IndexError:
        #         # print(i)
        #         break
        # x_range = range(int(max(x) * 0.6), int(max(x)), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.4), int(max(y) * 0.2), int(len(x_range) + 1), endpoint=False)

        if internal:
            ax.scatter(x, y, 5, color='purple', alpha=0.5)
        # if not ignore_boundary:
            # ax.plot(model_x_data[:boundary_X], [cap_avg] * boundary_X,
            #         color='black', linewidth=3)  # Horizontal Y cap
            # ax.plot([end_x] * len(end_Y), end_Y, color='black', linewidth=3)  # Vertical X Cap
            # if linear_approx:
            #     ax.plot(model_x_data[boundary_X:], boundary_power_cap(model_x_data[boundary_X:], *p),
            #             color='black', linewidth=3)

        # cset1 = ax.contour(X, Y, Z, colors='k', levels=levels, linewidths=[1, 0.5])

        # if not ignore_boundary:
        #     max_y, max_x = np.where(Z == max(map(max, Z)))
        #     x_range = range(int(end_rpm * .05), int(X[0][max_x[0]]), int(end_rpm * .05))
        #     y_range = np.linspace(int(max(y) * 0.8), int(Y[max_y[0]][0]), len(x_range), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # if not ignore_boundary:
        #     for i, r in enumerate(x_range):
        #         try:
        #             clabel_manual.append((r, y_range[i]))
        #         except IndexError:
        #             # print(i)
        #             break
        #     ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=clabel_manual)
        # else:
        #     ax.clabel(cset1, inline=True, fontsize=10, colors='k')

        # plt.colorbar(ticks=levels)
        plt.colorbar(tcf)

        ax.grid()
        plt.xticks(ticks=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)),
                   labels=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)), rotation=0)
        # y_labels = []
        # y_label_text = []
        # print(max(y), int(max(y) + 1), int(max(y) / 10))
        # for i in range(0, int(max(y) + 1), int(max(y) / 10) if int(max(y) / 10) > 0 else 1):
        #     y_labels.append(i)
        #     y_label_text.append(i)
        # if internal:
        #     if abs(max(y) - y_labels[-1]) > 0.5:
        #         y_labels.append(max(y))
        #         y_label_text.append(f"{max(y):.3f}")
        # else:
        #     if abs(cap_avg - y_labels[-1]) > 0.5:
        #         y_labels.append(cap_avg)
        #         y_label_text.append(f"{cap_avg:0.3f}")
        # plt.yticks(ticks=y_labels, labels=y_label_text, rotation=0)

        # See fit plane in 3D
        # cset1 = ax.contour(X, Y, Z, zdir='z', offset=min(z), cmap=cm.coolwarm, levels=levels)
        # cset2 = ax.contour(X, Y, Z, zdir='x', offset=min(x), cmap=cm.coolwarm)
        # cset3 = ax.contour(X, Y, Z, zdir='y', offset=max(y), cmap=cm.coolwarm)
        try:
            ax.set_xlabel(f'{x_data} [{self.devices[PA].log_params[x_data].Units.strip()}]')
        except KeyError:
            target = x_data.split(' ')[0]
            name = x_data[4:]
            if target == 'DUT':
                ax.set_xlabel(f'{x_data} [{self.devices[1].log_params[name].Units.strip()}]')
            else:
                ax.set_xlabel(f'{x_data} [{self.devices[2].log_params[name].Units.strip()}]')
        try:
            ax.set_ylabel(f'{y_data} [{self.devices[PA].log_params[y_data].Units.strip()}]')
        except KeyError:
            target = y_data.split(' ')[0]
            name = y_data[4:]
            if target == 'DUT':
                ax.set_ylabel(f'{y_data} [{self.devices[1].log_params[name].Units.strip()}]')
            else:
                ax.set_ylabel(f'{y_data} [{self.devices[2].log_params[name].Units.strip()}]')
        ax.set_xlim(0, max(x) * 1.1)
        ax.set_ylim(0, max(y) + 1)

        plt.savefig(f"{self._logdir}/{title}{' - Internal' if internal else ''}.png")
        print("Plot saved")

    def plot_temperature_map(
            self,
            title="Efficiency Map",
            internal=False,
            # show_3d=False,
            ratio=1,
            # linear_approx=False,
            # use_final=True,
            # cap_use_avg=False,
            # ignore_boundary=False,
            x_data='Target Speed',
            y_data='Target Torque',
            z_data='Temperature',
            levels=EFFICIENCY_MAP_LEVELS
    ):
        # levels = np.arange(60, 100, 2)
        data = self.extra_combinator()
        # data = data.drop(data[data[cutoff_data] >= cutoff[1]].index)
        # data = data.drop(data[data[cutoff_data] < cutoff[0]].index)
        # # print(max(data['Motor Efficiency']))
        # final_csv = list(self.extra_files.keys())[-1]
        # try:
        #     end_rpm = int(final_csv.split('.')[0].split('/')[1])
        # except IndexError:
        #     end_rpm = int(final_csv.split('.')[0])
        # data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        fig = plt.figure()
        fig.set_size_inches(10., 6.)
        ax = plt.gca()
        fig.suptitle(f"{title}{' - Internal' if internal else ''}")
        fig.subplots_adjust(right=1.05, top=0.91, bottom=0.11)

        hsv = matplotlib.pyplot.get_cmap('hsv_r', 256)
        newcolors = hsv(np.linspace(0, 1, 300))
        newcolors = newcolors[44:, :]
        new_cmap = ListedColormap(newcolors)

        x = data[x_data].unique() / ratio
        y = data[y_data].unique() * ratio
        if len(data[z_data]) != len(x) * len(y):
            z = []
            for i, x_val in enumerate(x):
                temp = []
                for y_val in y:
                    try:
                        temp.append(data.loc[(data[x_data] == x_val) & (data[y_data] == y_val), z_data].item())
                    except ValueError:
                        break
                if i > 0:
                    if len(z[i - 1]) > len(temp):
                        break
                z.append(temp)
        else:
            z = data[z_data].values.reshape(len(x), len(y))

        z = z.T
        # if use_final:
        #     x_boundary = data_final[data_final['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data_final[data_final['Efficiency Map Flag'] == 2][y_data] * ratio
        # else:
        #     x_boundary = data[data['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data[data['Efficiency Map Flag'] == 2][y_data] * ratio
        # y_cap = data[data['Efficiency Map Flag'] == 3][y_data] * ratio
        # if cap_use_avg:
        #     cap_avg = np.average(y_cap)
        # else:
        #     try:
        #         cap_avg = max(y_cap)
        #     except ValueError:
        #         cap_avg = max(y_boundary)

        # model_x_data = np.linspace(1, max(x), num=int(max(x) + 1))
        # model_y_data = np.linspace(1, max(y), num=int(max(y) * 10 + 1))

        cs = ax.contourf(x, y, z, cmap=new_cmap)

        # x_range = range(int(max(x) * 0.12), int(max(x) * 0.5), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.2), int(max(y) * 0.6), int(len(x_range) + 1), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # for i, r in enumerate(x_range):
        #     try:
        #         clabel_manual.append((r, y_range[i]))
        #     except IndexError:
        #         # print(i)
        #         break
        # x_range = range(int(max(x) * 0.6), int(max(x)), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.4), int(max(y) * 0.2), int(len(x_range) + 1), endpoint=False)

        if internal:
            ax.scatter(data[x_data], data[y_data], 5, color='black', alpha=0.5)
        # if not ignore_boundary:
            # ax.plot(model_x_data[:boundary_X], [cap_avg] * boundary_X,
            #         color='black', linewidth=3)  # Horizontal Y cap
            # ax.plot([end_x] * len(end_Y), end_Y, color='black', linewidth=3)  # Vertical X Cap
            # if linear_approx:
            #     ax.plot(model_x_data[boundary_X:], boundary_power_cap(model_x_data[boundary_X:], *p),
            #             color='black', linewidth=3)

        # cset1 = ax.contour(X, Y, Z, colors='k', levels=levels, linewidths=[1, 0.5])

        # if not ignore_boundary:
        #     max_y, max_x = np.where(Z == max(map(max, Z)))
        #     x_range = range(int(end_rpm * .05), int(X[0][max_x[0]]), int(end_rpm * .05))
        #     y_range = np.linspace(int(max(y) * 0.8), int(Y[max_y[0]][0]), len(x_range), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # if not ignore_boundary:
        #     for i, r in enumerate(x_range):
        #         try:
        #             clabel_manual.append((r, y_range[i]))
        #         except IndexError:
        #             # print(i)
        #             break
        #     ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=clabel_manual)
        # else:
        #     ax.clabel(cset1, inline=True, fontsize=10, colors='k')

        # plt.colorbar(ticks=levels)
        plt.colorbar(cs)

        ax.grid()
        # plt.xticks(ticks=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)),
        #            labels=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)), rotation=0)
        # y_labels = []
        # y_label_text = []
        # print(max(y), int(max(y) + 1), int(max(y) / 10))
        # for i in range(0, int(max(y) + 1), int(max(y) / 10) if int(max(y) / 10) > 0 else 1):
        #     y_labels.append(i)
        #     y_label_text.append(i)
        # if internal:
        #     if abs(max(y) - y_labels[-1]) > 0.5:
        #         y_labels.append(max(y))
        #         y_label_text.append(f"{max(y):.3f}")
        # else:
        #     if abs(cap_avg - y_labels[-1]) > 0.5:
        #         y_labels.append(cap_avg)
        #         y_label_text.append(f"{cap_avg:0.3f}")
        # plt.yticks(ticks=y_labels, labels=y_label_text, rotation=0)

        # See fit plane in 3D
        # cset1 = ax.contour(X, Y, Z, zdir='z', offset=min(z), cmap=cm.coolwarm, levels=levels)
        # cset2 = ax.contour(X, Y, Z, zdir='x', offset=min(x), cmap=cm.coolwarm)
        # cset3 = ax.contour(X, Y, Z, zdir='y', offset=max(y), cmap=cm.coolwarm)
        try:
            ax.set_xlabel(f'{x_data} [RPM] [{self.devices[PA].log_params[x_data].Units.strip()}]')
        except KeyError:
            target = x_data.split(' ')[0]
            name = x_data[4:]
            if target == 'DUT':
                ax.set_xlabel(f'{x_data} [RPM] [{self.devices[1].log_params[name].Units.strip()}]')
            elif target == 'BRK':
                ax.set_xlabel(f'{x_data} [RPM] [{self.devices[2].log_params[name].Units.strip()}]')
            else:
                ax.set_xlabel(f'{x_data} [RPM]')
        try:
            ax.set_ylabel(f'{y_data} [Nm] [{self.devices[PA].log_params[y_data].Units.strip()}]')
        except KeyError:
            target = y_data.split(' ')[0]
            name = y_data[4:]
            if target == 'DUT':
                ax.set_ylabel(f'{y_data} [Nm] [{self.devices[1].log_params[name].Units.strip()}]')
            elif target == 'BRK':
                ax.set_ylabel(f'{y_data} [Nm] [{self.devices[2].log_params[name].Units.strip()}]')
            else:
                ax.set_ylabel(f'{y_data} [Nm]')
        # ax.set_xlim(0, max(x) * 1.1)
        # ax.set_ylim(0, max(y) + 1)

        plt.savefig(f"{self._logdir}/{title}{' - Internal' if internal else ''}.png")
        print("Plot saved")

    def plot_torque_constant(
            self,
            title="Torque Constant",
            internal=False,
            # show_3d=False,
            ratio=1,
            # linear_approx=False,
            # use_final=True,
            # cap_use_avg=False,
            # ignore_boundary=False,
            x_data='Motor Speed',
            y_data='Torque',
            cutoff_data='Motor Efficiency',
            cutoff=(0, 100),
            min_circle=0.001
    ):
        # levels = np.arange(60, 100, 2)
        data = self.extra_combinator()
        data = data.drop(data[data[cutoff_data] >= cutoff[1]].index)
        data = data.drop(data[data[cutoff_data] < cutoff[0]].index)
        # print(max(data['Motor Efficiency']))
        final_csv = list(self.extra_files.keys())[-1]
        # data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        try:
            end_rpm = int(final_csv.split('.')[0].split('/')[1])
        except IndexError:
            end_rpm = int(final_csv.split('.')[0])
        # final_csv = list(self.extra_files.keys())[-1]
        data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        fig = plt.figure()
        fig.set_size_inches(10., 6.)
        ax = plt.gca()
        fig.suptitle(f"{title}{' - Internal' if internal else ''}")
        fig.subplots_adjust(right=1.05, top=0.91, bottom=0.11)

        hsv = plt.get_cmap('hsv_r', 256)
        newcolors = hsv(np.linspace(0, 1, 300))
        newcolors = newcolors[44:, :]
        new_cmap = ListedColormap(newcolors)

        x = data[x_data] / ratio
        y = data[y_data] * ratio

        avg_current = np.average([data['Phase RMS Current 1'],
                                  data['Phase RMS Current 2'],
                                  data['Phase RMS Current 3']],
                                 axis=0) * 1.414
        z = y / avg_current

        print(max(z))
        levels = np.linspace(0.0, max(z), num=20)
        # levels = None

        x_bad_current = []
        y_bad_current = []
        # print(len(avg_current), len(data['DUT motor current']))
        for dut_current, avg, bad_x ,bad_y in zip(data['DUT motor current'], avg_current, x, y):
            # print(dut_current, avg, bad_x ,bad_y)
            if dut_current * 0.95 <= avg <= 1.05 * dut_current:
                continue
            else:
                x_bad_current.append(bad_x)
                y_bad_current.append(bad_y)

        # if use_final:
        #     x_boundary = data_final[data_final['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data_final[data_final['Efficiency Map Flag'] == 2][y_data] * ratio
        # else:
        #     x_boundary = data[data['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data[data['Efficiency Map Flag'] == 2][y_data] * ratio
        # y_cap = data[data['Efficiency Map Flag'] == 3][y_data] * ratio
        # if cap_use_avg:
        #     cap_avg = np.average(y_cap)
        # else:
        #     try:
        #         cap_avg = max(y_cap)
        #     except ValueError:
        #         cap_avg = max(y_boundary)

        # model_x_data = np.linspace(1, max(x), num=int(max(x) + 1))
        # model_y_data = np.linspace(1, max(y), num=int(max(y) * 10 + 1))
        # X, Y = np.meshgrid(model_x_data, model_y_data)
        # parameters, covariance = curve_fit(function, [x, y], z)
        # Z = function(np.array([X, Y]), *parameters)
        # Z[Z > max(data[data['Efficiency Map Flag'] == 2][z_data])] = max(data[data['Efficiency Map Flag'] == 2][z_data])

        # if not ignore_boundary:
        #     if linear_approx:
        #         p, c = curve_fit(boundary_power_cap, x_boundary, y_boundary, absolute_sigma=True)
        #         boundary_Y = boundary_power_cap(model_x_data, *p)
        #     else:
        #         p, c = curve_fit(boundary_function, x_boundary, y_boundary, absolute_sigma=True)
        #         boundary_Y = boundary_function(model_x_data, *p)
        #     # print(p)
        #
        #     max_boundary_x = []
        #     if linear_approx:
        #         for val in model_x_data:
        #             if boundary_power_cap(val, *p) >= cap_avg:
        #                 max_boundary_x.append(val)
        #     else:
        #         for val in model_x_data:
        #             if boundary_function(val, *p) >= cap_avg:
        #                 max_boundary_x.append(val)
        #
        #     try:
        #         max_boundary_x = max(max_boundary_x)
        #     except ValueError:
        #         max_boundary_x = max(x_boundary)
        #
        #     boundary_Y[boundary_Y > cap_avg] = cap_avg
        #     boundary_X = 0
        #     for val in boundary_Y:
        #         if val == cap_avg:
        #             boundary_X += 1
        #         else:
        #             break
        #     # print(boundary_X)
        #
        #     end_x = end_rpm
        #     end_y = boundary_Y[-1]
        #     end_Y = model_y_data[model_y_data < end_y]
        #
        #     for i, boundary_val in enumerate(boundary_Y):
        #         for j, y_val in enumerate(Y[:,0]):
        #             if i < max_boundary_x:
        #                 if y_val > cap_avg:
        #                     Z[j][i] = 0
        #             else:
        #                 if y_val > boundary_val:
        #                     Z[j][i] = 0

        tri = Triangulation(x, y)

        # masking badly shaped triangles at the border of the triangular mesh.
        mask = TriAnalyzer(tri).get_flat_tri_mask(min_circle)
        tri.set_mask(mask)

        # refining the data
        refiner = UniformTriRefiner(tri)
        tri_refi, z_test_refi = refiner.refine_field(z,
                                                     triinterpolator=LinearTriInterpolator(tri, z))
        tcf = ax.tricontourf(tri_refi, z_test_refi, alpha=0.8, levels=levels, cmap=new_cmap)
        cset1 = ax.tricontour(tri_refi, z_test_refi, colors='k', linewidths=[1, 0.5], levels=levels)
        ax.clabel(cset1, inline=1)

        # x_range = range(int(max(x) * 0.12), int(max(x) * 0.5), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.2), int(max(y) * 0.6), int(len(x_range) + 1), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # for i, r in enumerate(x_range):
        #     try:
        #         clabel_manual.append((r, y_range[i]))
        #     except IndexError:
        #         # print(i)
        #         break
        # x_range = range(int(max(x) * 0.6), int(max(x)), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.4), int(max(y) * 0.2), int(len(x_range) + 1), endpoint=False)

        if internal:
            ax.scatter(x, y, 5, color='purple', alpha=0.5)
            ax.scatter(x_bad_current, y_bad_current, 8, color='red', marker='x')
        # if not ignore_boundary:
        #     # ax.plot(model_x_data[:boundary_X], [cap_avg] * boundary_X,
        #     #         color='black', linewidth=3)  # Horizontal Y cap
        #     # ax.plot([end_x] * len(end_Y), end_Y, color='black', linewidth=3)  # Vertical X Cap
        #     if linear_approx:
        #         ax.plot(model_x_data[boundary_X:], boundary_power_cap(model_x_data[boundary_X:], *p),
        #                 color='black', linewidth=3)

        # cset1 = ax.contour(X, Y, Z, colors='k', levels=levels, linewidths=[1, 0.5])

        # if not ignore_boundary:
        #     max_y, max_x = np.where(Z == max(map(max, Z)))
        #     x_range = range(int(end_rpm * .05), int(X[0][max_x[0]]), int(end_rpm * .05))
        #     y_range = np.linspace(int(max(y) * 0.8), int(Y[max_y[0]][0]), len(x_range), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # if not ignore_boundary:
        #     for i, r in enumerate(x_range):
        #         try:
        #             clabel_manual.append((r, y_range[i]))
        #         except IndexError:
        #             # print(i)
        #             break
        #     ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=clabel_manual)
        # else:
        #     ax.clabel(cset1, inline=True, fontsize=10, colors='k')

        # plt.colorbar(ticks=levels)
        plt.colorbar(tcf)

        ax.grid()
        plt.xticks(ticks=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)),
                   labels=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)), rotation=0)
        # y_labels = []
        # y_label_text = []
        # for i in range(0, int(max(y) + 1), int(max(y) / 10) if int(max(y) / 10) > 0 else 1):
        #     y_labels.append(i)
        #     y_label_text.append(i)
        # if internal:
        #     if abs(max(y) - y_labels[-1]) > 0.5:
        #         y_labels.append(max(y))
        #         y_label_text.append(f"{max(y):.3f}")
        # else:
        #     if abs(cap_avg - y_labels[-1]) > 0.5:
        #         y_labels.append(cap_avg)
        #         y_label_text.append(f"{cap_avg:0.3f}")
        # plt.yticks(ticks=y_labels, labels=y_label_text, rotation=0)

        # See fit plane in 3D
        # cset1 = ax.contour(X, Y, Z, zdir='z', offset=min(z), cmap=cm.coolwarm, levels=levels)
        # cset2 = ax.contour(X, Y, Z, zdir='x', offset=min(x), cmap=cm.coolwarm)
        # cset3 = ax.contour(X, Y, Z, zdir='y', offset=max(y), cmap=cm.coolwarm)
        try:
            ax.set_xlabel(f'{x_data} [{self.devices[PA].log_params[x_data].Units.strip()}]')
        except KeyError:
            target = x_data.split(' ')[0]
            name = x_data[4:]
            if target == 'DUT':
                ax.set_xlabel(f'{x_data} [{self.devices[1].log_params[name].Units.strip()}]')
            else:
                ax.set_xlabel(f'{x_data} [{self.devices[2].log_params[name].Units.strip()}]')
        try:
            ax.set_ylabel(f'{y_data} [{self.devices[PA].log_params[y_data].Units.strip()}]')
        except KeyError:
            target = y_data.split(' ')[0]
            name = y_data[4:]
            if target == 'DUT':
                ax.set_ylabel(f'{y_data} [{self.devices[1].log_params[name].Units.strip()}]')
            else:
                ax.set_ylabel(f'{y_data} [{self.devices[2].log_params[name].Units.strip()}]')
        ax.set_xlim(0, max(x) * 1.1)
        ax.set_ylim(0, max(y) + 1)

        plt.savefig(f"{self._logdir}/{title}{' - Internal' if internal else ''}.png")
        print("Plot saved")

    def plot_efficiency_map_over_power(
            self,
            title="Efficiency VS Motor Power & RPM",
            internal=False,
            ratio=1,
            cutoff_data='Motor Efficiency',
            cutoff=(0, 100),
            # show_3d=False,
            # use_final=True,
            min_circle=0.001
    ):
        # levels = np.arange(60, 100, 2)
        data = self.extra_combinator()
        data = data.drop(data[data[cutoff_data] >= cutoff[1]].index)
        data = data.drop(data[data[cutoff_data] < cutoff[0]].index)
        final_csv = list(self.extra_files.keys())[-1]
        data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        try:
            end_rpm = int(final_csv.split('.')[0].split('/')[1])
        except IndexError:
            end_rpm = int(final_csv.split('.')[0])
        # final_csv = list(self.extra_files.keys())[-3]
        # data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        fig = plt.figure()
        fig.set_size_inches(10., 6.)
        ax = plt.gca()
        fig.suptitle(f"{title}{' - Internal' if internal else ''}")
        fig.subplots_adjust(right=1.05, top=0.91, left=0.08, bottom=0.11)

        if ratio == 1:
            x = data['Motor Speed']
        else:
            raw_x = data['Motor Speed']
            x = []
            for r_x in raw_x:
                x.append(r_x / ratio)
        y = data['Mechanical Power']
        z = data['Motor Efficiency']

        levels = [10, 20, 30, 40, 50,
                  60, 65, 70, 75, 80,
                  82, 84, 85, 86, 87,
                  88, 89, 90, 91, 92,
                  93, 94, 95, 96, 97,
                  98, 99, 100]

        # if use_final:
        #     x_boundary = data_final[data_final['Efficiency Map Flag'] == 3]['Motor Speed'] / ratio
        #     y_boundary = data_final[data_final['Efficiency Map Flag'] == 3]['Mechanical Power']
        # else:
        #     x_boundary = data[data['Efficiency Map Flag'] == 3]['Motor Speed'] / ratio
        #     y_boundary = data[data['Efficiency Map Flag'] == 3]['Mechanical Power']

        # model_x_data = np.linspace(1, max(x), num=int(max(x) + 1))
        # model_y_data = np.linspace(1, max(y), num=int(max(x) + 1))
        # X, Y = np.meshgrid(model_x_data, model_y_data)

        if internal:
            ax.scatter(x, y, 5, color='purple', alpha=0.5)

        # meshing with Delaunay triangulation
        tri = Triangulation(x, y)

        # masking badly shaped triangles at the border of the triangular mesh.
        mask = TriAnalyzer(tri).get_flat_tri_mask(min_circle)
        tri.set_mask(mask)

        # refining the data
        refiner = UniformTriRefiner(tri)
        tri_refi, z_test_refi = refiner.refine_field(z,
                                                     triinterpolator=LinearTriInterpolator(tri, z))
        tcf = ax.tricontourf(tri_refi, z_test_refi, alpha=0.8)
        cset1 = ax.tricontour(tri_refi, z_test_refi, colors='k', linewidths=[1, 0.5], levels=levels)
        ax.clabel(cset1, inline=1)

        # x_range = range(int(max(x) * 0.12), int(max(x) * 0.5), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.2), int(max(y) * 0.6), int(len(x_range) + 1), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # for i, r in enumerate(x_range):
        #     try:
        #         clabel_manual.append((r, y_range[i]))
        #     except IndexError:
        #         # print(i)
        #         break
        # x_range = range(int(max(x) * 0.6), int(max(x)), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.4), int(max(y) * 0.2), int(len(x_range) + 1), endpoint=False)
        # for i, r in enumerate(x_range):
        #     try:
        #         clabel_manual.append((r, y_range[i]))
        #     except IndexError:
        #         # print(i)
        #         break
        # ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=clabel_manual)
        # ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=True)

        # plt.colorbar(ticks=levels)
        plt.colorbar(tcf)

        ax.grid()
        plt.xticks(ticks=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)),
                   labels=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)), rotation=0)
        # y_labels = []
        # y_label_text = []
        # for i in range(0, int(max(y) + 1), int(max(y) / 10)):
        #     y_labels.append(i)
        #     y_label_text.append(i)
        # # if internal:
        # #     y_labels.append(max(y))
        # #     y_label_text.append(f"{max(y):.3f}")
        # # else:
        # #     y_labels.append(cap_avg)
        # #     y_label_text.append(f"{cap_avg:0.3f}")
        # plt.yticks(ticks=y_labels, labels=y_label_text, rotation=0)

        ax.set_xlabel('RPM')
        ax.set_ylabel('Motor Power [W]')
        ax.set_xlim(0, max(x) * 1.1)
        ax.set_ylim(0, max(y) + 1)

        plt.savefig(f"{self._logdir}/{title}{' - Internal' if internal else ''}.png")
        print("Plot saved")

    def plot_motor_power_map(
            self,
            title="Motor Power Map",
            internal=False,
            # show_3d=False,
            ratio=1,
            # use_final=True,
            # linear_approx=False,
            # cap_use_avg=False,
            # ignore_boundary=False,
            x_data='Motor Speed',
            y_data='Torque',
            z_data='Mechanical Power',
            cutoff_data='Motor Efficiency',
            cutoff=(0, 100),
            min_circle=0.001
    ):
        data = self.extra_combinator()
        data = data.drop(data[data[cutoff_data] >= cutoff[1]].index)
        data = data.drop(data[data[cutoff_data] < cutoff[0]].index)
        final_csv = list(self.extra_files.keys())[-1]
        # data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        try:
            end_rpm = int(final_csv.split('.')[0].split('/')[1])
        except IndexError:
            end_rpm = int(final_csv.split('.')[0])
        # final_csv = list(self.extra_files.keys())[-1]
        data_final = pd.read_csv(f"{self.logdir}/{final_csv}")
        fig = plt.figure()
        fig.set_size_inches(10., 6.)
        ax = plt.gca()
        fig.suptitle(f"{title}{' - Internal' if internal else ''}")
        fig.subplots_adjust(right=1.05, top=0.91, bottom=0.11)

        hsv = matplotlib.pyplot.get_cmap('hsv_r', 256)
        newcolors = hsv(np.linspace(0, 1, 300))
        newcolors = newcolors[44:, :]
        new_cmap = ListedColormap(newcolors)
        # print(new_cmap)

        x = data[x_data] / ratio
        y = data[y_data] * ratio
        z = data[z_data]

        levels = np.linspace(0, int(max(z)), num=12)

        # if use_final:
        #     x_boundary = data_final[data_final['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data_final[data_final['Efficiency Map Flag'] == 2][y_data] * ratio
        # else:
        #     x_boundary = data[data['Efficiency Map Flag'] == 2][x_data] / ratio
        #     y_boundary = data[data['Efficiency Map Flag'] == 2][y_data] * ratio
        # y_cap = data[data['Efficiency Map Flag'] == 3][y_data] * ratio
        # if cap_use_avg:
        #     cap_avg = np.average(y_cap)
        # else:
        #     try:
        #         cap_avg = max(y_cap)
        #     except ValueError:
        #         cap_avg = max(y_boundary)

        # model_x_data = np.linspace(0, max(x), num=int(max(x) + 1))
        # model_y_data = np.linspace(0, max(y), num=int(max(y) * 10 + 1))
        # X, Y = np.meshgrid(model_x_data, model_y_data)
        # parameters, covariance = curve_fit(f_power, [x, y], z)
        # Z = f_power(np.array([X, Y]), *parameters)
        # Z[Z > max(data[data['Efficiency Map Flag'] == 2][z_data])] = max(data[data['Efficiency Map Flag'] == 2][z_data])
        # if not show_3d:
        # if not ignore_boundary:
        #     if linear_approx:
        #         p, c = curve_fit(boundary_power_cap, x_boundary, y_boundary, absolute_sigma=True)
        #         boundary_Y = boundary_power_cap(model_x_data, *p)
        #     else:
        #         p, c = curve_fit(boundary_function, x_boundary, y_boundary, absolute_sigma=True)
        #         boundary_Y = boundary_function(model_x_data, *p)
        #     # print(p)
        #
        #     max_boundary_x = []
        #     if linear_approx:
        #         for val in model_x_data:
        #             if boundary_power_cap(val, *p) >= cap_avg:
        #                 max_boundary_x.append(val)
        #     else:
        #         for val in model_x_data:
        #             if boundary_function(val, *p) >= cap_avg:
        #                 max_boundary_x.append(val)
        #
        #     try:
        #         max_boundary_x = max(max_boundary_x)
        #     except ValueError:
        #         max_boundary_x = max(x_boundary)
        #
        #     boundary_Y[boundary_Y > cap_avg] = cap_avg
        #     boundary_X = 0
        #     for val in boundary_Y:
        #         if val == cap_avg:
        #             boundary_X += 1
        #         else:
        #             break
        #     # print(boundary_X)
        #
        #     end_x = end_rpm
        #     end_y = boundary_Y[-1]
        #     end_Y = model_y_data[model_y_data < end_y]
        #
        #     for i, boundary_val in enumerate(boundary_Y):
        #         for j, y_val in enumerate(Y[:,0]):
        #             if i < max_boundary_x:
        #                 if y_val > cap_avg:
        #                     Z[j][i] = 0
        #             else:
        #                 if y_val > boundary_val:
        #                     Z[j][i] = 0

        # plt.pcolormesh(X, Y, Z, cmap='Reds', vmin=60, vmax=max(data[data['Efficiency Map Flag'] == 2][z_data]))
        # meshing with Delaunay triangulation
        tri = Triangulation(x, y)

        # masking badly shaped triangles at the border of the triangular mesh.
        mask = TriAnalyzer(tri).get_flat_tri_mask(min_circle)
        tri.set_mask(mask)

        # refining the data
        refiner = UniformTriRefiner(tri)
        tri_refi, z_test_refi = refiner.refine_field(z,
                                                     triinterpolator=LinearTriInterpolator(tri, z))
        tcf = ax.tricontourf(tri_refi, z_test_refi, alpha=0.8, levels=levels, cmap=new_cmap)
        cset1 = ax.tricontour(tri_refi, z_test_refi, colors='k', linewidths=[1, 0.5], levels=levels)
        ax.clabel(cset1, inline=1)

        # x_range = range(int(max(x) * 0.12), int(max(x) * 0.5), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.2), int(max(y) * 0.6), int(len(x_range) + 1), endpoint=False)
        # print(cset1.collections)
        # clabel_manual = []
        # for i, r in enumerate(x_range):
        #     try:
        #         clabel_manual.append((r, y_range[i]))
        #     except IndexError:
        #         # print(i)
        #         break
        # x_range = range(int(max(x) * 0.6), int(max(x)), int(max(x) * 0.1))
        # y_range = np.linspace(int(max(y) * 0.4), int(max(y) * 0.2), int(len(x_range) + 1), endpoint=False)
        # for i, r in enumerate(x_range):
        #     try:
        #         clabel_manual.append((r, y_range[i]))
        #     except IndexError:
        #         # print(i)
        #         break
        # ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=clabel_manual)
        # ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=True)

        # plt.colorbar(ticks=levels)
        plt.colorbar(tcf)

        if internal:
            ax.scatter(x, y, 5, color='purple', alpha=0.5)
            # ax.scatter(x_boundary, y_boundary, 10, color='green', alpha=1)
            # ax.plot(model_x_data[:boundary_X], [cap_avg] * boundary_X, color='black', linewidth=3)
            # ax.plot([end_x] * len(end_Y), end_Y, color='black', linewidth=3)
            # if linear_approx:
            #     ax.plot(model_x_data[boundary_X:], boundary_power_cap(model_x_data[boundary_X:], *p), color='black', linewidth=3)

            # cset1 = ax.contour(X, Y, Z, colors='k', levels=levels, linewidths=[1, 0.5])

            # x_range = np.linspace(int(0.2 * max(x)), int(0.8 * max(x)), int(max(z) / 1000) - 1)
            # y_range = np.linspace(int(max(y) * 0.2), int(max(y) * 0.7), int(max(z) / 1000) - 1)
            # print(cset1.collections)
            # clabel_manual = []
            # if not ignore_boundary:
            #     for i, r in enumerate(x_range):
            #         try:
            #             if linear_approx:
            #                 if boundary_power_cap(r, *p) > y_range[i]:
            #                     clabel_manual.append((r, y_range[i]))
            #             else:
            #                 if boundary_function(r, *p) > y_range[i]:
            #                     clabel_manual.append((r, y_range[i]))
            #         except IndexError:
            #             print(i)
            #             break
            #     ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=clabel_manual)
            # else:
            #     ax.clabel(cset1, inline=True, fontsize=10, colors='k')
            # ax.clabel(cset1, inline=True, fontsize=10, colors='k', manual=True)

            # plt.colorbar()

        ax.grid()
        plt.xticks(ticks=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)),
                   labels=range(0, int(end_rpm * 1.1), int(end_rpm * 0.1)), rotation=0)
        # y_labels = []
        # y_label_text = []
        # for i in range(0, int(max(y) + 1), int(max(y) / 10) if int(max(y) / 10) > 0 else 1):
        #     y_labels.append(i)
        #     y_label_text.append(i)
        # if internal:
        #     if abs(max(y) - y_labels[-1]) > 0.5:
        #         y_labels.append(max(y))
        #         y_label_text.append(f"{max(y):.3f}")
        # else:
        #     if abs(cap_avg - y_labels[-1]) > 0.5:
        #         y_labels.append(cap_avg)
        #         y_label_text.append(f"{cap_avg:0.3f}")
        # plt.yticks(ticks=y_labels, labels=y_label_text, rotation=0)

        try:
            ax.set_xlabel(f'{x_data} [{self.devices[PA].log_params[x_data].Units.strip()}]')
        except KeyError:
            target = x_data.split(' ')[0]
            name = x_data[4:]
            if target == 'DUT':
                ax.set_xlabel(f'{x_data} [{self.devices[1].log_params[name].Units.strip()}]')
            else:
                ax.set_xlabel(f'{x_data} [{self.devices[2].log_params[name].Units.strip()}]')
        try:
            ax.set_ylabel(f'{y_data} [{self.devices[PA].log_params[y_data].Units.strip()}]')
        except KeyError:
            target = y_data.split(' ')[0]
            name = y_data[4:]
            if target == 'DUT':
                ax.set_ylabel(f'{y_data} [{self.devices[1].log_params[name].Units.strip()}]')
            else:
                ax.set_ylabel(f'{y_data} [{self.devices[2].log_params[name].Units.strip()}]')
        ax.set_xlim(0, max(x) * 1.1)
        ax.set_ylim(0, max(y) + 1)

        plt.savefig(f"{self._logdir}/{title}{' - Internal' if internal else ''}.png")
        print("Plot saved")

    def extra_combinator(self):
        combined = pd.DataFrame()
        for i, file_name in enumerate(self.extra_files):
            data = pd.read_csv(f"{self.logdir}/{file_name}")
            combined = pd.concat([combined, data], ignore_index=True)

        return combined

    def __del__(self):
        self.stop_test()
        try:
            if self._logEnabled:
                self.stop_logging()
        except AttributeError:
            pass
        self.stop_status()
        self._stop_polling()
        self.testing = False

        # try:
        #     if hasattr(self.devices[1], 'can') and self.devices[1].can:
        #         self.devices[1].can_bus.__del__()
        #         print('CAN shutdown')
        #
        # except (AttributeError, CommLossError):
        #     pass

        try:
            self.devices[1].__del__()
            self.devices[1] = None
        except (ValueError, AttributeError, CommLossError):
            pass
        else:
            logging.info("Device 1 reset")

        try:
            if self.devices[2].can:
                self.devices[2].can_bus.__del__()
            else:
                self.devices[2].__del__()
                self.devices[2] = None
        except (ValueError, AttributeError):
            pass
        else:
            logging.info("Device 2 reset")

        try:
            self.devices[PA] = None
        except (ValueError, AttributeError):
            pass
        else:
            logging.info("PA reset")

    def update(self, SSTime=None, SSTol=None, testTime=None, tPID=None, ss=None):
        self.pid_parameters['ssTime'] = SSTime if SSTime is not None else self.pid_parameters['ssTime']
        self.TestTime = testTime if testTime is not None else self.TestTime
        self.pid_parameters['ssTol'] = SSTol if SSTol is not None else self.pid_parameters['ssTol']
        self.pid_parameters['interval'] = tPID if tPID is not None else self.pid_parameters['interval']
        self.pid_parameters['ss'] = ss if ss is not None else self.pid_parameters['ss']

    def variables(self):
        print(f"Minutes for thermal steady state: {self.pid_parameters['ssTime']}\n"
              f"Minutes for test duration: {self.TestTime}\n"
              f"Steady state tolerance: {self.pid_parameters['ssTol']}\n"
              f"PID update time: {self.pid_parameters['interval']}\n"
              f"PID steady state cutoff enabled: {self.pid_parameters['ss']}")
        return self.pid_parameters['ssTime'], self.pid_parameters['ssTol'], \
            self.TestTime, self.pid_parameters['interval'], self.pid_parameters['ss']

    def start_test(self, interval=1, wait=2, note=''):
        """Test start sequence

        Keyword arguments:
            interval : float, optional. Logging interval (default 1)
            wait : int, optional. Waiting time between logging start and starting device 1 motor (default 2)
            note : str, optional. Logging file notes (default "")
        """
        if self.devices[1]:
            self.start_logging(interval, note)
            # for _ in range(int(wait)):
            self.int_event.wait(wait)
            self.devices[1].start_remote_motor()

    def stop_test(self):
        """Dyno stop sequence"""
        self.stop_pid()
        try:
            asi_brake = False
            if self.devices[2] is not None and isinstance(self.devices[2], ASIController):
                asi_brake = True
            if self.devices[1] is not None:
                if asi_brake:
                    self.devices[2].stop_switch()
                self.devices[1].write("Test mode", 0)
                self.devices[1].stop_remote_motor()
                sleep(0.5)
            if self.devices[2] is not None:
                if isinstance(self.devices[2], AbbAcs800):
                    self.devices[2].stop()
                    self.devices[2].set_torque(0.0)
                    self.curTorque = 0
                    print(f"ASI Brake stopping")
                else:
                    self.devices[2].stop()
        except CommLossError:
            pass

    @property
    def logdir(self):
        return self._logdir

    def is_logging_enabled(self):
        return self._logEnabled

    def hold_current(self, targetI, brake=2, ctm=True):
        """Hold DUT motor current with BRK torque using PID (ThermalMax)

        Parameters:
            targetI : int, required. Target motor current
            brake : str, optional. Braking controller: 1 or 2
            ctm : bool, optional. Whether the function is called from ThermalMax test or not.
                Uses config value if True. Uses pid_parameters if False.
        """
        if ctm:
            kp = float(self.config["ctm_kp_current"])
            ki = float(self.config["ctm_ki_current"])
        else:
            kp = self.pid_parameters['kp']
            ki = self.pid_parameters['ki']

        # set up PID controller with Ks appropriate for holding current
        self.start_pid(self.pid_parameters['interval'], brake, kp, ki, 0,
                       'motor current', targetI, start=self.devices[brake].cur_torque)

        if ctm:
            ninety_start = None
            while (self.pid_enabled and
                   not self.devices[1].in_foldback()):
                try:

                    if ninety_start is None and self.devices[1].read("motor current") >= 0.9 * targetI:
                        ninety_start = datetime.now()

                    sleep(self.pid_parameters['interval'])

                except TestInterrupt:

                    self.stop_pid()
                    self.stop_test()
                    self.stop_logging()
                    return

            self.test_outputs['ninety'] = (datetime.now() - ninety_start).total_seconds()
            self.stop_pid()

    def hold_speed(self, holdspeed, brake=2, wait=1, ctm=True, **kwargs):
        """Hold DUT motor RPM with BRK torque using PID (ThermalMax)

        Parameters:
            holdspeed : int, required. Target motor PRM

            brake : str, optional. Braking controller: 1 or 2

            wait : float, optional. Wait time for steady state in seconds

            ctm : bool, optional. Whether the function is called from ThermalMax test or not.
                Uses config value if True. Uses pid_parameters if False.

            kwargs: dict, opitional. For cyclic applications
                a : list, required if cyclic i.e. [0, 1000]

        """
        if ctm:
            kp = float(self.config["ctm_kp_speed"])
            ki = float(self.config["ctm_ki_speed"])
        else:
            kp = self.pid_parameters['kp']
            ki = self.pid_parameters['ki']

        self.devices[1].remote_speed_mode(speed=holdspeed)
        sleep(wait)

        # if used in cyclic test, change brake accordingly
        if set(['c', 's', 'a', 'b']).issubset(kwargs.keys()):
            if float(kwargs['a'][kwargs['s']]) != 0:
                brake = 2
            elif float(kwargs['b'][kwargs['s']]) != 0:
                brake = 1

        # set up PID controller with Ks appropriate for holding speed as a controller folds back
        self.start_pid(self.pid_parameters['interval'], brake, kp, ki, 0, 'motor rpm',
                       holdspeed - int(self.config["ctm_diff"]), start=self.devices[brake].cur_torque)

        if ctm:
            while self.pid_enabled and self.testing:
                try:

                    sleep(self.pid_parameters['interval'])

                except TestInterrupt:

                    self.stop_pid()
                    self.stop_test()
                    self.stop_logging()
                    return

            print(self.pid_enabled, self.testing)
            self.stop_pid()

    def ramp_torque(self, targetT, brake=2, step=1, interval=0.5):
        """Hold target torque after ramping to it linearly.
        Requires Yokogawa to work

        Keyword arguments:
            targetT : float, required. Target torque to hold at
            brake : int, optional. Braking device (default 2)
            step : int, optional. Ramping step in % torque command (default 1%)
            interval : float, optional. Ramping interval, updates pid_parameter
        """

        if not self.devices[PA]:
            print("Yokogawa not detected. Aborting test!")
            raise TestError("Missing Yokogawa")

        self.pid_parameters['interval'] = interval
        torque = self.devices[PA].getMeasurement("Torque")
        logging.info(f"Torque before ramping: {torque}")

        while abs(torque) > abs(targetT):
            print(f"Ramping to target", end="\r")

            self.curTorque -= step
            self.devices[brake].set_torque(self.curTorque)

            sleep(self.pid_parameters['interval'])

            torque = self.devices[PA].getMeasurement("Torque")

        while abs(torque) < abs(targetT):
            print(f"Ramping to target", end="\r")

            self.curTorque += step
            self.devices[brake].set_torque(self.curTorque)

            sleep(self.pid_parameters['interval'])

            torque = self.devices[PA].getMeasurement("Torque")

        torque = self.devices[PA].getMeasurement("Torque")
        logging.info(f"Torque after ramping: {torque}")

        return torque

    def hold_torque(self, targetT, brake=2, duration=5., step=1, **kwargs):
        """Hold target torque after ramping to it linearly.
        Requires Yokogawa to work

        Keyword arguments:
            targetT : float, required. Target torque to hold at
            brake : int, optional. Braking device (default 2)
            duration : float, optional. Holding duration in minutes (default 5 minutes)
            step : int, optional. Ramping step in % torque command (default 1%)
        """

        self.ramp_torque(targetT, brake, step)

        print(f"Holding target for {duration} minutes")
        self.int_event.wait(duration * 60)

    def reach_torque_speed(self,
                           speed,
                           torque,
                           timeout=60,
                           speed_window=5,
                           torque_window=5,
                           max_temperature=60,
                           device='controller',
                           brake=2,
                           **kwargs):
        """Get DUT (device 1) to target speed and torque window (Temperature Map)

        Keyword arguments:
            speed : int, required. Target motor PRM
            torque : float, required. Target brake torque
            timeout : int, optional.
                DUT considered stalled if unable to reach target within this timeout (default 60s)
            speed_window : float, optional.
                Percentage around target speed to be considered as reaching target speed (default 5%)
            torque_window : float, optional.
                Percentage around target speed to be considered as reaching target speed (default 5%)
            max_temperature : int, optional.
                DUT considered stalled if unable to reach target within this temperature (default 60s)
            device : str, optional.
                max_temperature checks motor or controller temperature (default controller)
            brake : int, optional. Braking controller: 1 or 2 (default 2 [BRK])

        """
        # try:
        #     kp = float(self.config["tempm_kp"])
        #     ki = float(self.config["tempm_ki"])
        # except (ValueError, KeyError):
        #     kp = self.pid_parameters['kp']
        #     ki = self.pid_parameters['ki']

        pre_speed_kp = self.devices[1 if brake == 2 else 2].read("Speed regulator Kp")
        pre_speed_ki = self.devices[1 if brake == 2 else 2].read("Speed regulator Ki")

        self.devices[1 if brake == 2 else 2].remote_speed_mode(speed=speed)
        self.int_event.wait(10)

        # set up PID controller to reach target torque
        # self.start_pid(self.pid_parameters['interval'],
        #                brake, kp, ki, 0,
        #                'Torque', torque)
        start_time = datetime.now()

        curTorque = float(kwargs['minTorque']) + float(kwargs['torqueStep'])
        while (self.testing and curTorque < kwargs['maxTorque'] and
               self.devices[PA].getMeasurement("Torque") < self.torque_limit - 0.5):
            # check timeout
            if (datetime.now() - start_time).total_seconds() > timeout:
                print("TIMEOUT before reaching target")
                break
            # check over temp
            if self.devices[1 if brake == 2 else 2].read(f'{device} temperature') > max_temperature:
                print("OVER TEMP before reaching target")
                break
            # check stalling
            if self.devices[1 if brake == 2 else 2].get_rpm() < 30:
                print("STALL before reaching target")
                to_log = self.getcsvline()
                to_log.append(speed)
                to_log.append(torque)
                self.extra_line(file_name="Temperature Mapping Data", custom=True, data=to_log)
                break
            # check torque
            if self.devices[PA].getMeasurement("Torque") >= torque + torque_window:
                to_log = self.getcsvline()
                to_log.append(speed)
                to_log.append(torque)
                self.extra_line(file_name="Temperature Mapping Data", custom=True, data=to_log)
                break
            # ramp brake to next point
            self.devices[2].ramp_to(target=curTorque, step=10, period=kwargs['settleTime'])
            # log data
            if (speed * (1 - speed_window * 0.01) <=
                    self.devices[1 if brake == 2 else 2].get_rpm() <=
                    speed * (1 + speed_window * 0.01) and
                    torque - torque_window <=
                    self.devices[PA].getMeasurement("Torque") <=
                    torque + torque_window):
                to_log = self.getcsvline()
                to_log.append(speed)
                to_log.append(torque)
                self.extra_line(file_name="Temperature Mapping Data", custom=True, data=to_log)
                break
            curTorque += float(kwargs['torqueStep'])

            # apply alternative speed regulator Kp Ki
            if self.devices[PA].getMeasurement("Torque") >= kwargs['alt_lower'] * torque and \
                    torque <= kwargs['alt_max']:
                if kwargs['alt_kp']:
                    self.devices[1 if brake == 2 else 2].write("Speed regulator Kp", kwargs['alt_kp'])
                if kwargs['alt_ki']:
                    self.devices[1 if brake == 2 else 2].write("Speed regulator Ki", kwargs['alt_ki'])

            sleep(1)

        self.devices[1 if brake == 2 else 2].write("Speed regulator Kp", pre_speed_kp)
        self.devices[1 if brake == 2 else 2].write("Speed regulator Ki", pre_speed_ki)

        # self.stop_pid()
        self.stop_test()

    def rundown(self, *args, **kwargs):
        """Rundown function

        Keyword arguments:
            minTorque : int, required. rundown starting brake torque
            maxTorque : int, required. rundown maximum braking torque
            torqueStep : float, required. rundown loop step
            settleTime : float, required. rundown loop interval
            zoom : bool, optional. enable zoom-in mode
            zoom_lo : float, required if zoom is True. starting torque for zoom-in mode
            zoom_hi : float, required if zoom is True. ending torque for zoom-in mode
        """
        _kw = ['minTorque',
               'maxTorque',
               'torqueStep',
               'settleTime',
               'zoom',
               'zoom_lo',
               'zoom_hi']
        for key, val in zip(_kw, args):
            kwargs[key] = val

        if 'max_efficiency' not in self.test_outputs.keys():
            self.test_outputs['max_efficiency'] = 0
        if 'max_torque' not in self.test_outputs.keys():
            self.test_outputs['max_torque'] = 0

        extra = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')} - RUNDOWN SS Pts"
        self.extra_logging(file_name=extra)

        # ramp torque with constant-time wait, and log SS dataline
        curTorque = int(kwargs['MinTorque'])
        # startRun = datetime.now()
        while (self.testing and curTorque < kwargs['MaxTorque'] and
               self.devices[PA].getMeasurement("Torque") < self.torque_limit - 0.5):
            if kwargs['zoom'] and (self.devices[PA].getMeasurement("Torque") < float(kwargs['zoom_lo']) or
                                      self.devices[PA].getMeasurement("Torque") > float(kwargs['zoom_hi'])):
                self.devices[2].set_torque(target=curTorque)
                sleep(kwargs['settleTime'] * 10)
            else:
                self.devices[2].ramp_to(target=curTorque, step=10, period=kwargs['settleTime'])

            # curSpeed = self.devices[PA].getMeasurement("Motor Speed")  # doesn't consistently represent current RPM
            curSpeed = self.devices[1].get_rpm()

            if curSpeed > 30:
                self.extra_line(file_name=extra)
                curTorque += kwargs['TorqueStep']
            else:
                print('Stalled')
                break
            #### End of Efficiency Map duplicate ###
            try:
                t = self.devices[PA].getMeasurement("Torque")
                if self.test_outputs['max_torque'] < t:
                    self.test_outputs['max_torque'] = t
                me = self.devices[PA].getMeasurement("Motor Efficiency")
                if self.test_outputs['max_efficiency'] < me:
                    self.test_outputs['max_efficiency'] = me
            except (TypeError, AttributeError):
                pass

        self.stop_test()

    def wait_till_stopped(self, device=1):
        if isinstance(self.devices[device], ASIController):
            while self.devices[device].get_rpm() != 0:
                self.int_event.wait(1)

    def maple_tak_production(self, *args, **kwargs):
        """Maple TAK Production test procedure

        Keyword arguments:
            ratio : float, required. Gear ratio between output shaft and Dyno shaft
            brake : str, required. Brake device type (ABB or BAC)
            ramp_step : float, required. Ramp step to reach target torque
            no_load_duration : float, required. Hold time during no load spinning in minutes
            no_laod_speed_command : float, required. Speed command for the test
            max_torque : flaot, required. Target torque for Max. torque step at the output shaft (Nm)
            typical_torque : float, required. Target torque for typical torque step at the output shaft (Nm)
            max_duration : float, required. Hold time during Max. torque step in minutes
            typical_torque_duration : float, required. Hold time during typical torque step in minutes
        """
        self.test_outputs['init_controller_temp'] = self.devices[1].read('controller temperature')
        self.test_outputs['init_motor_temp'] = self.devices[2].read('motor temperature')

        print(f"Step 1: No load both directions at "
              f"{kwargs['no_load_speed_command']} speed "
              f"for {kwargs['no_load_duration']} min each")
        print("Starting Driver")
        self.devices[1].remote_speed_mode(speed=0,
                                          speed_command=kwargs['no_load_speed_command'],
                                          motoring_current=100)
        print(f"Holding for {kwargs['no_load_duration']} minute(s)")
        self.int_event.wait(kwargs['no_load_duration'] * 60)
        self.devices[1].stop_remote_motor()
        # while self.devices[1].get_rpm() > 0:
        #     self.int_event.wait(1)
        self.wait_till_stopped()
        self.int_event.wait(3)

        print("Reversing Driver")
        self.babying(mode='speed', speed_command=-kwargs['no_load_speed_command'])
        # self.devices[1].clear_faults()
        # self.devices[1].remote_speed_mode(speed=0,
        #                                   motoring_current=50,
        #                                   speed_command=-0.5 * kwargs['no_load_speed_command'])
        # sleep(2)
        # self.devices[1].remote_speed_mode(speed=0,
        #                                   motoring_current=100,
        #                                   speed_command=-0.8 * kwargs['no_load_speed_command'])
        # sleep(2)
        # self.devices[1].remote_speed_mode(speed=0,
        #                                   motoring_current=100,
        #                                   speed_command=-1 * kwargs['no_load_speed_command'])
        print(f"Holding for {kwargs['no_load_duration']} minute(s)")
        self.int_event.wait(kwargs['no_load_duration'] * 60)
        self.devices[1].stop_remote_motor()
        # while self.devices[1].get_rpm() > 0:
        #     self.int_event.wait(1)
        self.wait_till_stopped()
        print("Check gearbox temperature")
        print("Cooldown for 1 minute")
        self.int_event.wait(60)

        print(f"Step 2: {kwargs['max_torque']} "
              f"{'forward' if kwargs['brake'] == 'ABB' else 'both'} directions "
              f"for {kwargs['max_duration']} min")
        # Forward direction
        print("Starting Driver")
        self.devices[1].remote_speed_mode(speed=0, motoring_current=100,
                                          speed_command=kwargs['no_load_speed_command'])
        self.int_event.wait(1)
        print("Starting Brake")
        self.devices[2].start()
        self.int_event.wait(3)
        print("Holding torque")
        self.hold_torque(targetT=kwargs['max_torque'] / kwargs['ratio'],
                         duration=kwargs['max_duration'],
                         step=kwargs['ramp_step'])
        print()
        self.stop_test()
        self.curTorque = 0
        self.devices[2].set_torque(0.0)
        # while self.devices[1].get_rpm() > 0:
        #     self.int_event.wait(1)
        self.wait_till_stopped()
        self.int_event.wait(3)
        while self.devices[1].in_foldback():
            self.int_event.wait(3)
        print("Check gearbox temperature")
        print("Cooldown for 1 minute")
        self.int_event.wait(60)

        # Reverse direction
        if kwargs['brake'] == 'BAC':
            print("Reversing Driver")
            self.babying(mode='speed', speed_command=-kwargs['no_load_speed_command'])
            self.int_event.wait(1)
            print("Starting Brake")
            self.devices[2].start()
            self.int_event.wait(3)
            print("Holding torque")
            self.hold_torque(targetT=-kwargs['max_torque'] / kwargs['ratio'],
                             duration=kwargs['max_duration'],
                             step=kwargs['ramp_step'])
            print(f"\n\n\n\n\n\n\n")
            self.stop_test()
            self.curTorque = 0
            self.devices[2].set_torque(0.0)
            # while self.devices[1].get_rpm() > 0:
            #     self.int_event.wait(1)
            self.wait_till_stopped()
            self.int_event.wait(3)
            while self.devices[1].in_foldback():
                self.int_event.wait(3)
            print("Check gearbox temperature")
            print("Cooldown for 1 minute")
            self.int_event.wait(60)

        print(f"Step 3: {kwargs['typical_torque']} Nm @ "
              f"{kwargs['no_load_speed_command']}% speed at "
              f"shaft for {kwargs['typical_torque_duration']} min")
        print("Starting Driver")
        self.devices[1].remote_speed_mode(speed=0,
                                          motoring_current=100,
                                          speed_command=kwargs['no_load_speed_command'])
        self.int_event.wait(1)
        print("Starting Brake")
        self.devices[2].start()
        self.int_event.wait(3)
        self.hold_torque(targetT=kwargs['typical_torque'] / kwargs['ratio'],
                         duration=kwargs['typical_torque_duration'],
                         step=kwargs['ramp_step'])
        print(f"\n\n\n\n\n\n\n")
        self.stop_test()
        print("Check gearbox temperature")
        self.test_outputs['test_result'] = True

    def babying(self, mode='speed', **kwargs):
        """Babying the controller to target speed/torque/current

        Keyword arguments:
            mode : str, required

                Accepted modes :
                    speed - Remote speed mode

                    torque - Remote torque mode

                    speed_torque or torque_speed - Remote torque speed mode

                    current - Open loop current mode

                    voltage - Open loop voltage mode

            speed : int, required if mode is speed or speed_torque
            torque : flaot, required if mode is torque or speed_torque
            speed_command : float, optional if mode is speed or speed_torque
            motoring_current : float, optional. Default to 100
            braking_current : float, optional. For closed loop modes
            current : int, required if mode is current
            modulation : float, required if mode is voltage
            frequency : int, required if mode is current or voltage
            angle : float, optional if mode is current or voltage
        """
        if 'motoring_current' not in kwargs.keys():
            kwargs['motoring_current'] = 100
        # faults = self.devices[1].check_faults()

        if not self.devices[1].remote_faults_handle(mode):
            faults = self.devices[1].check_faults()
            print(f"Registered faults: {faults}")
            if str(faults).find("over current"):
                # print("Assuming Inst. Over-current and trying to baby it...")
                kwargs['motoring_current'] = 0.25 * kwargs['motoring_current']
                if 'speed' in kwargs.keys():
                    kwargs['speed'] = 0.5 * kwargs['speed']
                if 'speed_command' in kwargs.keys():
                    kwargs['speed_command'] = 0.5 * kwargs['speed_command']
                if 'current' in kwargs.keys():
                    kwargs['current'] = 0.5 * kwargs['current']
                if 'torque' in kwargs.keys():
                    kwargs['torque'] = 0.5 * kwargs['torque']
                if 'modulation' in kwargs.keys():
                    kwargs['modulation'] = 0.5 * kwargs['modulation']
                self.devices[1].remote_mode[mode](self.devices[1], **kwargs)
                self.devices[1].clear_faults()

                self.int_event.wait(10)

                if 'speed' in kwargs.keys():
                    kwargs['speed'] = 2 * kwargs['speed']
                if 'speed_command' in kwargs.keys():
                    kwargs['speed_command'] = 2 * kwargs['speed_command']
                if 'current' in kwargs.keys():
                    kwargs['current'] = 2 * kwargs['current']
                if 'torque' in kwargs.keys():
                    kwargs['torque'] = 2 * kwargs['torque']
                if 'modulation' in kwargs.keys():
                    kwargs['modulation'] = 2 * kwargs['modulation']
                self.devices[1].remote_mode[mode](self.devices[1], **kwargs)

                self.int_event.wait(10)

                kwargs['motoring_current'] = 4 * kwargs['motoring_current']
                self.devices[1].remote_mode[mode](self.devices[1], **kwargs)

                faults = self.devices[1].check_faults()
                if faults:
                    if not self.devices[1].remote_faults_handle(mode):
                        print(f"This fault won't clear! Test aborted\n{faults}")
                        return False

    def wait_dut_motor_temp(self):
        """Cooldown helper - Waiting for DUT motor temperature"""
        print(f'Waiting for DUT (A) motor temperature to reach {self.cooldown_parameters["cooldown"]}\u00B0C')
        while self.testing and self.cooldown_parameters['cooldown'] < self.devices[1].read('motor temperature'):
            sleep(1)

    def wait_brk_motor_temp(self):
        """Cooldown helper - Waiting for BRK motor temperature"""
        print(f'Waiting for BRK (DUT B) motor temperature to reach {self.cooldown_parameters["cooldown"]}\u00B0C')
        while self.testing and self.cooldown_parameters['cooldown'] < self.devices[2].read('motor temperature'):
            sleep(1)

    def wait_dut_controller_temp(self):
        """Cooldown helper - Waiting for DUT controller temperature"""
        print(f'Waiting for DUT (A) controller temperature to reach {self.cooldown_parameters["cooldown"]}\u00B0C')
        while self.testing and self.cooldown_parameters['cooldown'] < self.devices[1].read('controller temperature'):
            sleep(1)

    def wait_brk_controller_temp(self):
        """Cooldown helper - Waiting for BRK controller temperature"""
        print(f'Waiting for BRK (DUT B) controller temperature to reach {self.cooldown_parameters["cooldown"]}\u00B0C')
        while self.testing and self.cooldown_parameters['cooldown'] < self.devices[2].read('controller temperature'):
            sleep(1)

    def parse_cooldown(self):
        """Parse cooldown from config"""
        if pd.isna(self.config['cycle_type']) or self.config['cycle_type'] == '':
            self.cooldown_parameters['cooldown_type'] = None
            return
        self.cooldown_parameters['cooldown_type'] = int(self.config['cycle_type'])
        if pd.isna(self.config['cycle_cd_driver']):
            self.cooldown_parameters['cd_on_driver'] = False
        else:
            self.cooldown_parameters['cd_on_driver'] = bool(self.config['cycle_cd_driver'])
        if self.cooldown_parameters['cooldown_type'] == 0:
            self.cooldown_parameters['cooldown'] = self.config['cycle_cd']
            if pd.isna(self.cooldown_parameters['cooldown']):
                self.cooldown_parameters['cooldown'] = 0
            else:
                self.cooldown_parameters['cooldown'] = float(self.cooldown_parameters['cooldown'])
        elif self.cooldown_parameters['cooldown_type'] == 1:
            self.cooldown_parameters['cooldown'] = self.config['cycle_dut_motor_temp']
            if pd.isna(self.cooldown_parameters['cooldown']):
                self.cooldown_parameters['cooldown'] = self.devices[1].read('motor temperature') + 10
            else:
                self.cooldown_parameters['cooldown'] = int(self.cooldown_parameters['cooldown'])
        elif self.cooldown_parameters['cooldown_type'] == 2:
            self.cooldown_parameters['cooldown'] = self.config['cycle_dut_temp']
            if pd.isna(self.cooldown_parameters['cooldown']):
                self.cooldown_parameters['cooldown'] = self.devices[1].read('controller temperature') + 10
            else:
                self.cooldown_parameters['cooldown'] = int(self.cooldown_parameters['cooldown'])
        elif self.cooldown_parameters['cooldown_type'] == 3:
            self.cooldown_parameters['cooldown'] = self.config['cycle_brk_motor_temp']
            if pd.isna(self.cooldown_parameters['cooldown']):
                self.cooldown_parameters['cooldown'] = self.devices[2].read('motor temperature') + 10
            else:
                self.cooldown_parameters['cooldown'] = int(self.cooldown_parameters['cooldown'])
        elif self.cooldown_parameters['cooldown_type'] == 4:
            self.cooldown_parameters['cooldown'] = self.config['cycle_brk_temp']
            if pd.isna(self.cooldown_parameters['cooldown']):
                self.cooldown_parameters['cooldown'] = self.devices[2].read('controller temperature') + 10
            else:
                self.cooldown_parameters['cooldown'] = int(self.cooldown_parameters['cooldown'])
        else:
            print('Bad cycle type! Will only run 1 iteration')

    def handle_cooldown(self):
        """Handing cooldown based on cooldown_parameters and driver"""
        if self.cooldown_parameters['cooldown_type'] is None:
            return
        if self.devices[1]:
            self.devices[1].stop()
        if self.devices[2]:
            self.devices[2].stop()

        # Cooldown between speeds
        if self.cooldown_parameters['cooldown_type'] == 0:
            try:
                if self.cooldown_parameters['cooldown'] > 1:  # Time
                    for t in range(int(self.cooldown_parameters['cooldown'])):
                        print(f"{self.cooldown_parameters['cooldown'] - t:.1f} min left")
                        self.int_event.wait(60)
                elif self.cooldown_parameters['cooldown'] > 0:
                    self.int_event.wait(int(self.cooldown_parameters['cooldown'] * 60))
            except (TestInterrupt, TestError):
                return
        elif self.cooldown_parameters['cooldown_type'] == 1:
            if self.cooldown_parameters['cd_on_driver']:
                if self.driver == 1 and self.devices[1]:
                    self.wait_dut_motor_temp()
                elif self.driver == 2 and self.devices[2]:
                    self.wait_brk_motor_temp()
            else:
                self.wait_dut_motor_temp()
        elif self.cooldown_parameters['cooldown_type'] == 2:
            if self.cooldown_parameters['cd_on_driver']:
                if self.driver == 1 and self.devices[1]:
                    self.wait_dut_controller_temp()
                elif self.driver == 2 and self.devices[2]:
                    self.wait_brk_controller_temp()
            else:
                self.wait_dut_controller_temp()
        elif self.cooldown_parameters['cooldown_type'] == 3:
            if self.cooldown_parameters['cd_on_driver']:
                if self.driver == 1 and self.devices[1]:
                    self.wait_dut_motor_temp()
                elif self.driver == 2 and self.devices[2]:
                    self.wait_brk_motor_temp()
            else:
                self.wait_brk_motor_temp()
        elif self.cooldown_parameters['cooldown_type'] == 4:
            if self.cooldown_parameters['cd_on_driver']:
                if self.driver == 1 and self.devices[1]:
                    self.wait_dut_controller_temp()
                elif self.driver == 2 and self.devices[2]:
                    self.wait_brk_controller_temp()
            else:
                self.wait_brk_controller_temp()

    def cycle(
        self, 
        total_cycles : int,
        total_steps : int,
        *args, 
        **kwargs
    ):
        """cyclic function

        Keyword arguments:
            total_cycles : int, required. total # of cycles
            total_steps : int, required. total # of steps per cycle
            foldback : bool, optional. whether controller foldback overwrites hold time.
                Default value : False
            foldback_driver : bool, optional. Whether foldback is based on driving controller.
                Default value : False
            cd_in_step : bool, optional. If cooldown happens in between steps
            cd_on_driver : bool, optional. If cooldown is based on driving controller or fixed controller.
                Default value : False
            ramp_command : Callable or None, required. Ramping up/down action in each step.
                Default value : None
            hold_setup : Callable or None, optional. Sets up hold function, excuted before while loop.
                Default value : None
            hold_condition : Callable or None, optional. The condition to keep holding loop if true
                or breaks out of it if false.
                Excuted before hold_command but after foldback checks.
                Default value : None
                Returns : bool
            hold_command : Callable or None, required.
                Cyclic action that takes place between ramping in each step.
                Need to update driver if foldback_driver is True.
                Default value : None
            watchdog : Thread or None, optional. Whether the controllers are driven thru a watchdog.
                Default value : None
            steps : list, required for hold times. Raises TestError if steps is missing
            ramps : list, required if ramp_command is not None
            others : optional. Test specific kwargs
        """
        _kw = ['foldback',
               'foldback_driver',
               'cd_in_step',
               'cd_on_driver',
               'ramp_command',
               'hold_setup',
               'hold_condition',
               'hold_command',
               'watchdog',
               'steps',
               'ramps']
        for key, val in zip(_kw, args):
            kwargs[key] = val

        self.test_outputs['total_cycles'] = total_cycles
        self.test_outputs['total_steps'] = total_steps

        if 'foldback' not in kwargs.keys():
            kwargs['foldback'] = False
        if 'foldback_driver' not in kwargs.keys():
            kwargs['foldback_driver'] = False
        if 'cd_in_step' not in kwargs.keys():
            kwargs['cd_in_step'] = False
        if 'cd_on_driver' not in kwargs.keys():
            self.cooldown_parameters['cd_on_driver'] = False
        else:
            self.driver = 1
        if 'ramp_command' not in kwargs.keys():
            kwargs['ramp_command'] = None
        if 'hold_setup' not in kwargs.keys():
            kwargs['hold_setup'] = None
        if 'hold_command' not in kwargs.keys():
            kwargs['hold_command'] = None
        if 'watchdog' not in kwargs.keys() and not bool(self.config['watchdog']):
            kwargs['watchdog'] = None
        if 'steps' not in kwargs.keys():
            raise TestError('Missing Critical Parameter: "steps" - type: list')
        if 'ramps' not in kwargs.keys():
            kwargs['ramp_command'] = None
            logging.info('Missing Critical Parameter: "ramps" not found! "ramp_command" ignored!')

        current_cycle = 0
        self.test_outputs['current_cycle'] = current_cycle
        current_step = 0
        self.test_outputs['current_step'] = current_step

        def log_step():
            print('\n---------------------\n')
            result_file = self.logdir / "cyclic result.txt"
            with open(result_file, "a") as txt:
                txt.write(f'Cycle {current_cycle}/{total_cycles}\n')
                print(f'Cycle {current_cycle}/{total_cycles}\n')

                txt.write(f'Cycle started @ {cycle_start}\n')
                print(f'Cycle started @ {cycle_start}\n')

                txt.write(f'Step {current_step}/{total_steps}\n')
                print(f'Step {current_step}/{total_steps}')

                try:
                    txt.write(f'Speed: {float(kwargs["a"][s])} - {float(kwargs["b"][s])}\n')
                except KeyError:
                    pass

                if self.config['test'] not in ['Temperature Map', 'Efficiency Table']:
                    try:
                        txt.write(f'Speed: {float(kwargs["speeds"][s])}\n')
                    except KeyError:
                        pass
                else:
                    try:
                        txt.write(f'Speed: {float(kwargs["speeds"][c])}\n')
                    except KeyError:
                        pass

                txt.write(f'Step started @ {step_start}\n')
                print(f'Step started @ {step_start}\n')

                result = f"Duration: {(datetime.now() - startTime).total_seconds() / 60:.1f} minutes\n"
                txt.write(result)
                print(result)

                try:
                    faults = self.devices[1].check_faults()
                    if len(faults) == 0:
                        result = f"No warnings or faults\n"
                    else:
                        result = f"Faults: {faults}\n"
                    print(result)
                    txt.write(f"{result}\n\n")
                except AttributeError:
                    pass

                # if self.test_outputs:
                #     for key in self.test_outputs:
                #         result = f"{key}: {self.test_outputs[key]}\n"
                #         txt.write(result)
                #         print(result)


        self.parse_cooldown()

        if kwargs['foldback']:
            print("Foldback overwrite hold time is ENABLED")
        if kwargs['foldback_driver']:
            print("Foldback based on driving controller")
        if kwargs['cd_in_step']:
            print("Cooldown between steps is ENABLED")
        if self.cooldown_parameters['cd_on_driver']:
            print("Cooldown based on driving controller")

        startTime = datetime.now()

        try:
            for c in range(total_cycles):
                if not self.testing:
                    return
                current_cycle = c + 1
                self.test_outputs['current_cycle'] = current_cycle
                cycle_start = datetime.now()
                print(f"-------------------\n"
                      f"{cycle_start} - Starting cycle {current_cycle}/{total_cycles}")

                for s in range(total_steps):
                    if not self.testing:
                        return
                    current_step = s + 1
                    self.test_outputs['current_step'] = current_step
                    step_start = datetime.now()
                    print(f"-------------------\n"
                          f"{step_start} - Starting step {current_step}/{total_steps}")

                    if 'ramp_command' in kwargs.keys():
                        # ramping up
                        ramp_start = datetime.now()
                        print(f'-------------------\n'
                              f'{ramp_start} - Ramping up over {int(kwargs["ramps"][s])} seconds\n')
                        kwargs['ramp_command'](ramp='up', ramp_start=ramp_start, cycle=c, step=s, **kwargs)
                        logging.info(f'Actual ramp duration: '
                                     f'{(datetime.now() - ramp_start).total_seconds():.1f} seconds\n')

                    if 'hold_command' in kwargs.keys() or 'hold_setup' in kwargs.keys():
                        # sets up holding loop or using your own loop
                        setup_start = datetime.now()
                        if 'hold_setup' in kwargs.keys():
                            kwargs['hold_setup'](setup_start=setup_start, cycle=c, step=s, **kwargs)

                        # Hold for step duration
                        hold_start = datetime.now()
                        print(f'-------------------\n'
                              f'{hold_start} - Holding: {int(kwargs["steps"][s])} seconds\n')

                        while self.testing and (datetime.now() - hold_start).total_seconds() < int(kwargs['steps'][s]):
                            # Foldback overwrite
                            if kwargs['foldback']:
                                if kwargs['foldback_driver']:  # Driver based foldback
                                    if self.driver == 1:
                                        if self.devices[1] and self.devices[1].in_foldback():
                                            print("Device 1 in foldback")
                                            print(self.devices[1].check_faults())
                                            break
                                    elif self.driver == 2:
                                        if isinstance(self.devices[2], ASIController) and self.devices[2].in_foldback():
                                            print("Device 2 in foldback")
                                            print(self.devices[2].check_faults())
                                            break
                                else:  # Any foldback
                                    if self.devices[1]:
                                        if self.devices[1].in_foldback():
                                            print("Device 1 in foldback")
                                            print(self.devices[1].check_faults())
                                            break
                                    if self.devices[2]:
                                        if self.devices[2].in_foldback():
                                            print("Device 2 in foldback")
                                            print(self.devices[2].check_faults())
                                            break

                            if 'hold_condition' in kwargs.keys():
                                if kwargs['hold_condition'](hold_start=hold_start, cycle=c, step=s, **kwargs):
                                    pass
                                else:
                                    break

                            sleep(1)

                            if 'hold_command' in kwargs.keys():
                                kwargs['hold_command'](hold_start=hold_start, cycle=c, step=s, **kwargs)

                        if self.pid_enabled:
                            self.stop_pid()
                        if self.watchdog:
                            self.stop_watchdog()

                        logging.info(f'Actual hold duration: '
                                     f'{(datetime.now() - hold_start).total_seconds():.1f} seconds\n')

                    if 'ramp_command' in kwargs.keys():
                        # ramping down
                        ramp_start = datetime.now()
                        print(f'-------------------\n'
                              f'{ramp_start} - Ramping down over {int(kwargs["ramps"][s])} seconds\n')
                        kwargs['ramp_command'](ramp='down', ramp_start=ramp_start, total_steps=total_steps,
                                               cycle=c, step=s, **kwargs)
                        logging.info(f'Actual ramp duration: '
                                     f'{(datetime.now() - ramp_start).total_seconds():.1f} seconds\n')

                    # Cooldown in between steps
                    if kwargs['cd_in_step'] and current_step < total_steps and self.testing:
                        print(f'-------------------\n'
                              f'{datetime.now()} - Cooldown between steps\n')
                        self.handle_cooldown()

                    log_step()

                if current_cycle < total_cycles and self.testing:
                    print(f'-------------------\n'
                          f'{datetime.now()} - Cooldown between cycles\n')
                    self.handle_cooldown()
                    if current_cycle == 1:
                        try:
                            self.plot_cycle('First Cycle')
                        except (pd.errors.ParserError, KeyError):
                            pass

        except TestInterrupt:
            self.test_outputs['cycle_duration'] = (datetime.now() - cycle_start).total_seconds()
            return

        self.test_outputs['cycle_duration'] = (datetime.now() - cycle_start).total_seconds()

    def dyno_speed_ramp(self, dut=2000., brk=1000., duration=10.):
        """Brings dyno up to speed

        Arguments:
            dut : float, optional. Target Device 1 RPM (default 2000)
            brk : float, optional. Target Device 2 RPM (default 1000)
            duration : float, optional. Ramp duration in seconds (default 10)
        """
        # no ramping when duration <= 0
        if duration <= 0 and dut == 0 and brk == 0: # Stop test if all values are 0
            self.stop_test()
            return
        elif duration <= 0 and dut == 0: # Stop both motor and restart BRK if dut is 0
            if self.devices[1]:
                self.stop_test()
            if self.devices[2]:
                self.devices[2].remote_speed_mode(speed=brk, speed_command=0)
            return
        elif duration <= 0 and brk == 0: # Stop both motor and restart DUT if brk is 0
            if self.devices[2]:
                self.top_test()
            if self.devices[1]:
                self.devices[1].remote_speed_mode(speed=dut, speed_command=0)
            return
        elif duration <= 0: # Run both motors at desired speed if not 0
            if self.devices[1]:
                self.devices[1].remote_speed_mode(speed=dut, speed_command=0, braking_current=10)
            if self.devices[2]:
                self.devices[1].remote_speed_mode(speed=brk, speed_command=0, braking_current=10)
            return

        # Ramping
        try:
            if self.devices[1]:
                step_a = (dut - self.devices[1].get_rpm()) / 10
                # step_a = (dut) / 10
            if self.devices[2]:
                step_b = (brk - self.devices[2].get_rpm()) / 10
                # step_b = (brk) / 10
            for i in range(10):
                if self.devices[1]:
                    print('Device 1')
                    self.devices[1].remote_speed_mode(speed=dut - (9 - i) * step_a, speed_command=0,
                                               braking_current=0 if dut == 0 else 50,
                                               motoring_current=20 if dut == 0 else 100)
                if self.devices[2]:
                    print('Device 2')
                    self.devices[2].remote_speed_mode(speed=brk - (9 - i) * step_b, speed_command=0,
                                               braking_current=0 if brk == 0 else 50,
                                               motoring_current=20 if brk == 0 else 100)
                sleep(duration / 10)
                if not self.testing:
                    self.stop_test()
                    return
        except AttributeError:
            return
        except CommLossError:
            self.testing = False
            return

    def cyclic_ramp(self, **kwargs):
        """Default cyclic ramp function to bring dyno up to speed.
        Uses dyno_speed_ramp.

        Keyword arguments:
            ramp : str, required. Indicates ramping up or down. Accepts up or down
            a : list, required. List of RPMs for Device 1
            b : list, required. List of RPMs for Device 2
            ramps : list, required. List of ramp durations
            step : int, required. Current step in the cyclic test
            total_steps : int, required. Total # of steps
        """
        if kwargs['ramp'] == 'up':
            self.dyno_speed_ramp(float(kwargs['a'][kwargs['step']]),
                                 float(kwargs['b'][kwargs['step']]),
                                 float(kwargs["ramps"][kwargs["step"]]))
        elif kwargs['ramp'] == 'down':
            if kwargs["step"] + 1 == kwargs['total_steps']:
                if self.cooldown_parameters['cooldown_type'] is None:
                    self.dyno_speed_ramp(float(kwargs['a'][0]),
                                         float(kwargs['b'][0]),
                                         float(kwargs["ramps"][kwargs["step"]]))
                else:
                    self.dyno_speed_ramp(0, 0, float(kwargs["ramps"][kwargs["step"]]))
            else:
                self.dyno_speed_ramp(float(kwargs['a'][kwargs['step']]),
                                     float(kwargs['b'][kwargs['step']]),
                                     float(kwargs["ramps"][kwargs["step"]]))

    def cyclic_hold_setup(self, **kwargs):
        """
        Default cyclic hold setup to bring BAC2BAC dyno up to speed.
        This function determines driver in cyclic tests

        Keyword arguments:
            step : int, required. Current step in cyclic test
            a : list, required. List of RPMs for Device 1
            b : list, required. List of RPMs for Device 2
            motoring_a : list, required. List of motoring current for Device 1
            motoring_b : list, required. List of motoring current for Device 2
            regen_a : list, required. List of braking current for Device 1
            regen_b : list, required. List of braking current for Device 2
            ki : list, optional. Used to set up hold_speed
            kp : list, optional. Used to set up hold_speed
        """
        watchdog = self.config['watchdog']
        if pd.isna(watchdog):
            self.watchdog = None
        else:
            if bool(watchdog):
                self.watchdog = Thread(target=self._watchdog_thread)
                self.watchdog_enabled = True
            else:
                self.watchdog = None

        if self.devices[1] and float(kwargs['a'][kwargs['step']]) != 0:
            self.driver = 1
            a_rated_current = float(self.devices[1].read("Rated motor current"))
            self.devices[1].remote_speed_mode(speed=float(kwargs['a'][kwargs['step']]),
                                              motoring_current=float(
                                                  kwargs['motoring_a'][kwargs['step']]) / a_rated_current * 100,
                                              braking_current=float(
                                                  kwargs['regen_a'][kwargs['step']]) / a_rated_current * 100,
                                              watchdog=self.watchdog)
            if self.devices[2]:
                self.int_event.wait(3)
                if abs(self.devices[1].get_rpm()) > abs(0.25 * float(kwargs['a'][kwargs['step']])):
                    self.devices[2].start(2)
                else:
                    self.testing = False
                    raise TestError("Device 1 RPM out of safety range of target holding RPM")

        elif isinstance(self.devices[2], ASIController) and float(kwargs['b'][kwargs['step']]) != 0:
            self.driver = 2
            b_rated_current = float(self.devices[2].read("Rated motor current"))
            self.devices[2].remote_speed_mode(speed=float(kwargs['b'][kwargs['step']]),
                                              motoring_current=float(
                                                  kwargs['motoring_b'][kwargs['step']]) / b_rated_current * 100,
                                              braking_current=float(
                                                  kwargs['regen_b'][kwargs['step']]) / b_rated_current * 100,
                                              watchdog=self.watchdog)
            if self.devices[1]:
                self.int_event.wait(3)
                if abs(self.devices[2].get_rpm()) > abs(0.25 * float(kwargs['b'][kwargs['step']])):
                    self.devices[1].start(2)
                else:
                    self.testing = False
                    raise TestError("Device 2 RPM out of safety range of target holding RPM")

        # if isinstance(kwargs['ki'], list) and isinstance(kwargs['kp'], list):
        if 'ki' in kwargs.keys() and 'kp' in kwargs.keys():
            if kwargs['ki'] and kwargs['kp']:
                self.pid_parameters['ki'] = float(kwargs['ki'][kwargs['step']])
                self.pid_parameters['kp'] = float(kwargs['kp'][kwargs['step']])

                set_point = 0
                if float(kwargs['a'][kwargs['step']]) != 0:
                    set_point = ((abs(int(kwargs['a'][kwargs['step']])) / int(kwargs['a'][kwargs['step']])) *   # sign
                                 (abs(int(kwargs['a'][kwargs['step']]))))    # value
                elif float(kwargs['b'][kwargs['step']]) != 0:
                    set_point = ((abs(int(kwargs['b'][kwargs['step']])) / int(kwargs['b'][kwargs['step']])) *   # sign
                                 (abs(int(kwargs['b'][kwargs['step']]))))    # value

                self.hold_speed(set_point, ctm=False, **kwargs)

    def cyclic_hold_timeout(self, **kwargs):
        """
        Default cyclic hold command handling timeout (BAC2BAC)

        Keyword arguemnts:
            hold_start : datetime, required.
            steps : list, required. List of hold durations, passed on from cycle
            step : int, required. Current step, passed on from cycle
            raise_error : bool, optional. Whether timeout raises TestError or logs as warning
        """
        if (datetime.now() - kwargs['hold_start']).total_seconds() >= int(kwargs['steps'][kwargs['step']]):
            if 'raise_error' in kwargs.keys() and kwargs['raise_error']:
                raise TestError(f"Test Timeout: Cycle {kwargs['cycle']} Step {kwargs['step']} timed out")
            else:
                logging.warning(f"Cycle {kwargs['cycle']} Step {kwargs['step']} timed out")

    def cyclic_hold_condition(self, **kwargs):
        """
        Default cyclic hold condition, returns True if condition is met, False if condition not met

        Keyword arguments:
            hold_condition_driver : str, optional.
                Accepts 1 or 2 or PA, enabling driver specific condition check
            upper_limit : float, optional. Upper limit for condition check.
                Required if parameter needs to be below a value.
                Can use both upper_limit and lower_limit
            lower_limit : float, optional. Lower limit for condition check.
                Required if parameter needs to be greater than a value.
                Can use both upper_limit and lower_limit
            hold_condition_param : str, required. Parameter name for condition check
        """
        if 'hold_condition_driver' in kwargs.keys():  # Driver specific condition
            if kwargs['hold_condition_driver'] == 1:
                if self.devices[1]:
                    if 'upper_limit' in kwargs.keys() and 'lower_limit' in kwargs.keys():
                        if kwargs['upper_limit'] >= self.devices[1].read(
                                kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                            return True
                        else:
                            return False
                    if 'upper_limit' in kwargs.keys():
                        if kwargs['upper_limit'] >= self.devices[1].read(kwargs['hold_condition_param']):
                            return True
                        else:
                            return False
                    if 'lower_limit' in kwargs.keys():
                        if self.devices[1].read(kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                            return True
                        else:
                            return False
            elif kwargs['hold_condition_driver'] == 2:
                if self.devices[2] and isinstance(self.devices[2], ASIController):
                    if 'upper_limit' in kwargs.keys() and 'lower_limit' in kwargs.keys():
                        if kwargs['upper_limit'] >= self.devices[2].read(
                                kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                            return True
                        else:
                            return False
                    if 'upper_limit' in kwargs.keys():
                        if kwargs['upper_limit'] >= self.devices[2].read(kwargs['hold_condition_param']):
                            return True
                        else:
                            return False
                    if 'lower_limit' in kwargs.keys():
                        if self.devices[2].read(kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                            return True
                        else:
                            return False
            elif kwargs['hold_condition_driver'] == PA:
                if self.devices[PA] and isinstance(self.devices[PA], Yokogawa_WT1806):
                    if 'upper_limit' in kwargs.keys() and 'lower_limit' in kwargs.keys():
                        if kwargs['upper_limit'] >= self.devices[PA].getMeasurement(
                                kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                            return True
                        else:
                            return False
                    if 'upper_limit' in kwargs.keys():
                        if kwargs['upper_limit'] >= self.devices[PA].getMeasurement(kwargs['hold_condition_param']):
                            return True
                        else:
                            return False
                    if 'lower_limit' in kwargs.keys():
                        if self.devices[PA].getMeasurement(kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                            return True
                        else:
                            return False
        else:  # Any condition
            if self.devices[1]:
                if 'upper_limit' in kwargs.keys() and 'lower_limit' in kwargs.keys():
                    if kwargs['upper_limit'] >= self.devices[1].read(
                            kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                        return True
                    else:
                        return False
                if 'upper_limit' in kwargs.keys():
                    if kwargs['upper_limit'] >= self.devices[1].read(kwargs['hold_condition_param']):
                        return True
                    else:
                        return False
                if 'lower_limit' in kwargs.keys():
                    if self.devices[1].read(kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                        return True
                    else:
                        return False
            if self.devices[2] and isinstance(self.devices[2], ASIController):
                if 'upper_limit' in kwargs.keys() and 'lower_limit' in kwargs.keys():
                    if kwargs['upper_limit'] >= self.devices[2].read(
                            kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                        return True
                    else:
                        return False
                if 'upper_limit' in kwargs.keys():
                    if kwargs['upper_limit'] >= self.devices[2].read(kwargs['hold_condition_param']):
                        return True
                    else:
                        return False
                if 'lower_limit' in kwargs.keys():
                    if self.devices[2].read(kwargs['hold_condition_param']) >= kwargs['lower_limit']:
                        return True
                    else:
                        return False

    def efficiency_map_step(self, **kwargs):
        """Efficiency map setup_command. An adjusted rundown function

        Keyword arguements:
            speeds : list, required. List of RPMs for efficiency mapping
            settleTime : flaot, required. Rundown interval
            MinTorque : list, required. Starting torque % at start of rundown
            MaxTorque : list, required. Max torque % when stopping rundown
            TorqueStep : list, required. Torque % increment for rundown
            motoring : list, required. Motoring current for each rundown
        """
        # Reset return parameters
        extra = f"{kwargs['speeds'][kwargs['step']]}"
        header = self.getcsvline(getnames=True)
        header.append('Efficiency Map Flag')
        self.extra_logging(file_name=extra, header=header)

        self.test_outputs['max_torque'] = 0
        self.test_outputs['max_efficiency'] = 0
        rated_motor_current = self.devices[1].read('Rated motor current')

        print(f"-------------------\n{datetime.now()} - "
              f"Starting efficiency map step {kwargs['step']}/{len(kwargs['speeds'])}")
        print(f"Testing speed: {int(kwargs['speeds'][kwargs['step']])} rpm")

        def efficiency_map_flag(torque):
            torque_slope = (self.test_outputs['max_torque'] - torque) / kwargs['settleTime']
            if self.devices[1].get_rpm() > int(kwargs['speeds'][kwargs['step']]) - 40:  # Before motor slows down
                return 1
            elif self.devices[1].log_params['motor current'].Value <= rated_motor_current - 2:  # Motor on boundary curve
                return 2
            elif self.devices[1].log_params['motor current'].Value > rated_motor_current - 2:
                if torque_slope < 1.5 / kwargs['settleTime']:
                    return 3
                else:
                    return 2
            else:
                return 0

        self.devices[1].remote_speed_mode(speed=int(kwargs['speeds'][kwargs['step']]),
                                   motoring_current=kwargs['motoring'][kwargs['step']])
        self.int_event.wait(2)

        self.devices[2].start()
        self.devices[2].set_torque(0)
        self.int_event.wait(2)

        self.babying('speed', speed=int(kwargs['speeds'][kwargs['step']]),
                     motoring_current=kwargs['motoring'][kwargs['step']])

        # settle after initial speed command
        self.int_event.wait(5)

        # ramp torque with constant-time wait, and log SS dataline
        curTorque = int(kwargs['MinTorque'][kwargs['step']])

        while (curTorque < kwargs['MaxTorque'][kwargs['step']] and
               self.devices[PA].getMeasurement("Torque") < self.torque_limit - 0.5):
            self.devices[2].ramp_to(target=curTorque, step=10, period=kwargs['settleTime'])

            curSpeed = self.devices[1].get_rpm()
            pre_torque = self.test_outputs['max_torque']
            try:
                t = self.devices[PA].getMeasurement("Torque")
                if self.test_outputs['max_torque'] < t:
                    self.test_outputs['max_torque'] = t
                me = self.devices[PA].getMeasurement("Motor Efficiency")
                if self.test_outputs['max_efficiency'] < me < 100:
                    self.test_outputs['max_efficiency'] = me
            except (TypeError, AttributeError):
                pass

            if curSpeed > (50 if int(kwargs['speeds'][kwargs['step']]) >= 1000 else 10):
                sleep(kwargs['settleTime'])
                to_log = self.getcsvline()
                to_log.append(efficiency_map_flag(pre_torque))
                self.extra_line(file_name=extra, custom=True, data=to_log)
                curTorque += kwargs['TorqueStep'][kwargs['step']]
            else:
                break

        self.stop_test()

    def temperature_map_step(self, **kwargs):
        """Efficiency map setup_command. An adjusted rundown function

        Keyword arguments:
            speeds : list, required. List of target speeds i.e. [3000, 2500, ... , 500]
            torques : list, required. List of target torques i.e. [5, 5.5, ... , 0.5]
            cycle : int, required. Current cycle in the test, used for speeds
            step : int, required. Current step in the cycle, used for torques
            timeout : int, optional.
                DUT considered stalled if unable to reach target within this timeout (default 60s)
            speed_window : float, optional.
                Percentage around target speed to be considered as reaching target speed (default 5%)
            torque_window : float, optional.
                Percentage around target speed to be considered as reaching target speed (default 5%)
            max_temperature : int, optional.
                DUT considered stalled if unable to reach target within this temperature (default 60s)
            device : str, optional.
                max_temperature checks motor or controller temperature (default controller)
            brake : int, optional. Braking controller: 1 or 2 (default 2 [BRK])
        """
        # Reset return parameters
        extra = "Temperature Mapping Data"
        header = self.getcsvline(getnames=True)
        header.append('Target Speed')
        header.append('Target Torque')
        self.extra_logging(file_name=extra, header=header)

        print(f"-------------------\n{datetime.now()} - "
              f"Starting {kwargs['device']} temperature map step {kwargs['step']}/{len(kwargs['torques'])}")
        print(f"Target speed: {int(kwargs['speeds'][kwargs['cycle']])} rpm")
        print(f"Target torque: {float(kwargs['torques'][kwargs['step']])} Nm")

        self.devices[1 if kwargs['brake'] == 2 else 2].remote_speed_mode(
            speed=int(kwargs['speeds'][kwargs['cycle']]),
            motoring_current=100)
        self.int_event.wait(10)

        self.devices[kwargs['brake']].start()
        self.devices[kwargs['brake']].set_torque(0)
        self.int_event.wait(2)

        self.babying('speed', speed=int(kwargs['speeds'][kwargs['cycle']]),
                     motoring_current=100)

        # settle after initial speed command
        self.int_event.wait(5)

        self.devices[kwargs['brake']].set_torque(float(kwargs['minTorque']))
        self.int_event.wait(5)

        self.reach_torque_speed(speed=int(kwargs['speeds'][kwargs['cycle']]),
                                  torque=float(kwargs['torques'][kwargs['step']]),
                                  **kwargs)

        self.stop_test()

    def efficiency_table_ramp(self, **kwargs):
        """
        Function to bring dyno up to speed using ABB speed mode
        ABB has really good PID for speed, so no need to actually ramp RPM with ABB
        RPM only changes per cycle

        Keyword arguments:
            ramp_start : datetime, required. Used for timeout
            ramp : str, required. Indicates ramping up or down. Accepts up or down
            speeds : list, required. List of target speeds i.e. [500, 1000, ... , 2540]
            ss_rpm : float, required. Delta to determine dyno is at steady state RPM
            cycle : int, required. Current cycle in the test, used for speeds
            timeout : int, required.
                DUT considered stalled if unable to reach target steady state RPM
            reset : bool, required
        """

        if not isinstance(self.devices[2], AbbAcs800):
            print("TEST ERROR: This test requires ABB in speed mode. ABB not detected as device 2 (BRK)")
            raise TestError("Missing ABB")
        
        if not isinstance(self.devices[PA], Yokogawa_WT1806):
            print("TEST ERROR: This test requires Yokogawa as power analyzer")
            raise TestError("Missing Yokogawa")

        target_rpm = int(kwargs['speeds'][kwargs['cycle']])
        window = kwargs['ss_rpm']
        timeout = kwargs['timeout']
        start_time = kwargs['ramp_start']
        if self.devices[2].mode == 'torque':
            self.devices[2].speed_mode()
            self.devices[2].set_torque(0)
            self.devices[2].set_limits('b')
            self.devices[2].set_abb_direction('b')
            self.int_event.wait(1)
            self.devices[2].start()

        if kwargs['ramp'] == 'up':
            self.devices[2].set_rpm(target_rpm)

            while ((datetime.now() - start_time).total_seconds() < timeout and self.testing and 
                   (self.devices[PA].getMeasurement('Motor Speed') < abs(target_rpm) - window or 
                    self.devices[PA].getMeasurement('Motor Speed') > abs(target_rpm) + window)):
                self.int_event.wait(1)

            if not self.testing: 
                print("Test interrupted")
                raise TestInterrupt("Interrupted at ramp up")

            if (datetime.now() - start_time).total_seconds() >= timeout:
                print(f"TIMEOUT: before reaching target RPM {abs(target_rpm)}")
                raise TestError("TIMEOUT: Dyno failed to reach target RPM")
            
            if abs(target_rpm) - window < self.devices[PA].getMeasurement('Motor Speed') < abs(target_rpm) + window:
                print(f"Target RPM reached after {(datetime.now() - start_time).total_seconds()} seconds")
            else:
                print(f"UNKNOWN ERROR: Dyno failed to reach target RPM {abs(target_rpm)}")
                raise TestError("UNKNOWN ERROR: Dyno failed to reach target RPM")
        
        else:
            if kwargs['reset']:
                self.devices[1].set_torque(0)
            if kwargs['step'] + 1 == len(kwargs['apks']):  # if this is the ramp down for the last step
                self.devices[1].stop()
        
    def efficiency_table_setup(self, **kwargs):
        """
        Function to set up each individual data point
        Checks if temperature is within window
        Determine test parameters
        Dyno should be in steady state at the end of the function
        Resets steady state sample count

        Keyword arguments:
            setup_start : datetime, required. For timeout
            cycle : int, required. current cycle #
            step : int, required. current step #
            apks : list, required. To determine brake torque %
            device : str, required. Efficiency Table target device. Accepts "motor" or "controller"
            timeout : int, required. 
                DUT considered stalled if unable to reach target steady state RPM and current
            ss_rpm : int, required. RPM delta to determine steady state
            ss_current : float, required. Motor current delta to determine steady state
            temp_window : [min, max], required. 
                Min. & Max. of the efficiency map temperature window. 
                Outside this range before reaching target steady state will be considered stalled
            ramp_torque : bool, required. Determines if DUT brake ramps or steps to target
        """

        start_time = kwargs['setup_start']
        apks = kwargs['apks']
        target_akp = int(apks[kwargs['step']])
        brake_torque = target_akp / kwargs['rated_motor_current'] * 100
        timeout = kwargs['timeout']
        device = kwargs['device']
        temp_window = kwargs['temp_window']
        self.test_outputs['skip_ss'] = False
        ss_current = kwargs['ss_current']
        braking = False

        # setup logging file for current cycle test speed
        extra = f"{kwargs['speeds'][kwargs['cycle']]}"
        self.test_outputs['extra'] = extra
        self.extra_logging(file_name=extra, 
                           header=self.appended_csvline(['PkCurrent', 
                                                         '3PH Power', 
                                                         'Efficiency Map Flag'],
                                                        True))

        # check temp
        print(f"Checking {kwargs['device']} temperature")
        cur_temp = self.devices[1].read(f'{device} temperature')
        if temp_window[0] > cur_temp:  # warm up if under temp
            self.devices[1].start()
            self.devices[1].ramp_to(brake_torque)
            braking = True
        elif temp_window[1] < cur_temp:  # cool down if over temp
            self.devices[1].stop()
            braking = False
        self.efficiency_table_extra_line(**kwargs)
        
        while (datetime.now() - start_time).total_seconds() < timeout and self.testing:
            if temp_window[0] > cur_temp or temp_window[1] < cur_temp:
                self.int_event.wait(1)
            else:
                break
        self.efficiency_table_extra_line(**kwargs)
        print(f"{kwargs['device']} temperature in range")

        # check timeout
        if (datetime.now() - start_time).total_seconds() >= timeout:
            print("TIMEOUT: before setting up for next steady state!")
            print("Skipping the next steady state")
            self.test_outputs['skip_ss'] = True

        # restart braking if was cooling down
        if not braking:
            self.devices[1].start()
            if kwargs['ramp_torque']:
                self.devices[1].ramp_to(brake_torque)
            else:
                self.devices[1].set_torque(brake_torque)
            self.int_event.wait(2)  # wait for extra seconds to reach steady state
            self.efficiency_table_extra_line(**kwargs)

        # check steady state before handing over to the while loop in cycle function
        [peak_current, three_ph_power, current_flag] = self.efficiency_table_flag(**kwargs)
        if target_akp * (1 - ss_current / 100) <= peak_current <= target_akp * (1 + ss_current / 100):
            pass
        else:
            # find out braking torque with PID
            calibration_pid = PID(Kp=0.02, Ki=0.05, setpoint=target_akp, output_limits=(0, 100), sample_time=1)
            calibration_pid.set_auto_mode(False)
            calibration_pid.set_auto_mode(True, peak_current)
            while (datetime.now() - start_time).total_seconds() < timeout and self.testing:
                self.int_event.wait(1)
                [peak_current, three_ph_power, current_flag] = self.efficiency_table_flag(**kwargs)
                if target_akp * (1 - ss_current / 100) <= peak_current <= target_akp * (1 + ss_current / 100):
                    calibration_pid = None
                    break
                new_torque = calibration_pid(peak_current)
                # new_torque = (2 - peak_current / target_akp) * brake_torque
                self.devices[1].set_torque(new_torque)
                self.test_outputs['current_target'] = new_torque
                
        self.efficiency_table_extra_line(**kwargs)

        # reset ss sample count
        self.test_outputs['samples'] = 0

        if (datetime.now() - start_time).total_seconds() >= timeout:
            self.test_outputs['skip_ss'] = True

    def efficiency_table_extra_line(self, **kwargs):
        flag = self.efficiency_table_flag(**kwargs)
        if flag[2] == 1:
            self.test_outputs['samples'] += 1
        self.extra_line(file_name=self.test_outputs['extra'], 
                        custom=True, 
                        data=self.appended_csvline(flag))
        return True
    

    def efficiency_table_flag(self, **kwargs):
        """
        reads current dyno csvline and flag the data for certain conditions
        checks RPM, peak motor current and device temperature within steady state window

        Keyword arguments:
            cycle : int, required. current cycle #
            step : int, required. current step #
            speeds : list, required. List of target speeds i.e. [500, 1000, ... , 2540]
            apks : list, required. To determine brake torque %
            device : str, required. Efficiency Table target device. Accepts "motor" or "controller"
            ss_rpm : int, required. RPM delta to determine steady state
            ss_current : float, required. Motor current delta to determine steady state
            temp_window : [min, max], required. 
                Min. & Max. of the efficiency map temperature window. 
                Outside this range before reaching target steady state will be considered stalled
            samples : int, required. indicates how many steady state samples have already been collected
        
        Return:
            0 - not in steady state
            1 - in steady state
            2 - over temp steady state
        """

        speeds = kwargs['speeds']
        target_rpm = int(speeds[kwargs['cycle']])
        apks = kwargs['apks']
        target_akp = int(apks[kwargs['step']])
        device = kwargs['device']
        temp_window = kwargs['temp_window']
        ss_rpm = kwargs['ss_rpm']
        ss_current = kwargs['ss_current']

        csv_line = self.current_csv_line
        headers = self.getcsvline(getnames=True)
        phase_current_index = [headers.index('Phase RMS Current 1'),
                    headers.index('Phase RMS Current 2'),
                    headers.index('Phase RMS Current 3')]
        phase_power_index = [headers.index('Phase Real Power 1'),
                            headers.index('Phase Real Power 2'),
                            headers.index('Phase Real Power 3')]
        yoko_speed_index = headers.index('Motor Speed')
        device_temp_index = headers.index(f'DUT {device} temperature')

        # calculate peak current from yoko phase currents
        peak_current = 0
        for i in range(3):
            peak_current += csv_line[phase_current_index[i]]
        peak_current /= 3
        peak_current *= math.sqrt(2)

        # calculate 3 phase total power
        three_ph_power = 0
        for i in range(3):
            three_ph_power += csv_line[phase_power_index[i]]
        
        # check rpm in ss
        rpm_in_ss = False
        if abs(target_rpm) * (1 - ss_rpm / 100) <= csv_line[yoko_speed_index] <= abs(target_rpm) * (1 + ss_rpm / 100):
            rpm_in_ss = True
            
        # check current in ss
        current_in_ss = False
        if target_akp * (1 - ss_current / 100) <= peak_current <= target_akp * (1 + ss_current / 100):
            current_in_ss = True
            
        # check temp in ss
        temp_in_ss = False
        if temp_window[0] <= csv_line[device_temp_index] <= temp_window[1]:
            temp_in_ss = True

        # determines the state
        if rpm_in_ss and current_in_ss and temp_in_ss:
            return [peak_current, three_ph_power, 1]
        elif rpm_in_ss and current_in_ss:
            return [peak_current, three_ph_power, 2]
        else:
            return [peak_current, three_ph_power, 0]

    def efficiency_table_hold_condition(self, **kwargs):
        """
        hold conditions to log efficiency table data
        uses efficiency_table_flag

        Keyword arguments:
            cycle : int, required. current cycle #
            step : int, required. current step #
            speeds : list, required. List of target speeds i.e. [500, 1000, ... , 2540]
            apks : list, required. To determine brake torque %
            device : str, required. Efficiency Table target device. Accepts "motor" or "controller"
            ss_rpm : int, required. RPM delta to determine steady state
            ss_current : float, required. Motor current delta to determine steady state
            temp_window : [min, max], required. 
                Min. & Max. of the efficiency map temperature window. 
                Outside this range before reaching target steady state will be considered stalled
            samples : int, required. indicates how many steady state samples have already been collected
        """

        if self.test_outputs['skip_ss']:
            print("Skipping SS due to timeout")
            return False
        if self.test_outputs['samples'] >= kwargs['ss_samples']:
            print(f"SS sample count reached {kwargs['ss_samples']}")
            return False
        
        [peak_current, three_ph_power, current_flag] = self.efficiency_table_flag(**kwargs)

        if current_flag == 1:
            return True
        else:
            if self.test_outputs['samples'] >= kwargs['ss_samples']:
                return False
            else:
                return True

    def efficiency_table_hold_command(self, **kwargs):
        """
        Hold command should just be writing steady state to log file
        just calling efficiency_table_extra_line
        """

        self.efficiency_table_extra_line(**kwargs)
        print(f"{self.test_outputs['samples']}/{kwargs['ss_samples']} SS points logged")
        # self.test_outputs['samples'] += 1


def collectPvals(paramlist, getnames=False, indicator=None):
    retlist = []

    for param in paramlist:
        if getnames:
            if indicator is None:
                retlist.append(paramlist[param].Name)
            else:
                retlist.append(f"{indicator} {paramlist[param].Name}")
        else:
            try:
                if paramlist[param].Value is not None:
                    retlist.append(float(paramlist[param].Value))
                else:
                    retlist.append(0)
            except TypeError as t_e:
                logging.debug(t_e)
                retlist.append(0)

    return retlist

# def function(data, a, b, c, d, e, f, g):
#     x = data[0]
#     y = data[1]
#     ans = a*np.log(x) + b*np.log(y) + c*x + d*y + e*x**2 + f*y**2 + g
#     ans[ans < 59] = 0
#     return ans
#
# def f_power(data, a):
#     x = data[0]
#     y = data[1]
#     # ans = y*(a*x + b*y + c*x**2 + d*y**2 + e)
#     ans = a*x*y
#     # ans[ans < 59] = 0
#     return ans
#
# def f_eff_power(data, a, b, c, d, e, f, g):
#     x = data[0]
#     y = data[1]
#     # ans = np.log(y)*(a*x**2 + b*x + c*y/x + e*(y/x)**0.5 + d) + f
#     ans = a*np.log(x) + b*np.log(y/x) + c*x + d*y/x + e*x*y + f*y +g
#     ans[ans < 20] = 0
#     return ans
#
# def boundary_function(data, a, b, c):
#     # return a*data**0.5 + b
#     # return a*np.log(data) + b
#     return a*data**0.5 + b*data + c
#     # return a*data**2 + b*data + c
#
# def boundary_function_power(data, a, b):
#     # return a*data**0.5 + b
#     return a*data + b
#     # return a*data**2 + b*data + c
#     # return a*data**2 + b*data + c
#
# def boundary_power_cap(data, a, b):
#     return a*data + b

