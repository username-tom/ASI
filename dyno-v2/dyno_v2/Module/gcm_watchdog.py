from BACmodbus import Parameter, BAC
from time import sleep
from datetime import datetime


class GCMWatchdog:

    def __init__(self, port='COM11', baudrate=115200, id=1):
        self.gcm = BAC(id, port, baudrate)
        self.firmware_version = Parameter('variable', 511, 32, '')

    def gcm_checksum_checker(self, duration=20.):  # duration in minutes
        start = datetime.now()
        test_time = duration * 60  # convert duration to seconds
        print(f"Will run for {test_time} seconds...")
        while (datetime.now() - start).total_seconds() < test_time:
            self.gcm.readParameter(self.firmware_version)  # read calculated system voltage parameter with no pause
            # sleep(0.001)
        print(f"checksum errors: {self.gcm.checksums}/{self.gcm.attempt}")  # Results: No. of checksum errors (bad signal)
        print("Ran for " + str((datetime.now() - start).total_seconds()) + "s")  # total run time


if __name__ == "__main__":
    watchdog = GCMWatchdog()
    watchdog.gcm_checksum_checker()
