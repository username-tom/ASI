# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.8 Low Speed Kp Ki
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    # Init Watchdog
    parameters = {"BETA: Low Speed Kp Value": 0,
                  "BETA: Low Speed Kp Start Threshold": 25,  # %
                  "BETA: Low Speed Kp End Threshold": 50,  # %
                  "BETA: Target Speed Ki Value": 0,
                  "BETA: Target Speed Ki Start Threshold": 25,  # %
                  "BETA: Target Speed Ki End Threshold": 50,  # %
                  "Control command source": 0,  # remote
                  "Features4": 3}  # low speed kp & target speed ki
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
    print("Running at 20% speed")
    watchdog.dut.remote_speed_mode(speed_command=20)
    sleep(5)

    if watchdog.dut.get_rpm() == 0:
        print("PASSED: motor is stopped")
    else:
        test_failed("FAILED: motor is moving")

    watchdog.dut.stop_remote_motor()

    # Test 2
    print("Test 2")
    parameters = {"BETA: Low Speed Kp Start Threshold": 0,  # %
                  "BETA: Low Speed Kp End Threshold": 25,  # %
                  "BETA: Target Speed Ki End Threshold": 25,  # %
                  "BETA: Target Speed Ki Start Threshold": 0}  # %
    watchdog.update_params(**parameters)
    print("Running at 50% speed")
    watchdog.dut.remote_speed_mode(speed_command=50)
    sleep(5)

    if watchdog.dut.get_rpm() > 0:
        print("PASSED: motor is moving")
    else:
        test_failed("FAILED: motor is stopped")

    watchdog.dut.stop_remote_motor()

    end_of_test()

    print("\nPASSED: Low Speed Kp Ki Test Finished")