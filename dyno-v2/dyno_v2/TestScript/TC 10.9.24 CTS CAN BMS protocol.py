# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.21 CTS CAN BMS Protocol
PORT = "COM5"
BAUD_RATE = 115200
MB_ADDRESS = 1
params_2_check = {1: {"battery state of charge": 42,
                      "remote maximum battery current limit": 103.4,
                      "remote maximum regen battery current limit": 75.5,
                      "battery temperature": 39},
                  2: {"battery state of charge": 80,
                      "remote maximum battery current limit": 100,
                      "remote maximum regen battery current limit": 90,
                      "battery temperature": 23}}
# def wait_for(time):
#     wait_start = datetime.now()
#     waiting = True
#     while waiting:
#         if (datetime.now() - wait_start).total_seconds() < time:
#             sleep(1)
#         else:
#             waiting = False


if __name__ == "__main__":
    parameters = {"Battery management interface type": 9,  # CTS
                  "CTS Battery Comm Timeout": 2250}  # ms
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.clear_faults()
    watchdog.dut.turn_off_communication_timeout()
    print("Battery management interface type and timeout updated")
    print("Make sure PCAN-View is connected and transmitting Test 1 messages")

    def end_of_test():
        # End of test
        watchdog.restore_parameters()
        watchdog.dut.save_to_flash()


    input("Power cycle and press Enter to continue")
    print("Initialization successful!")

    # Test 1
    print("Checking for Test 1")
    for p in params_2_check[1]:
        read_value = watchdog.dut.read(p)
        if read_value * 0.95 <= params_2_check[1][p] <= read_value * 1.05:
            print(f"PASSED: {p} = {read_value} in range")
        else:
            print(f"FAILED: {p} = {read_value} not in range")
            exit("FAILED: Test 1")

    print("PASSED: Test 1")

    print("Resume Test 2 messages and pause Test 1 messages")
    input("Press Enter to continue")

    # Test 2
    print("Checking for Test 1")
    for p in params_2_check[2]:
        read_value = watchdog.dut.read(p)
        if read_value * 0.95 <= params_2_check[2][p] <= read_value * 1.05:
            print(f"PASSED: {p} = {read_value} in range")
        else:
            print(f"FAILED: {p} = {read_value} not in range")
            exit("FAILED: Test 2")

    print("PASSED: Test 2")

    end_of_test()
    print("PASSED: CTS CAN BMS Protocol Validation Finished")