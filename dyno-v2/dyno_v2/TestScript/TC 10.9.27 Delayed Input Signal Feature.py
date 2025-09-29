# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.27 Delayed Input Signal Feature
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Regen brake source": -1,  # none
                  "Cutoff brake sensor source": 4,  # remote
                  "Delayed Input Period": 3000,  # ms
                  "Delayed Input Source": (1 << 11),  # remote regen 1
                  "Delayed Input Destination": 1,  # Cut out
                  "Remote Digital Commands": 0,  # for reset
                  "Features5": 0}  # for reset
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.clear_faults()
    sleep(5)


    def end_of_test():
        # End of test
        watchdog.restore_parameters()
        watchdog.dut.set_access_level(2)
        watchdog.check_bit_vector("HW configuration vector", 9, 0)
        watchdog.dut.set_access_level(0)

    def test_failed(msg=""):
        print(msg)
        end_of_test()
        exit()


    print("Initialization successful!\n")
    sleep(1)

    # Test 1
    print("Test 1")
    # Check cut off is disabled
    if watchdog.check_bit_vector("controller flags", 1, 0, False):
        print("PASSED: Initial cut off status is OFF")
    else:
        test_failed("FAILED: Initial cut off status is ON! Please check parameter")

    sleep(1)

    print("Engage cut off")
    watchdog.dut.write("Remote Digital Commands", 1 << 7)  # regen 1
    for _ in range(4):
        if watchdog.check_bit_vector("controller flags", 1, 0, False):
            print("PASSED: Delaying... Cut off status is off")
        else:
            test_failed("FAILED: cut off status is ON prematurely!")

        sleep(0.5)

    sleep(2)
    print("Delay period over\nChecking cut off")
    # Check cut off is on
    if watchdog.check_bit_vector("controller flags", 1, 1, False):
        print("PASSED: Cut off status is ON")
    else:
        test_failed("FAILED: Cut off status is OFF!")

    # Check Remote Digital Commands cut off is on
    if watchdog.check_bit_vector("Remote Digital Commands", 0, 1, False):
        print("PASSED: Remote Digital Commands Cut off is ON")
    else:
        test_failed("FAILED: Remote Digital Commands Cut off is OFF!")

    # Test 2
    print("Test 2")
    print("Toggle remote regen 1 off")
    watchdog.dut.write("Remote Digital Commands", 1)
    sleep(1)

    # Check cut off is disabled
    if watchdog.check_bit_vector("controller flags", 1, 0, False):
        print("PASSED: Cut off status is OFF")
    else:
        test_failed("FAILED: Cut off status is ON!")

    # Test 3
    print("Test 3")
    print("Engage cut off")
    watchdog.dut.write("Remote Digital Commands", 1)  # regen 1
    for _ in range(2):
        if watchdog.check_bit_vector("controller flags", 1, 0, False):
            print("PASSED: Delaying... Cut off status is off")
        else:
            test_failed("FAILED: cut off status is ON prematurely!")

        sleep(0.5)

    print("Toggle remote regen 1 off before delay expired")
    watchdog.dut.write("Remote Digital Commands", 1)
    sleep(1)

    # Check cut off is disabled
    if watchdog.check_bit_vector("controller flags", 1, 0, False):
        print("PASSED: Cut off status remained OFF")
    else:
        test_failed("FAILED: Cut off status is ON!")

    # Test 4
    print("Test 4")
    print("Enabling latching")
    watchdog.dut.write("Features5", 1 << 3)

    print("Repeating Test 1")

    # Check cut off is disabled
    if watchdog.check_bit_vector("controller flags", 1, 0, False):
        print("PASSED: Initial cut off status is OFF")
    else:
        test_failed("FAILED: Initial cut off status is ON! Please check parameter")

    sleep(1)

    print("Engage cut off")
    watchdog.dut.write("Remote Digital Commands", 1 << 7)  # regen 1
    for _ in range(4):
        if watchdog.check_bit_vector("controller flags", 1, 0, False):
            print("PASSED: Delaying... Cut off status is off")
        else:
            test_failed("FAILED: cut off status is ON prematurely!")

        sleep(0.5)

    sleep(2)
    print("Delay period over\nChecking cut off")
    # Check cut off is on
    if watchdog.check_bit_vector("controller flags", 1, 1, False):
        print("PASSED: Cut off status is ON")
    else:
        test_failed("FAILED: Cut off status is OFF!")

    # Check Remote Digital Commands cut off is on
    if watchdog.check_bit_vector("Remote Digital Commands", 0, 1, False):
        print("PASSED: Remote Digital Commands Cut off is ON")
    else:
        test_failed("FAILED: Remote Digital Commands Cut off is OFF!")

    # Test 5
    print("Test 5")
    print("Toggle remote regen 1 off")
    watchdog.dut.write("Remote Digital Commands", 1)
    sleep(1)

    # Check cut off is on
    if watchdog.check_bit_vector("controller flags", 1, 1, False):
        print("PASSED: Cut off status remains ON")
    else:
        test_failed("FAILED: Cut off status is OFF!")

    # Test 6
    print("Test 6")
    print("Enabling inverted input")
    watchdog.dut.write("Features5", 1 << 4)
    watchdog.dut.set_access_level(2)
    watchdog.check_bit_vector("HW configuration vector", 9, 1)
    sleep(3)

    # Check cut off is on
    if watchdog.check_bit_vector("controller flags", 1, 1, False):
        print("PASSED: Cut off status is ON")
    else:
        test_failed("FAILED: Cut off status is OFF!")

    print("Toggle remote regen 1 on")
    watchdog.dut.write("Remote Digital Commands", 1 << 7)
    sleep(1)
    print(watchdog.check_bit_vector("controller flags", 1, 0, False))
    print("Toggle remote regen 1 off")
    watchdog.dut.write("Remote Digital Commands", 0)

    # Check cut-off is off
    if watchdog.check_bit_vector("controller flags", 1, 0, False):
        print("PASSED: Cut off status remains OFF")
    else:
        test_failed("FAILED: Cut off status is ON!")

    for _ in range(4):
        if watchdog.check_bit_vector("controller flags", 1, 0, False):
            print("PASSED: Delaying... Cut off status is OFF")
        else:
            test_failed("FAILED: cut off status is ON prematurely!")

        sleep(0.5)

    sleep(2)
    print("Delay period over\nChecking cut off")
    # Check cut-off turns on
    if watchdog.check_bit_vector("controller flags", 1, 1, False):
        print("PASSED: Cut off status is OFF")
    else:
        test_failed("FAILED: Cut off status is ON!")

    end_of_test()
    print("Power cycle to reset parameters\n")

    print("PASSED: Momentary Assist Mode & High-speed Vehicle Test Finished")