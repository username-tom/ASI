# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.12 Shared Regen and Cutoff Brake Input
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
                  "Analogue brake off voltage": 0,
                  "Analogue brake full voltage": 5,
                  "Cutoff brake sensor source": 0,  # Brake 1
                  "Regen brake source": 1,  # Brake 1
                  "Features4": 16,  # 0000 0000 0001 0000
                  "Features": 1 << 4, # enable regen brake
                  "Regen brake speed": 10,  # km/h
                  "Vehicle Speed threshold for Regen and Cutoff": 8}  # km/h
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    # watchdog.dut.save_to_flash()


    def end_of_test():
        # End of test
        watchdog.restore_parameters()
        # watchdog.dut.save_to_flash()
        # print("Power cycle to restore parameters...")

    # input("Power cycle and press Enter to continue...")
    print("Initialization successful!")

    # Bring motor up to steady state
    print("Use Throttle to bring motor above 10 kph")
    start_time = datetime.now()
    while watchdog.dut.read('vehicle speed') < 10:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before vehicle speed get to 10 kph!")
            end_of_test()
            exit()

    # Wait for motor steady state
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()

    print("Apply 5V to Brake 1")

    print("Gradually reduce throttle and reduce vehicle speed to below 8 kph")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() > 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            print(f"vehicle speed: {watchdog.dut.read('vehicle speed')}", end='\r')
            sleep(1)
        else:
            print("FAILED: TIMEOUT before brakes stopping the motor!")
            end_of_test()
            exit()
    print("PASSED: Shared Regen and Cutoff brake is functional")

    end_of_test()
    print("PASSED: Shared Regen and Cutoff Brake Input Test Finished")