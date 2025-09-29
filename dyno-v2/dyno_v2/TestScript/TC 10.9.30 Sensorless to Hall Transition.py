# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.30 Sensorless to Hall Transition
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Sensorless closed loop enable frequency": 20,  # Hz
                  "Sensorless to Hall Transition Frequency": 10,  # Hz
                  "Motor position sensor type": 1,  # Hall start
                  "Control command source": 1,  # throttle
                  "Throttle sensor source": 5,  # remote
                  "Remote Throttle Voltage": 1}  # V
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
    print("< 20Hz")
    watchdog.dut.write("Remote Throttle Voltage", 1.9)
    sleep(5)
    # Wait for motor steady state
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < 30:
        if 10 < watchdog.dut.read("flux frequency") < 20:
            print("PASSED: Flux frequency in range")
            break
        else:
            print(f"Waiting for flux frequency to be in range "
                  f"[{watchdog.dut.read('flux frequency')}]")
        sleep(5)

    if (datetime.now() - start_time).total_seconds() >= 30:
        test_failed("FAILED: TIMEOUT before RPM in range!")

    if watchdog.check_bit_vector("controller flags2", 7, 0, False):
        print("PASSED: < 20Hz flux frequency kept controller in Hall mode")
    else:
        test_failed("FAILED: controller left Hall mode")


    # Test 2
    print("Test 2")
    print("> 20Hz")
    watchdog.dut.write("Remote Throttle Voltage", 2.2)
    sleep(5)
    # Wait for motor steady state
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < 30:
        if 20 < watchdog.dut.read("flux frequency") < 30:
            print("PASSED: Flux frequency in range")
            break
        else:
            print(f"Waiting for flux frequency to be in range "
                  f"[{watchdog.dut.read('flux frequency')}]")
        sleep(1)

    if (datetime.now() - start_time).total_seconds() >= 30:
        test_failed("FAILED: TIMEOUT before RPM in range!")

    if watchdog.check_bit_vector("controller flags2", 7, 1, False):
        print("PASSED: > 20Hz flux frequency moved controller to sensorless mode")
    else:
        test_failed("FAILED: controller still in Hall mode")

    # Test 3
    print("Test 3")
    print("> 10Hz")
    watchdog.dut.write("Remote Throttle Voltage", 1.85)
    sleep(5)
    # Wait for motor steady state
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < 30:
        if 10 < watchdog.dut.read("flux frequency") < 20:
            print("PASSED: Flux frequency in range")
            break
        else:
            print(f"Waiting for flux frequency to be in range "
                  f"[{watchdog.dut.read('flux frequency')}]")
        sleep(1)

    if (datetime.now() - start_time).total_seconds() >= 30:
        test_failed("FAILED: TIMEOUT before RPM in range!")

    if watchdog.check_bit_vector("controller flags2", 7, 1, False):
        print("PASSED: > 10Hz flux frequency kept controller to sensorless mode")
    else:
        test_failed("FAILED: controller in Hall mode")

    # Test 4
    print("Test 4")
    print("< 10Hz")
    watchdog.dut.write("Remote Throttle Voltage", 1.8)
    sleep(5)
    # Wait for motor steady state
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < 30:
        if watchdog.dut.read("flux frequency") < 10:
            print("PASSED: Flux frequency in range")
            break
        else:
            print(f"Waiting for flux frequency to be in range "
                  f"[{watchdog.dut.read('flux frequency')}]")
        sleep(1)

    if (datetime.now() - start_time).total_seconds() >= 30:
        test_failed("FAILED: TIMEOUT before RPM in range!")

    if watchdog.check_bit_vector("controller flags2", 7, 0, False):
        print("PASSED: < 10Hz flux frequency moved controller to Hall mode")
    else:
        test_failed("FAILED: controller still in sensorless mode")

    end_of_test()

    print("\nPASSED: Sensorless to Hall Transition Test Finished")