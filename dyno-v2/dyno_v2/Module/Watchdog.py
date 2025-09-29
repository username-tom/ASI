# ASI Includes
import sys
sys.path.extend(['C:\\Users\\twu\\PycharmProjects\\dyno-v2'])
from dyno_v2.Module.asi_controller import ASIController
from time import sleep
from datetime import datetime, timedelta
from dyno_v2.Module.util import parse_etree
from dyno_v2.Module.j1939 import *


def wait_for(time):
    wait_start = datetime.now()
    waiting = True
    while waiting:
        if (datetime.now() - wait_start).total_seconds() < time:
            sleep(1)
        else:
            waiting = False


class Watchdog:
    def __init__(self, port="COM3", baud=115200, mb_address=1, j1939=False, **pv):
        if "COM" in port:
            print("Initiating Watchdog Tester @ port " + port + " with Baud rate "
                  + str(baud) + " & MB Address " + str(mb_address))
            print("Initiating ASI Controller")
            self.dut = ASIController(port, baud, mb_address, "",
                                     root="C:\\Users\\twu\\PycharmProjects\\dyno-v2", all_params=True)
        elif j1939:
            print("Initiating J1939 Watchdog Tester @ port " + port + " with Baud rate "
                  + str(baud) + " & MB Address " + str(mb_address))
            print("Initiating ASI Controller")
            self.dut = ASIController(port, baud, mb_address, j1939=True,
                                     root="C:\\Users\\twu\\PycharmProjects\\dyno-v2")
        else:
            print("Initiating Watchdog Tester @ can port " + port + " with Baud rate "
                  + str(baud))
            print("Initiating ASI Controller")
            self.dut = ASIController("default", baud_rate=baud, mb_address=42, is_can=True,
                                     root="C:\\Users\\twu\\PycharmProjects\\dyno-v2", all_params=True)
        self.original_parameters = {}
        for p in pv:
            self.original_parameters[p] = self.dut.read(p)
        self.update_params(**pv)

    def restore_parameters(self):
        self.update_params(**self.original_parameters)

    def run_till_fault(self, interval=0.05, loop=20):
        if self.dut.read("controller status") == 4:
            print("Controller fault!")
            return
        start = datetime.now()
        for i in range(loop):
            self.dut.write("Remote state command", 258)  # Toggle high bit off
            sleep(interval)
            self.dut.write("Remote state command", 514)  # Toggle high bit on
            sleep(interval)
            if self.dut.read("controller status") == 4:
                print("Controller fault after ~" + str((datetime.now() - start).total_seconds()) + "s")
                return
        print("Motor ran for " + str((datetime.now() - start).total_seconds()) + "s")

    def run_for(self, interval=0.05, loop=20):
        if self.dut.read("controller status") == 4:
            print("Controller fault!")
            return
        start = datetime.now()
        for i in range(loop):
            self.dut.write("Remote state command", 258)  # Toggle high bit off
            sleep(interval)
            self.dut.write("Remote state command", 514)  # Toggle high bit on
            sleep(interval)
        if not self.dut.is_j1939:
            print(f"checksum errors: {self.dut.modbus.checksums}")
        print("Motor ran for " + str((datetime.now() - start).total_seconds()) + "s")

    def update_params(self, **pv):
        for param in pv:
            self.dut.write(param, pv[param])
            if param == "Fault clear" or \
                    0.99 * abs(pv[param]) <= abs(self.dut.read(param)) <= 1.01 * abs(pv[param]):
                # print(param + " is set with " + str(self.dut.read(param)))
                continue
            else:
                print(param + " not set!")

    def update_timeout(self, timeout=0, average_timeout=0):
        self.dut.write("Command timeout threshold", timeout)
        self.dut.write("Average Command timeout threshold", average_timeout)
        if self.dut.read("Command timeout threshold") == timeout \
                and self.dut.read("Average Command timeout threshold") == average_timeout:
            print("Timeout threshold update successful!")
        else:
            print("Timeout threshold update failed!")

    def check_bit_vector(self, param, bit: int, mask=1, write=True):
        print(f"Checking {param} bit {bit} == {mask}")
        check = int(self.dut.read(param))
        if (check & (1 << bit)) >> bit == mask:
            return True
        else:
            if write:
                if mask == 1:
                    self.dut.write(param, check + (1 << bit))
                else:
                    self.dut.write(param, check - (1 << bit))
                return True
            else:
                return False


# COM & Motor parameters for TC 10.1.2
PORT = "COM5"
BAUD_RATE = 115200
MB_ADDRESS = 1
REMOTE_SPEED_COMMAND = 50
REMOTE_MOTORING_CURRENT = 25
REMOTE_BRAKING_CURRENT = 25

if __name__ == "__main__":
    parameters = {"Fault clear": 1,
                  "Control command source": 0,
                  "Speed regulator mode": 0,
                  "Remote maximum motoring current": REMOTE_MOTORING_CURRENT,
                  "Remote maximum braking current": REMOTE_BRAKING_CURRENT,
                  "Remote speed command": REMOTE_SPEED_COMMAND}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.set_access_level(4)
    watchdog.dut.write("TE Configuration", 0)
    watchdog.dut.set_access_level(0)
    watchdog.dut.turn_off_communication_timeout()
    print("Initialization successful!")

    parameters = {"TE Configuration": 3}
    run_for = 8
    watchdogInt = 0.25
    print("Watchdog interval: " + str(watchdogInt) + "s")

    # tests 1: Ensure heartbeat signal can keep the controller alive
    watchdog.update_timeout(1000, 750)

    print("Motor running with timeout threshold for " + str(watchdogInt * 2 * run_for) + "s")
    watchdog.run_for(watchdogInt, run_for)

    # tests 2: Ensure heartbeat signal works with TE Configuration -> 3
    watchdog.dut.set_access_level(4)
    print("Changing TE Configuration at " + str(datetime.now().time().isoformat()))
    watchdog.update_params(**parameters)
    # watchdog.dut.set_access_level(0)

    print("Motor running with TE Configuration for " + str(watchdogInt * 2 * run_for) + "s")
    watchdog.run_till_fault(watchdogInt, run_for)

    # tests 3: Ensure risk address state is triggered by slow comm
    watchdogInt = 3.2
    print("Watchdog interval: " + str(watchdogInt) + "s")
    print("Timeout threshold -> 3000ms")
    watchdog.update_timeout(3000, 2600)

    print("Controller should be in risk address mode")
    watchdog.run_till_fault(watchdogInt, run_for)
