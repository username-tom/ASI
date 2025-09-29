"""Watchdog version of TC 10.5.4"""
# ASI Includes
from dyno_v2.Module.ASIDynoModule import ASIDynoModule
from dyno_v2.Module.yokogawa_WT1806 import Yokogawa_WT1806
from dyno_v2.Module.asi_controller import ASIController
from dyno_v2.Module.Watchdog import Watchdog

from time import sleep
from datetime import datetime

REMOTE_SPEED_COMMAND = 50  # Remote speed command (490)
REMOTE_MOTORING_CURRENT = 10  # Remote motoring current (491)
REMOTE_BRAKING_CURRENT = 25  # Remote braking current (492)

if __name__ == "__main__":

    # instruments on their addresses:
    # Yoko：
    PORT = "COM5"
    BAUD_RATE = 115200
    MB_ADDRESS = 1

    parameters = {"Fault clear": 1,
                  "Control command source": 0,
                  "Speed regulator mode": 0,
                  "Remote maximum motoring current": REMOTE_MOTORING_CURRENT,
                  "Remote maximum braking current": REMOTE_BRAKING_CURRENT,
                  "Remote speed command": REMOTE_SPEED_COMMAND,
                  "Regeneration battery current limit": 100,
                  "Remote comm loss braking current limit": 1}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)

    # BAC2BAC：
    # driver = ASIController("COM8", 115200, 1, "")
    # brake  = ASIController("COM6", 115200, 1, "")

    # init dyno, set timing params, and start logging
    sleep(1)

    ################# Watchdog Start ##########################
    watchdog.dut.stop_remote_motor()
    watchdog.dut.clear_faults()

    print("TC 10.5 tests starting!")
    # Logging start!
    # dyno.start_logging(1)
    # print("Logging start!")
    # startTime = datetime.now()
    # print("tests Started at " + str(startTime.time().isoformat()))

    # Starting motor to reach steady state
    watchdog.dut.turn_off_communication_timeout()

    watchdogInt = 0.2
    print("Watchdog interval: " + str(watchdogInt) + "s")

    print("Motor reaching SS in " + str(watchdogInt * 50) + "s")
    watchdog.run_for(watchdogInt, 25)

    # Part 1: Motor remains running during slow com
    print("Changing Timeout Threshold!")
    watchdog.update_timeout(500, 450)

    print("Part 1 Started at " + str(datetime.now().time().isoformat()))
    print("Motor will hold for " + str(watchdogInt * 50) + "s")
    watchdog.run_for(watchdogInt, 25)

    # Part 2: Com loss
    print("Changing Timeout Threshold!")
    watchdog.update_timeout(300, 150)

    print("Part 2 Started at " + str(datetime.now().time().isoformat()))
    watchdog.run_till_fault(watchdogInt, 20)
    ################### Watchdog End ######################
    # sleep(1)
    # input("Press Enter to stop logging and quit...")
    # endTime = datetime.now()
    # delta = endTime - startTime
    # print("TC 10.5 tests duration: " + str(delta.total_seconds()) + " seconds")
    # dyno.stop_logging()
