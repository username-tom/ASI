# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.1.6 Motor Phase Disconnect
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Open Phase Fault Detection Threshold": 1}  # Amp
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.clear_faults()


    def end_of_test():
        # End of test
        watchdog.restore_parameters()
        watchdog.dut.set_access_level(1)
        watchdog.dut.write("Level 1 Features", 0)  # reset
        watchdog.dut.set_access_level(0)

    def test_failed(msg=""):
        print(msg)
        end_of_test()
        exit()


    watchdog.dut.set_access_level(1)
    watchdog.dut.write("Level 1 Features", 1 << 2)  # Open phase fault detection
    print("Initialization successful!\n")
    sleep(1)

    # Test 1
    print("Test 1")
    print("Disconnect Phase U")
    watchdog.dut.remote_speed_mode(speed=300)

    input("Disconnect Phase U and press Enter...")

    print("Put load on motor")

    # Wait for open phase fault
    start_time = datetime.now()
    while watchdog.check_bit_vector("faults2", 14, 0, False):
        if (datetime.now() - start_time).total_seconds() <= 30:
            print("Waiting for fault")
            sleep(1)
        else:
            test_failed(f"TIMEOUT: Failed to trigger fault")
    print("PASSED: Open phase fault triggered")

    input("Release load, reconnect phase U and press Enter")
    watchdog.dut.clear_faults()

    # Test 2
    print("Test 2")
    print("Disconnect Phase V")
    watchdog.dut.remote_speed_mode(speed=300)

    input("Disconnect Phase V and press Enter...")

    print("Put load on motor")

    # Wait for open phase fault
    start_time = datetime.now()
    while watchdog.check_bit_vector("faults2", 14, 0, False):
        if (datetime.now() - start_time).total_seconds() <= 30:
            print("Waiting for fault")
            sleep(1)
        else:
            test_failed(f"TIMEOUT: Failed to trigger fault")
    print("PASSED: Open phase fault triggered")

    input("Release load, reconnect phase V and press Enter")
    watchdog.dut.clear_faults()


    # Test 3
    print("Test 3")
    print("Disconnect Phase W")
    watchdog.dut.remote_speed_mode(speed=300)

    input("Disconnect Phase W and press Enter...")

    print("Put load on motor")

    # Wait for open phase fault
    start_time = datetime.now()
    while watchdog.check_bit_vector("faults2", 14, 0, False):
        if (datetime.now() - start_time).total_seconds() <= 30:
            print("Waiting for fault")
            sleep(1)
        else:
            test_failed(f"TIMEOUT: Failed to trigger fault")
    print("PASSED: Open phase fault triggered")

    input("Release load, reconnect phase W and press Enter")
    watchdog.dut.clear_faults()

    end_of_test()

    print("\nPASSED: Motor Phase Disconnect Test Finished")