# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.31 Configurable Voltage Rail Gain
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS)
    watchdog.dut.clear_faults()


    def end_of_test():
        # End of test
        watchdog.dut.write("Analog Input Gain - Internal Voltage Rail ", original_voltage_gain)
        watchdog.dut.set_access_level(2)
        watchdog.dut.write("Level 2 HW bits", 0)  # Variable internal rail voltage gain
        watchdog.dut.set_access_level(0)

    def test_failed(msg=""):
        print(msg)
        end_of_test()
        exit()


    print("Initialization successful!\n")
    sleep(1)

    # Test 1
    print("Test 1")
    print("Reading original voltage gain")
    original_voltage_gain = watchdog.dut.read("Analog Input Gain - Internal Voltage Rail ")
    original_voltage = watchdog.dut.read("internal rail voltage")

    print("Enabling feature")
    watchdog.dut.set_access_level(2)
    watchdog.dut.write("Level 2 HW bits", 1 << 6)

    print("Overwriting voltage gain")
    watchdog.dut.write("Analog Input Gain - Internal Voltage Rail ", original_voltage_gain - 0.1)
    sleep(1)

    if original_voltage > watchdog.dut.read("internal rail voltage"):
        print("PASSED: New internal rail voltage in range")
    else:
        test_failed("FAILED: Internal rail voltage not in range")


    # Test 2
    print("Test 2")
    print("Disabling feature")
    watchdog.dut.write("Level 2 HW bits", 0)
    sleep(1)

    if original_voltage * 0.99 <= watchdog.dut.read("internal rail voltage") <= original_voltage * 1.01:
        print("PASSED: Internal rail voltage in range")
    else:
        test_failed(f"FAILED: Internal rail voltage not in range [{watchdog.dut.read('internal rail voltage')}]")

    end_of_test()

    print("\nPASSED: Configurable Voltage Rail Gain Test Finished")