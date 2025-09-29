# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime
from threading import Thread


# COM & Motor parameters for TC 10.9.3 Flash Parameter Locking
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1
TIMEOUT = 30

if __name__ == "__main__":
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS)
    watchdog.dut.clear_faults()

    def end_of_test():
        # End of test
        watchdog.dut.write(f"Features4", 0)

    # Reset if device already have digital logic inversion enabled

    if int(watchdog.dut.read("Features4")) != 0:
        print("Resetting parameters")
        end_of_test()
        input("Power cycle and press Enter to continue")

    print("Initialization successful!")

    print("Test Started\n")

    # Check Brake 1 without feature
    print(f"Checking Brake 1 without inversion\nApply 5V to Brake 1")
    start_time = datetime.now()
    while (int(watchdog.dut.read("digital inputs")) & (1 << 5)) >> 5 == 0:
        if (datetime.now() - start_time).total_seconds() < TIMEOUT:
            sleep(1)
        else:
            print("FAILED: TIMEOUT on Brake 1 digital input")
            end_of_test()
            exit()
    print(f'PASSED: Brake 1 [{watchdog.dut.read("brake 1 voltage")}V] without inversion is GOOD\n')

    print("Disconnect Brake 1")
    start_time = datetime.now()
    while (int(watchdog.dut.read("digital inputs")) & (1 << 5)) >> 5 == 1:
        if (datetime.now() - start_time).total_seconds() < TIMEOUT:
            sleep(1)
        else:
            print("INTERRUPTED: TIMEOUT on disconnecting Brake 1 digital input")
            end_of_test()
            exit()
    print(f"Brake 1 - {watchdog.dut.read('brake 1 voltage')}V\nBrake 1 Disconnected")
    sleep(1)

    # Check Brake 1 with feature
    print(f"Checking Brake 1 with inversion")
    watchdog.dut.write(f"Features4", 1 << 5)
    sleep(1)
    print("Apply 5V to Brake 1")

    start_time = datetime.now()
    while (int(watchdog.dut.read("digital inputs")) & (1 << 5)) >> 5 == 1:
        if (datetime.now() - start_time).total_seconds() < TIMEOUT:
            sleep(1)
        else:
            print("FAILED: TIMEOUT on Brake 1 digital input")
            end_of_test()
            exit()
    print(f'PASSED: Brake 1 [{watchdog.dut.read("brake 1 voltage")}V] with inversion is GOOD\n')

    end_of_test()
    print("PASSED: Digital Input Inversion Test (shortened retest) Finished")