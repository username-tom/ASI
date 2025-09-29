# ASI Includes
from simple_pid import PID
from dyno_v2.Module.ASIDynoModule import *
from dyno_v2.Module.yokogawa_WT1806 import Yokogawa_WT1806
from dyno_v2.Module.abb_acs800 import AbbAcs800
from dyno_v2.Module.asi_controller import ASIController

from time import sleep
from datetime import datetime
import os
ROOT_DIR = os.getcwd()


def count_down(seconds=60):
    for i in range(seconds):
        print(f"{seconds - i} seconds remaining...", end='\r')
        sleep(1)
    print()


class RundownGear:
    def __init__(self, dyno: ASIDynoModule):
        self.dyno = dyno
        self._PID = None
        self.target = 0
        self.test_time = 0
        self.gear_ratio = 1

    # Tested with a Cedar motor and an ABB controller as the torque / brake
    def hold_torque(self, target, duration=5.):
        torque = self.dyno.devices[PA].getMeasurement("Torque")
        print(torque)
        
        while abs(torque) > abs(target):
            print(f"Ramping to target", end="\r")

            self.dyno.curTorque -= 1
            self.dyno.devices[2].set_torque(self.dyno.curTorque)
            
            sleep(self.dyno.pid_parameters['interval'])
            
            torque = self.dyno.devices[PA].getMeasurement("Torque")
        
        while abs(torque) < abs(target):
            print(f"Ramping to target", end="\r")

            self.dyno.curTorque += 1
            self.dyno.devices[2].set_torque(self.dyno.curTorque)
            
            sleep(self.dyno.pid_parameters['interval'])
            
            torque = self.dyno.devices[PA].getMeasurement("Torque")
            
        print()

        torque = self.dyno.devices[PA].getMeasurement("Torque")
        print(torque)

        print(f"Holding target")
        count_down(int(duration) * 60)

        return torque

    def rundown_gear(self, targetTorque, ratio: float, time):
        self.target = targetTorque
        self.gear_ratio = ratio
        self.test_time = time

        startTime = datetime.now()
        self.dyno.start_logging(1, run_down="Geared Cedar")

        try:
            # Step 1: No load both directions at max speed for 1 min each
            print("Starting Driver")
            self.dyno.devices[1].remote_speed_mode(speed=0, speed_command=100, motoring_current=100)
            count_down(60)
            dyno.devices[1].stop_remote_motor()
            while self.dyno.devices[1].get_rpm() > 0:
                continue
            sleep(3)
            print("Reversing Driver")
            self.dyno.devices[1].clear_faults()
            self.dyno.devices[1].remote_speed_mode(speed=0, motoring_current=50, speed_command=-50)
            sleep(2)
            self.dyno.devices[1].remote_speed_mode(speed=0, motoring_current=100, speed_command=-80)
            sleep(2)
            self.dyno.devices[1].remote_speed_mode(speed=0, motoring_current=100, speed_command=-100)
            count_down(60)
            dyno.devices[1].stop_remote_motor()
            while self.dyno.devices[1].get_rpm() > 0:
                continue
            print("Record Temp")
            count_down(60)
            
            # Step 2: Full load forward directions for 1 min
            print("Starting Driver")
            self.dyno.devices[1].remote_speed_mode(speed=0, motoring_current=100, speed_command=100)
            sleep(1)
            print("Starting Brake")
            self.dyno.devices[2].start()
            sleep(3)
            print("holding torque")
            self.hold_torque(target=targetTorque / ratio, duration=self.test_time)
            print(f"\n\n\n\n\n\n\n")
            self.dyno.stop_test()
            self.dyno.curTorque = 0
            self.dyno.devices[2].set_torque(0.0)
            while self.dyno.devices[1].get_rpm() > 0:
                continue
            sleep(3)
            while self.dyno.devices[1].in_foldback():
                sleep(3)

            count_down(60)
            
            # Step 3: 100 Nm @ 150 rpm at shaft (max speed for motor) for 5 min
            print("Starting Driver")
            self.dyno.devices[1].remote_speed_mode(speed=0, motoring_current=100, speed_command=100)
            sleep(1)
            print("Starting Brake")
            self.dyno.devices[2].start()
            sleep(3)
            self.target = 100
            self.test_time = 5
            self.hold_torque(target=self.target / ratio, duration=self.test_time)
            print(f"\n\n\n\n\n\n\n")
            self.dyno.stop_test()
            print("Record Temp")

        except KeyboardInterrupt:
            print(f"\n\n\n\n\n\n\nInterrupted")
            self.dyno.stop_test()
        finally:
            print("tests Over")
            self.dyno.stop_test()
            self.dyno.stop_logging()
            delta = (datetime.now() - startTime).total_seconds() / 60
            print(f"tests duration: {delta:.2f} minutes")


if __name__ == "__main__":
    # TUNABLES:
    test_time = 1

    # instruments on their addresses:
    yoko = Yokogawa_WT1806("192.168.1.164", abs_torque=True)  # Check address with YOKOGAWA
    ABB = AbbAcs800(port='COM5', baud=19200, auto=True)
    dut = ASIController("COM11", 115200, 1, "", root=ROOT_DIR)

    # BAC2BAC：
    # driver = ASIController("COM5", 115200, 1, "")
    # brake = ASIController("COM7", 115200, 1, "")

    # init dyno, set timing params, and start logging
    sleep(1)
    dyno = ASIDynoModule(dut, yoko, ABB)

    test = RundownGear(dyno)
    test.rundown_gear(300, 7.47, test_time)
    exit()
