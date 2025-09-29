# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.13 Input Mapping to Available Power
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

def wait_for(time):
    wait_start = datetime.now()
    waiting = True
    while waiting:
        if (datetime.now() - wait_start).total_seconds() < time:
            sleep(1)
        else:
            waiting = False


if __name__ == "__main__":
    parameters = {"Control command source": 1,  # Throttle
                  "Speed regulator mode": 1,  # torque
                  "Remote Throttle Voltage": 1,
                  "Throttle sensor source": 5,  # Network
                  "Throttle off voltage": 1,
                  "Throttle full voltage": 4,
                  "Features4": 1024,  # 0000 0100 0000 0000
                  "Battery current limit": 1}  # %
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()


    def end_of_test():
        # End of test
        watchdog.restore_parameters()


    print("Initialization successful!")

    # Check mapping to available power
    print("Setting Remote Throttle Voltage to 2.5V")
    watchdog.dut.write("Remote Throttle Voltage", 2.5)

    # Wait for motor steady state
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()

    start_time = datetime.now()
    while watchdog.dut.get_rpm() <= 150:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM is in range")
            end_of_test()
            exit()
    print("PASSED: RPM is in range")

    # Stopping motor
    print("Setting Remote Throttle Voltage to 1V")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    # Check without mapping to available power
    print("Disabling Input Scaled to Available Power")
    watchdog.dut.write("Features4", 0)

    # Running motor
    print("Setting Remote Throttle Voltage to 2.5V")
    watchdog.dut.write("Remote Throttle Voltage", 2.5)

    # Wait for motor steady state
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()

    start_time = datetime.now()
    while watchdog.dut.get_rpm() <= 280:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM is in range")
            end_of_test()
            exit()
    print("PASSED: RPM is in range")

    # Stopping motor
    print("Setting Remote Throttle Voltage to 1V")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    end_of_test()
    print("PASSED: Input Mapping to Available Power Test Finished")