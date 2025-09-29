import dyno_v2.Module.rpc
import dyno_v2.Module.vxi11 as vxi11
import threading
import logging
from math import isfinite
from time import sleep
from dyno_v2.Module.Parameter import Parameter
from dyno_v2.Module.DynoABCs import DynoPoller
from dyno_v2.Module.exceptions import *


class Yokogawa_WT1806(DynoPoller):

    def __init__(
            self,
            IP="192.168.1.79",
            file="yoko_parameter_information.csv",
            abs_torque=False
    ):
        # connect to Yoko
        self.ip = IP
        self.connected = False
        try:
            self.device = vxi11.Instrument(IP)
            identity = self.query("*IDN?")
            print("Connected to Yokogawa! Identity: " + str(identity))
        except (TimeoutError, ConnectionError, ConnectionRefusedError) as e:
            print(str(e))
            del self.device
            raise ConnectionError
        except KeyboardInterrupt:
            print("Interrupted")
            del self.device
            return

        self.connected = True

        # tell Yoko to encode its responses as ASCii, needed for vxi11 parsing
        self.device.write("numeric:Format ASCII")

        # setup instance variables
        self.log_params = file
        self._poll_interval = 0.1  # seconds
        self._poll_enabled = False  # Polling flag for worker thread: True for continuous polling
        self._worker = None
        self._lock = threading.Lock()

        self.abs_torque = abs_torque

    def __repr__(self):
        template = f"YOKOGAWA on {self.ip}"
        return template

    def loadParams(self, file="yoko_parameter_information.csv"):
        # load yoko parameters
        with open(file, "r") as f:
            f.readline()  # throw away header line
            plines = f.readlines()

        params = {}
        for address, line in enumerate(plines, 1):
            name, shortened_name, channel, units = line.split(",")
            params[name] = Parameter(name=name, field=shortened_name, element=channel, units=units, address=address)
            # write config to yoko
            self.device.write("numeric:normal:item" + str(address) + " " + str(shortened_name) + "," + str(channel))

        return params

    def query(self, msg):
        try:
            return self.device.ask(msg)
        except (dyno_v2.Module.rpc.RPCUnpackError, ConnectionResetError):
            return 0

    def write(self, msg):
        self.device.write(msg)

    def read(self, param):
        return self.query(":numeric:normal:value? " + str(param.Address))

    def pollingThread(self):
        while self.poll_enabled:
            self.fetchAllMeasurements()
            sleep(self.poll_interval)

    def start_polling(self, pollTime=0.1):
        self.poll_interval = pollTime
        self.poll_enabled = True
        self._worker = threading.Thread(target=self.pollingThread)
        self._worker.daemon = True
        self._worker.start()

    def stop_polling(self):
        if self.poll_enabled:
            self.poll_enabled = False
            if hasattr(self, '_worker') and self._worker:
                self._worker.join()

    def close(self):
        self.stop_polling()
        if hasattr(self, 'device'):
            try:
                self.device.close()
            except ConnectionResetError:
                del self.device

    def __del__(self):
        self.connected = False
        self.close()

    def fetchAllMeasurements(self):
        for param in self.log_params:
            value = self.query(":numeric:normal:value? " + str(self.log_params[param].Address))
            if isfinite(float(value)):
                with self._lock:
                    if self.abs_torque and "Torque" in self.log_params[param].Name:
                        self.log_params[param].Value = abs(float(value))
                    else:
                        self.log_params[param].Value = value

    def getMeasurement(self, name) -> float:
        # for param in self.log_params:
        try:
            param = self.log_params[name]
        except KeyError:
            raise NotInLogParameterError
        else:
            if param.Name == name or param.field == name:
                if self.poll_enabled:
                    if param.Value is not None:
                        return float(param.Value)
                else:
                    return float(self.read(param))

    def getAvgPhaseCurrent(self) -> float:
        try:
            value: float = self.getMeasurement("Phase RMS Current 1")
            value += self.getMeasurement("Phase RMS Current 2")
            value += self.getMeasurement("Phase RMS Current 3")
        except NotInLogParameterError:
            logging.warning(f"Phase RMS Currents not in log parameters")
            return 0
        else:
            return value / 3.0

    @property
    def log_params(self):
        return self._log_params

    @log_params.setter
    def log_params(self, file):
        self._log_params = self.loadParams(file)

    @property
    def poll_interval(self):
        return self._poll_interval

    @poll_interval.setter
    def poll_interval(self, val):
        self._poll_interval = val

    @property
    def poll_enabled(self):
        if hasattr(self, '_poll_enabled'):
            return self._poll_enabled

    @poll_enabled.setter
    def poll_enabled(self, val):
        self._poll_enabled = val


if __name__ == "__main__":
    yoko = Yokogawa_WT1806("192.168.1.79")
    yoko.start_polling()
    while yoko.poll_enabled:
        sleep(3)
        for param in yoko.log_params:
            print(param)
