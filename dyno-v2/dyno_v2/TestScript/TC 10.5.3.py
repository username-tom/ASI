# ASI Includes
from dyno_v2.Module.ASIDynoModule import ASIDynoModule
from dyno_v2.Module.yokogawa_WT1806 import Yokogawa_WT1806
from dyno_v2.Module.abb_acs800 import AbbAcs800
from dyno_v2.Module.asi_controller import ASIController

from time import sleep
from datetime import datetime

if __name__ == "__main__":
    # TUNABLES:
    peakCurrent: float = 75  # rated current in Amps RMS, from product datasheet
    opSpeed = 1500  # RPM

    SSTime = 50  # minutes. If torque has been stable for this long, unit has reached thermal SS
    SSTol: float = 0.05  # consider values within this % of target to have settled, 0.0-1.0  = 0-100%
    RPMTol: float = 0.01  # speed control has failed if we're below target by this %, 0.0-1.0  = 0-100%
    testTime = 60  # minutes, test max time, will end after this
    tPID = 0.5  # PID loop update time, seconds

    # instruments on their addresses:
    # Yoko：
    yoko = Yokogawa_WT1806("192.168.1.242", file=f"C:\\Users\\twu\\PycharmProjects\\dyno-v2\\dyno_v2\\yoko_parameter_information.csv")
    # ABB = AbbAcs800(port='COM5', baud=19200, auto=True)
    # dut = ASIController("COM12", 115200, 1, "")

    # BAC2BAC：
    driver = ASIController("COM15", 115200, 1, "", root="C:\\Users\\twu\\PycharmProjects\\dyno-v2")
    brake  = ASIController("COM16", 115200, 1, "", root="C:\\Users\\twu\\PycharmProjects\\dyno-v2")

    # init dyno, set timing params, and start logging
    sleep(1)
    dyno = ASIDynoModule(driver, yoko, brake,
                         log_folder="C:/DynoResults/TC 10.5.3/")

    # Placeholder. Copy from TC 10.5.4

    ################# Watchdog Start ##########################
    # init variables
    REMOTE_SPEED_COMMAND = 50  # Remote speed command (490)
    REMOTE_MOTORING_CURRENT = 100  # Remote motoring current (491)
    REMOTE_BRAKING_CURRENT = 100  # Remote braking current (492)

    dyno.devices[1].stop_remote_motor()
    dyno.devices[1].clear_faults()
    dyno.devices[1].write("Remote maximum motoring current", REMOTE_MOTORING_CURRENT)
    print("Remote maximum motoring current set!")
    dyno.devices[1].write("Remote maximum braking current", REMOTE_BRAKING_CURRENT)
    print("Remote maximum braking current set!")
    dyno.devices[1].write("Remote speed command", REMOTE_SPEED_COMMAND)
    print("Remote speed command set!")
    dyno.devices[1].write("Regeneration battery current limit", 100)
    print("Regeneration battery current limit set!")
    dyno.devices[1].write("Remote comm loss braking current limit", 1)
    print("Remote comm loss braking current limit set!")

    print("TC 10.5 tests starting!")
    # Logging start!
    dyno.start_logging(1)
    print("Logging start!")
    startTime = datetime.now()
    print("tests Started at " + str(startTime.time().isoformat()))

    # Starting motor to reach steady state
    dyno.devices[1].turn_off_communication_timeout()

    watchdogInt = 0.2
    print("Watchdog interval: " + str(watchdogInt) + "s")

    print("Motor reaching SS in " + str(watchdogInt * 50) + "s")
    for i in range(25):
        dyno.devices[1].write("Remote state command", 258)  # Toggle high bit off
        sleep(watchdogInt)
        dyno.devices[1].write("Remote state command", 514)  # Toggle high bit on
        sleep(watchdogInt)

    # Part 1: Motor remains running during slow com
    print("Changing Timeout Threshold!")
    dyno.devices[1].write("Command timeout threshold", 500)
    print("Command timeout threshold set to 500ms!")
    dyno.devices[1].write("Average Command timeout threshold", 450)
    print("Average Command timeout threshold set to 450ms!")

    print("Part 1 Started at " + str(datetime.now().time().isoformat()))
    print("Motor will hold for " + str(watchdogInt * 50) + "s")
    for i in range(25):
        dyno.devices[1].write("Remote state command", 258)  # Toggle high bit off
        sleep(watchdogInt)
        dyno.devices[1].write("Remote state command", 514)  # Toggle high bit on
        sleep(watchdogInt)

    # Part 2: Com loss
    print("Changing Timeout Threshold!")
    dyno.devices[1].write("Command timeout threshold", 300)
    print("Command timeout threshold set to 300ms!")
    dyno.devices[1].write("Average Command timeout threshold", 150)
    print("Average Command timeout threshold set to 150ms!")

    print("Part 2 Started at " + str(datetime.now().time().isoformat()))
    for i in range(20):
        dyno.devices[1].write("Remote state command", 258)  # Toggle high bit off
        sleep(watchdogInt)
        dyno.devices[1].write("Remote state command", 514)  # Toggle high bit on
        sleep(watchdogInt)
        if dyno.devices[1].read("controller status") == 4:
            print("Motor stopping after " + str((1 + i) * 2 * watchdogInt) + "s")
            break
    ################### Watchdog End ######################
    sleep(1)
    input("Press Enter to stop logging and quit...")
    endTime = datetime.now()
    delta = endTime - startTime
    print("TC 10.5 tests duration: " + str(delta.total_seconds()) + " seconds")
    dyno.stop_logging()
