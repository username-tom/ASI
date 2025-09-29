# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.21 RPM Foldback
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Control command source": 0,  # Remote
                  "Speed regulator mode": 0,  # Speed
                  "Motor RPM Foldback End %": 60,  # % of rated rpm
                  "Motor RPM Foldback Start %": 50,  # % of rated rpm
                  "Motor features": 1 << 6}  # RPM Foldback
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    sleep(5)


    def end_of_test():
        # End of test
        watchdog.restore_parameters()


    print("Initialization successful!")

    # Test 1
    print("Test 1")
    watchdog.dut.remote_speed_mode(speed_command=100)

    sleep(2)

    if 0.55 * watchdog.dut.read("Rated motor speed") <= \
            watchdog.dut.get_rpm() <= \
            0.65 * watchdog.dut.read("Rated motor speed"):
        print("PASSED: RPM foldback is keeping RPM in range")
    else:
        print("FAILED: RPM foldback failed to keep RPM in range")

    print()

    watchdog.dut.write("Motor RPM Foldback End %", 70)

    sleep(2)

    if 0.65 * watchdog.dut.read("Rated motor speed") <= \
            watchdog.dut.get_rpm() <= \
            0.75 * watchdog.dut.read("Rated motor speed"):
        print("PASSED: RPM foldback is keeping RPM in range")
    else:
        print("FAILED: RPM foldback failed to keep RPM in range")

    print("Test 1: PASSED!")

    # Test 2
    print("Test 2")

    watchdog.dut.write("Motor RPM Foldback End %", 60)

    sleep(2)
    ref_rpm = watchdog.dut.get_rpm()

    print("Apply load to motor")
    sleep(5)
    ref_rpm_diff = watchdog.dut.get_rpm()

    input("Release load and press Enter")

    watchdog.dut.write("Motor RPM Foldback Start %", 20)

    sleep(2)
    if ref_rpm * 0.9 <= watchdog.dut.get_rpm() <= 1.1 * ref_rpm:
        print("RPM in range")
    else:
        print("RPM not in range")
        end_of_test()
        exit()

    print("Apply same load to motor")
    sleep(5)

    if watchdog.dut.get_rpm() < ref_rpm_diff:
        print("RPM in range")
    else:
        print("RPM not in range")
        end_of_test()
        exit()

    input("Release load and press Enter")

    end_of_test()
    print("PASSED: RPM Foldback Test Finished")