# ASI Includes
from Module.DynoABCs import DynoPoller, DynoBrake
from Module.asi_controller import *
from Module.config import *

# needed
import logging
from tkinter import messagebox
from os import makedirs
from pathlib import Path
import csv
from time import sleep
from datetime import datetime
from threading import Thread, Event


class ASIDynoModule:
    def __init__(
            self,
            dut="COM10",
            brake="COM9",
            log_folder="C:/DynoResults/"
    ):
        # operating parameters
        self.curTorque = 0  # % brake torque

        self.devices = {}
        self.dyno_connect(dut, brake)
        print("Initialized")

        self.faults_backup = {
            1: self.devices[1].faults_parameters.copy() if isinstance(self.devices[1], ASIController) else None,
            2: self.devices[2].faults_parameters.copy() if isinstance(self.devices[2], ASIController) else None
        }

        # create new timestamped logfile directory
        self.update_log_dir(log_folder)
        self._logfile = self._logdir / "startup.csv"  # this file is placeholder; should never be created
        self._logInterval = 10
        self._logEnabled = False
        self.extra_files = {}
        self._worker = None
        self.start_time = None
        self.driver = 1  # 1 - Device 1 | 2 - Device 2
        self.testing = False
        self.stopping = False
        self.status_thread = None
        self.updating = True
        self.current_csv_line = [0] * len(self.update_csv_line(True))
        self.csv_thread = Thread(target=self.update_csv)
        self.test_outputs = {}
        self.watchdog_enabled = False
        self.watchdog = None
        self.watchdog_interval = WATCHDOG_INTERVAL
        self.int_event = Event()

        self._start_polling()
        self.start_status_thread()

    def __repr__(self):
        template = f"Device 1: {self.devices[1]}\n" \
                   f"Device 2: {self.devices[2]}\n"
        return template

    def dyno_connect(self, dut, brake):
        if isinstance(dut, ASIController):
            self.devices[1] = dut
        elif dut is None:
            raise AttributeError("Missing DUT")
        elif isinstance(dut, str):
            try:
                if "COM" in dut:
                    self.devices[1] = ASIController(dut, 115200, 1)
            except ConnectionError:
                print("Connection to device 1 failed!")
        else:
            raise TypeError(f"Invalid type for device 1, {type(dut)}")

        # Init Brake
        if (isinstance(brake, DynoBrake) or
                brake is None):
            self.devices[2] = brake
        elif isinstance(brake, str):
            try:
                self.devices[2] = ASIController(brake, 115200, 1)
            except ConnectionError:
                print('Connection to device 2 failed!')
        else:
            raise TypeError("Invalid type for device 2, '", type(brake), "' ")

    def start_status_thread(self):
        self.start_time = datetime.now()
        self.status_thread = Thread(target=self.status_update)
        self.status_thread.start()

    def status_update(self):
        while self.updating:
            try:
                if self.devices[1]:
                    if not self.devices[1].connected:
                        logging.info("Device 1 Connection lost")
                        self.testing = False
                        raise CommError
            except (CommError, AttributeError, TypeError):
                self.devices[1].connected = False
                break

            if self.devices[2] and not self.devices[2].connected:
                logging.info("Device 2 Connection lost")
                self.testing = False
                raise CommError

            if self.updating:
                sleep(1)

    def stop_status(self):
        self.updating = False
        self.status_thread = None

    def _start_polling(self):
        # start instruments polling
        if isinstance(self.devices[1], DynoPoller):
            self.devices[1].start_polling(1)
        if isinstance(self.devices[2], DynoPoller):
            self.devices[2].start_polling(1)

        self.csv_thread.start()

    def _stop_polling(self):
        self.updating = False
        self.csv_thread = None

        if isinstance(self.devices[1], DynoPoller):
            self.devices[1].stop_polling()
        if isinstance(self.devices[2], DynoPoller):
            self.devices[2].stop_polling()

    def update_log_interval(self, new_interval):
        try:
            float(new_interval)
        except (TypeError, ValueError):
            pass
        else:
            self._logInterval = float(new_interval)
            logging.info(f"Logging Interval Updated to {self._logInterval}")

    def update_log_dir(self, log_folder):
        self.logpath = Path(log_folder)
        self._logdir = self.logpath / datetime.now().strftime('%Y-%m-%d-%H-%M')

    def logging_thread(self):
        while self._logEnabled:
            sleep(self._logInterval)
            with open(file=self._logfile, mode='a', newline='') as csvfile:
                csv.writer(csvfile).writerow(self.getcsvline())

    def start_logging(self, logtime=10, run_down=""):
        if not self.is_logging_enabled():
            # begin new timestamped logfile for new datarun
            self.start_time = datetime.now()
            self._logdir = self.logpath / (f"{run_down if run_down == '' else f'{run_down} '}"
                                           f"{self.start_time.strftime('%Y-%m-%d-%H-%M')}")
            makedirs(self._logdir, exist_ok=True)
            csv_name = f"{self.start_time.strftime('%Y-%m-%d-%H-%M-%S')} {run_down}.csv"
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

    def log_file(self):
        return self._logfile

    def getcsvline(self, getnames=False):
        if getnames:
            return self.update_csv_line(getnames)
        else:
            return self.current_csv_line

    def update_csv(self):
        while self.updating:
            self.current_csv_line = self.update_csv_line()
            sleep(1)

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

        if self.devices[1] and isinstance(self.devices[1], DynoPoller):
            linelist.extend(collectPvals(self.devices[1].log_params, getnames, indicator="DUT"))
        if self.devices[2]:
            linelist.extend(collectPvals(self.devices[2].log_params, getnames, indicator="BRK"))

        return linelist

    def extra_logging(self, file_name="", header=None):
        csv_name = f"{file_name.replace('.csv', '')}.csv"

        if csv_name in self.extra_files:
            pass
        else:
            idx = len(self.extra_files)
            self.extra_files[csv_name] = idx

        datafile = f"{self.logdir}\\{csv_name}"

        try:
            with open(file=datafile, mode='x', newline='') as csvfile:
                if header is None:
                    csv.writer(csvfile).writerow(self.getcsvline(getnames=True))
                else:
                    csv.writer(csvfile).writerow(header)
        except FileExistsError:
            if header is None:
                with open(file=datafile, mode='w', newline='') as csvfile:
                    csv.writer(csvfile).writerow(self.getcsvline(getnames=True))
            else:  # Assuming only appending to existing extra custom files
                logging.info("Attention: File already exists, only appending new lines! ")

    def extra_line(self, file_name=""):
        csv_name = f"{file_name.replace('.csv', '')}.csv"
        datafile = self.logdir / csv_name

        try:
            with open(file=datafile, mode='a', newline='') as csvfile:
                csv.writer(csvfile).writerow(self.getcsvline())
        except PermissionError as e:
            print(e)

            return

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
            # self.devices[1].turn_off_communication_timeout()
            self.devices[1].write("Remote state command", 0)
        if isinstance(self.devices[2], ASIController):
            # self.devices[2].turn_off_communication_timeout()
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

        try:
            self.devices[1].__del__()
            self.devices[1] = None
        except (ValueError, AttributeError, CommError):
            pass
        else:
            logging.info("Device 1 reset")

        try:
            self.devices[2].__del__()
            self.devices[2] = None
        except (ValueError, AttributeError):
            pass
        else:
            logging.info("Device 2 reset")

    def stop_test(self):
        """Dyno stop sequence"""
        self.stop_watchdog()
        try:
            asi_brake = False
            if self.devices[3 - self.driver] is not None:
                asi_brake = True
            if self.devices[self.driver] is not None:
                if asi_brake:
                    self.devices[3 - self.driver].stop_switch()
                self.devices[self.driver].stop_remote_motor()
                sleep(0.5)
            if self.devices[3 - self.driver] is not None:
                self.devices[3 - self.driver].stop()
        except CommError:
            pass

    @property
    def logdir(self):
        return self._logdir

    def is_logging_enabled(self):
        return self._logEnabled

    def rundown(self, **kwargs):
        """Rundown function

        Keyword arguments:
            minTorque : int, required. rundown starting brake torque
            maxTorque : int, required. rundown maximum braking torque
            torqueStep : float, required. rundown loop step
            settleTime : float, required. rundown loop interval
        """
        extra = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')} - RUNDOWN SS Pts"
        self.extra_logging(file_name=extra)

        self.test_outputs['max_torque'] = 0
        self.test_outputs['max_temp'] = 0

        # ramp torque with constant-time wait, and log SS dataline
        curTorque = int(kwargs['minTorque'])
        # startRun = datetime.now()
        while self.testing and curTorque < kwargs['maxTorque']:
            self.devices[3 - self.driver].ramp_to(target=curTorque,
                                                  step=10,
                                                  period=kwargs['settleTime'])

            curSpeed = self.devices[self.driver].get_rpm()

            if self.test_outputs['max_torque'] < curTorque:
                self.test_outputs['max_torque'] = curTorque

            if curSpeed > 30:
                self.extra_line(file_name=extra)
                curTorque += kwargs['torqueStep']
            else:
                print('Stalled')
                break

        self.stop_test()
        self.test_outputs['max_temp'] = self.devices[self.driver].read("motor temperature")

    def wait_till_stopped(self, device=1):
        if isinstance(self.devices[device], ASIController):
            while self.devices[device].get_rpm() != 0:
                self.int_event.wait(1)

    def babying(self, device=1, **kwargs):
        """Babying the controller to target speed/torque/current

        Keyword arguments:
            device : int, optional. Target device
            speed : int, required
            speed_command : float, optional
            motoring_current : float, optional. Default to 100
            braking_current : float, optional.
        """
        if 'motoring_current' not in kwargs.keys():
            kwargs['motoring_current'] = 100

        if not self.devices[device].remote_faults_handle():
            faults = self.devices[device].check_faults()
            print(f"Registered faults: {faults}")
            if str(faults).find("over current"):
                kwargs['motoring_current'] = 0.25 * kwargs['motoring_current']
                if 'speed' in kwargs.keys():
                    kwargs['speed'] = 0.5 * kwargs['speed']
                if 'speed_command' in kwargs.keys():
                    kwargs['speed_command'] = 0.5 * kwargs['speed_command']
                self.devices[device].remote_speed_mode(**kwargs)
                self.devices[device].clear_faults()

                self.int_event.wait(10)

                if 'speed' in kwargs.keys():
                    kwargs['speed'] = 2 * kwargs['speed']
                if 'speed_command' in kwargs.keys():
                    kwargs['speed_command'] = 2 * kwargs['speed_command']
                self.devices[device].remote_speed_mode(**kwargs)

                self.int_event.wait(10)

                kwargs['motoring_current'] = 4 * kwargs['motoring_current']
                self.devices[device].remote_speed_mode(**kwargs)

                faults = self.devices[device].check_faults()
                if faults:
                    if not self.devices[device].remote_faults_handle():
                        print(f"This fault won't clear! Test aborted\n{faults}")
                        return False

    def motor_discovery(self, mode):
        if self.devices[self.driver]:
            self.devices[self.driver].motor_discovery(mode)
            if mode == 1:
                self.int_event.wait(MD1)
            elif mode == 2:
                self.int_event.wait(MD2)
            return self.devices[self.driver].retrieve_discovery(mode)

    def interrupt_motor_discovery(self):
        if self.devices[self.driver]:
            self.devices[self.driver].stop_motor_discovery()

    def clear_faults(self):
        if self.devices[1]:
            self.devices[1].clear_faults()
        if self.devices[2]:
            self.devices[2].clear_faults()


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
