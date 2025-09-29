# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.7 Simultaneous Throttle Speed Pedal Torque Mode
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
                  "Speed regulator mode": 0,  # Speed
                  "Remote Throttle Voltage": 1,
                  "Throttle sensor source": 5,  # Network
                  "Throttle off voltage": 1,
                  "Throttle full voltage": 4,
                  "Shared Motor Temp and Wheel speed timeout": 5000,  # ms
                  "voltage threshold for shared digital input + motor temperature source": 4,  # V
                  "Motor features": 16,  # 0000 0000 0001 0000
                  "Motor temperature source": 1}  # Brake 1
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Enabling Motor Temperature")
    feature = int(watchdog.dut.read("Features"))


    def end_of_test():
        # End of test
        watchdog.restore_parameters()


    if (feature & (1 << 5)) >> 5 == 0:
        watchdog.dut.write("Features", feature + (1 << 5))
    sleep(1)

    print("Initialization successful!")

    # Check pulses on Brake 1 can change motor temperature
    original_temp = watchdog.dut.read("motor temperature")
    print(f'Motor temperature: {original_temp}')
    print("Apply 5V to Brake 1 repeatedly")
    start_time = datetime.now()
    while watchdog.dut.read("motor temperature") == original_temp:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before a motor temperature change is detected!")
            end_of_test()
            exit()
    print("PASSED: Motor temperature changed")

    # Check Shared Motor Temp and Wheel speed timeout
    print("Setting Remote Throttle Voltage to 2V")
    watchdog.dut.write("Remote Throttle Voltage", 2)

    # Wait for motor steady state
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()

    print("Disconnect 5V to Brake 1")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() > 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before Shared Motor Temp and Wheel speed timeout is applied!")
            end_of_test()
            exit()
    print("PASSED: Shared Motor Temp and Wheel speed timeout is functional")

    end_of_test()
    print("PASSED: Common Wheel Speed/Motor Temperature Input Feature Test Finished")