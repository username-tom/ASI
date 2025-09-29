# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.12 Cruise Control
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

# def wait_for(time):
#     wait_start = datetime.now()
#     waiting = True
#     while waiting:
#         if (datetime.now() - wait_start).total_seconds() < time:
#             sleep(1)
#         else:
#             waiting = False


if __name__ == "__main__":
    parameters = {"Control command source": 1,  # Throttle
                  "Speed regulator mode": 0,  # Speed
                  "Throttle sensor source": 0,  # Throttle Voltage
                  "Throttle off voltage": 1,  # V
                  "Throttle full voltage": 4,  # V
                  "RPM Limit": 0,
                  "Cruise Enable Source": 1 << 5,  # brake 1
                  "Cruise Motoring Torque Limit": 10,  # %
                  "Cruise Braking Torque Limit": 10,  # %
                  "Minimum Cruise Speed": 5,  # km/h
                  "Cruise Input Mode": 1,  # switch
                  "Cruise Disengage Increase Threshold": 10,  # %
                  "Features4": 1 << 14}  # Cruise Control
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()


    def end_of_test():
        # End of test
        watchdog.restore_parameters()


    print("Initialization successful!")

    # Test 1
    print("Bring motor up to 5km/h")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.read("vehicle speed") <= 5:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: Vehicle speed in range")
    cruise_setpoint = watchdog.dut.read('throttle voltage')

    print("Engaging Cruise Control\nConnect Brake 1 to 5V EXT")

    start_time = datetime.now()
    while (int(watchdog.dut.read("controller flags2")) & (1 << 1)) >> 1 == 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before Cruise Control is enabled!")
            end_of_test()
            exit()
    print("PASSED: Cruise Control Engaged")

    # Check cruising
    print("Checking cruising")
    print("Release throttle...")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.read("throttle voltage") >= 1:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before throttle is released!")
            end_of_test()
            exit()

    for i in range(5):
        if watchdog.dut.read('vehicle speed') > 5:
            print("PASSED: Vehicle speed in range")
            sleep(1)
        else:
            print("FAILED: Vehicle speed out of range")
            end_of_test()
            exit()
    print("PASSED: Cruise Control working as intended")
    print("Test 1 PASSED!")

    # Test 2
    cruise_current = watchdog.dut.read('motor current')
    print("Apply load by holding onto the motor")

    # Wait for motor current increase
    start_time = datetime.now()
    while watchdog.dut.read("motor current") <= cruise_current + 1:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before load is detected!")
            end_of_test()
            exit()

    print("Load on motor detected!")
    sleep(1)
    print("Checking speed")
    # Wait for motor steady state
    start_time = datetime.now()
    while 4 <= watchdog.dut.read("vehicle speed") <= 6:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: Vehicle speed in range")
    print("Test 2 PASSED!")

    # Test 3
    print("Move throttle past Cruise Disengage Increase Threshold")
    start_time = datetime.now()
    while watchdog.dut.read("throttle voltage") <= 1.1 * cruise_setpoint:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("Throttle setpoint in range")

    print("Checking if Cruise Control is still engaged")
    start_time = datetime.now()
    while (int(watchdog.dut.read("controller flags2")) & (1 << 1)) >> 1 != 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before Cruise Control is disabled!")
            end_of_test()
            exit()
    print("PASSED: Cruise Control Disengaged")
    print("Test 3 PASSED!")


    end_of_test()
    print("PASSED: Cruise Control Test Finished")