# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.6.1.1 Speed Mode Ramp Limit
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Control command source": 1,  # throttle
                  "Speed mode positive acceleration ramp": 1,  # rpm/s
                  "Speed mode Regen ramp": 0.1,  # rpm/s
                  "Throttle sensor source": 5,  # remote
                  "Remote Throttle Voltage": 1,  # V
                  "Speed regulator mode": 0}  # speed
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.clear_faults()


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
    print("Ramping up at low rate")
    watchdog.dut.write("Remote Throttle Voltage", 4)
    sleep(3)

    if watchdog.dut.get_rpm() < 500:
        print("PASSED: RPM in range")
    else:
        test_failed(f"FAILED: RPM out of range [{watchdog.dut.get_rpm()}]")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() < 1000:
        if (datetime.now() - start_time).total_seconds() <= 30:
            print("Waiting for motor to reach target RPM")
        else:
            test_failed(f"TIMEOUT: RPM not in range")
        sleep(5)


    # Test 2
    print("Test 2")
    print("Ramping down at low rate")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(3)

    if watchdog.dut.get_rpm() > 100:
        print("PASSED: RPM in range")
    else:
        test_failed(f"FAILED: RPM out of range [{watchdog.dut.get_rpm()}]")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() > 0:
        if (datetime.now() - start_time).total_seconds() <= 30:
            print("Waiting for motor to stop")
        else:
            test_failed(f"TIMEOUT: Motor still moving")
        sleep(5)


    # Test 3
    print("Test 3")
    print("Ramping up at high rate")
    parameters = {"Speed mode positive acceleration ramp": 20,  # rpm/s
                  "Speed mode Regen ramp": 20}  # rpm/s
    watchdog.update_params(**parameters)

    watchdog.dut.write("Remote Throttle Voltage", 4)
    sleep(3)

    if watchdog.dut.get_rpm() > 600:
        print("PASSED: RPM in range")
    else:
        test_failed(f"FAILED: RPM out of range [{watchdog.dut.get_rpm()}]")


    # Test 4
    print("Test 4")
    print("Ramping down at high rate")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(3)

    if watchdog.dut.get_rpm() < 50:
        print("PASSED: RPM in range")
    else:
        test_failed(f"FAILED: RPM out of range [{watchdog.dut.get_rpm()}]")

    end_of_test()

    print("\nPASSED: Speed mode Ramp Limit Test Finished")