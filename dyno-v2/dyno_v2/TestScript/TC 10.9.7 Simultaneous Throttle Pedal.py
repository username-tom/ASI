# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep
from datetime import datetime

# COM & Motor parameters for TC 10.9.7 Simultaneous Throttle Speed Pedal Torque Mode
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

if __name__ == "__main__":
    parameters = {"Control command source": 4,  # Throttle & Pedal
                  "Speed regulator mode": 0,  # Speed
                  "Remote Throttle Voltage": 1,
                  "Throttle sensor source": 5,  # Network
                  "Throttle off voltage": 1,
                  "Throttle full voltage": 4,
                  "Features4": 4}  # 0000 0000 0000 0100
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()

    def end_of_test():
        # End of test
        watchdog.restore_parameters()

    print("Initialization successful!")

    # Check throttle speed mode
    print("Setting Remote Throttle Voltage to 2")
    watchdog.dut.write("Remote Throttle Voltage", 2)
    sleep(1)

    # Check Speed regulator mode
    mode = watchdog.dut.read("Speed regulator mode")
    if mode == 0:
        print("PASSED: Throttle -> Speed Mode")
    else:
        print(f"FAILED: Throttle did not change speed regulator mode [{mode}]!")
        end_of_test()
        exit()

    # Throttle back to off
    print("Setting Remote Throttle Voltage to 1")
    watchdog.dut.write("Remote Throttle Voltage", 1)
    sleep(1)

    # Check pedal torque mode
    print("Start pedalling...")
    start_time = datetime.now()
    while watchdog.dut.read("Speed regulator mode") != 2:
        if (datetime.now() - start_time).total_seconds() < 30 and watchdog.dut.get_rpm() == 0:
            sleep(1)
        else:
            print("FAILED: TIMEOUT on pedal torque mode")
            end_of_test()
            exit()
    print('PASSED: Pedal -> Torque with Speed Limit Mode')

    end_of_test()
    print("PASSED: Simultaneous Throttle Speed Pedal Torque Mode Test Finished")