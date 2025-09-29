# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime
from threading import Thread


# COM & Motor parameters for TC 10.9.3 Flash Parameter Locking
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1
ACCESS_CODE = 0x10

if __name__ == "__main__":
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS)

    def end_of_test():
        # End of test
        watchdog.dut.set_access_level(3)
        if watchdog.dut.firmware > 6.021:
            for i in range(3):
                watchdog.dut.write(f"Flash parameter read access code {i + 1}", 0)
        else:
            watchdog.dut.write("Flash parameter read access code", 0)
        watchdog.dut.save_to_flash()

    # Reset if device already have parameter locks enabled
    if watchdog.dut.read("Baud rate") == 0:
        print("Resetting parameters")
        end_of_test()
        input("Power cycle and press Enter to continue")

    print("Initialization successful!")

    print("Test Started\n")

    # Check locking parameters
    print(f"Setting Flash parameter read access code to {ACCESS_CODE:04x}")
    if watchdog.dut.firmware > 6.021:
        watchdog.dut.write("Flash parameter read access code 1", ACCESS_CODE)
    else:
        watchdog.dut.write("Flash parameter read access code", ACCESS_CODE)
    sleep(1)
    watchdog.dut.save_to_flash()
    input("Power cycle and press Enter to continue")

    # Check lock
    print("Checking lock")
    if watchdog.dut.read("Baud rate") == 0:
        print("PASSED: Parameters locked!\n")
    else:
        print(f"FAILED: Parameters not locked!")
        end_of_test()
        exit()

    # Check exemptions
    print("Checking exemptions")
    if watchdog.dut.read("software revision level") == watchdog.dut.firmware:
        print("PASSED: Exemptions working!\n")
    else:
        print(f"FAILED: Exemptions not working!")
        end_of_test()
        exit()

    # Check writing to locked parameters
    print("Setting CAN ID to 1")
    watchdog.dut.write("CAN ID", 1)
    if watchdog.dut.read("CAN ID") == 0:
        print("PASSED: Writing locked!\n")
    else:
        print(f"FAILED: Lock not working!")
        end_of_test()
        exit()

    # Check unlock
    print("Checking unlock")
    watchdog.dut.write("Parameter read access code 1", ACCESS_CODE)
    if watchdog.dut.read("Baud rate") == 115200:
        print("PASSED: Parameters unlocked!\n")
    else:
        print(f"FAILED: Parameters not unlocked!")
        end_of_test()
        exit()

    # Check access level 3
    print("Checking access level overwrite")
    watchdog.dut.write("Parameter read access code 1", 0)
    watchdog.dut.set_access_level(3)
    if watchdog.dut.read("Baud rate") == 115200:
        print("PASSED: Parameters unlocked!\n")
    else:
        print(f"FAILED: Parameters not unlocked!")
        end_of_test()
        exit()

    # Check resetting parameter lock
    watchdog.dut.set_access_level(0)
    watchdog.dut.write("Parameter read access code 1", ACCESS_CODE)
    watchdog.dut.write("Flash parameter read access code 1", 0)
    watchdog.dut.save_to_flash()

    input("Power cycle and press Enter to continue")
    if watchdog.dut.read("Baud rate") == 115200:
        print("PASSED: Parameter lock reset!\n")
    else:
        print(f"FAILED: Parameters still locked!")
        end_of_test()
        exit()


    end_of_test()
    print("PASSED: Flash Parameter Lock Test Finished\nPower cycle to reset parameters")