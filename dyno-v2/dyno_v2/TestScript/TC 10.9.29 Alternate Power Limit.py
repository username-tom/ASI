# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.29 Alternate Power Limit
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Rated motor power (Race mode PAS power)": 350,  # W
                  "Rated motor power (Race mode Throttle power)": 300,  # W
                  "Rated motor power (Street mode PAS power)": 250,  # W
                  "Rated motor power (Street mode Throttle power)": 200,  # W
                  "Alternate power switch source": 4,  # Remote digital commands
                  "Battery current limit": 100,  # %
                  "Regeneration battery current limit": 10,  # 10
                  "Control command source": 1,  # throttle
                  "Throttle sensor source": 5,  # remote
                  "Remote Throttle Voltage": 1,  # V
                  "Remote Digital Commands": 0,  # for reset
                  "Features": 1 << 10,  # Alternate power limit enabled
                  "Features5": 1 << 2}  # Alternate Battery Limits
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.clear_faults()
    sleep(5)


    def end_of_test():
        # End of test
        watchdog.restore_parameters()

    def test_failed(msg=""):
        print(msg)
        end_of_test()
        exit()


    print("Initialization successful!\n")
    sleep(1)

    # Test 1
    print("Test 1")
    print("Race mode PAS")
    # Check calculated limits
    if watchdog.dut.read("calculated battery current braking limit") == 0.8750:
        print("PASSED: Race mode PAS braking limit in range")
    else:
        test_failed("FAILED: Race mode PAS braking limit not in range")

    if watchdog.dut.read("calculated battery current motoring limit") == 9.625:
        print("PASSED: Race mode PAS motoring limit in range")
    else:
        test_failed("FAILED: Race mode PAS motoring limit not in range")

    sleep(1)

    # Test 2
    print("Test 2")
    print("Race mode throttle")
    watchdog.dut.write("Remote Throttle Voltage", 2)  # V
    sleep(1)
    # Check calculated limits
    if watchdog.dut.read("calculated battery current braking limit") == 0.750:
        print("PASSED: Race mode PAS braking limit in range")
    else:
        test_failed("FAILED: Race mode PAS braking limit not in range")

    if watchdog.dut.read("calculated battery current motoring limit") == 8.25:
        print("PASSED: Race mode PAS motoring limit in range")
    else:
        test_failed("FAILED: Race mode PAS motoring limit not in range")

    watchdog.dut.write("Remote Throttle Voltage", 1)  # V
    sleep(1)

    # Test 3
    print("Test 3")
    print("Street mode PAS")
    watchdog.dut.write("Remote Digital Commands", 1 << 6)  # alt power
    # Check calculated limits
    if watchdog.dut.read("calculated battery current braking limit") == 0.625:
        print("PASSED: Race mode PAS braking limit in range")
    else:
        test_failed("FAILED: Race mode PAS braking limit not in range")

    if watchdog.dut.read("calculated battery current motoring limit") == 6.875:
        print("PASSED: Race mode PAS motoring limit in range")
    else:
        test_failed("FAILED: Race mode PAS motoring limit not in range")

    sleep(1)

    # Test 4
    print("Test 4")
    print("Street mode throttle")
    watchdog.dut.write("Remote Throttle Voltage", 2)  # V
    sleep(1)
    # Check calculated limits
    if watchdog.dut.read("calculated battery current braking limit") == 0.5:
        print("PASSED: Race mode PAS braking limit in range")
    else:
        test_failed("FAILED: Race mode PAS braking limit not in range")

    if watchdog.dut.read("calculated battery current motoring limit") == 5.5:
        print("PASSED: Race mode PAS motoring limit in range")
    else:
        test_failed("FAILED: Race mode PAS motoring limit not in range")

    sleep(1)

    end_of_test()

    print("\nPASSED: Alternate Power Limit Test Finished")