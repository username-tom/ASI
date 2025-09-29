# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.17 Bi-directional Throttle
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Control command source": 1,  # Throttle
                  "Speed regulator mode": 0,  # Speed
                  "Throttle sensor source": 0,  # Throttle Voltage
                  "Throttle off voltage": 1,  # V
                  "Throttle full voltage": 4,  # V
                  "Bidirectional Throttle Deadband": 0.2,  # V
                  "Bidirectional Throttle Midpoint": 2.5,  # V
                  "Reverse_Enable_Source": 4,  # bidirectional throttle
                  "Features4": 2048,  # 0000 1000 0000 0000
                  "Features": 1 << 1}  # enable reverse
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()


    def end_of_test():
        # End of test
        watchdog.restore_parameters()


    watchdog.dut.clear_faults()
    watchdog.dut.save_to_flash()
    input("Power cycle and press Enter to continue")

    print("Initialization successful!")

    # Check midpoint
    print("Checking midpoint")
    throttle = watchdog.dut.read("throttle setpoint")
    print(f'Throttle Setpoint: {throttle}')
    if throttle == 0:
        print("PASSED: Throttle setpoint is 0")
    else:
        print("FAILED: Throttle setpoint is not 0")
        end_of_test()
        exit()

    # Check forward
    print("Checking forward")
    print("Move throttle to forward range")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() <= 50:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: RPM in range")

    print("Move throttle back to midpoint")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() != 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: forward is working")

    # Check reverse
    print("Checking reverse")
    print("Move throttle to reverse range")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() >= -50:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: RPM in range")

    print("Move throttle back to midpoint")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() != 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: Bidirectional Throttle with reverse is working")

    # Checking regen brake
    watchdog.dut.write("Features", (1 << 4))
    watchdog.dut.write("Regen brake speed", 5)
    sleep(1)

    # Check forward
    print("Checking forward")
    print("Move throttle to forward range")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() <= 50:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: RPM in range")

    print("Move throttle back to midpoint")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() != 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: forward is working")

    # Check reverse
    print("Checking reverse")
    print("Move throttle to reverse range")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() >= 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: RPM in range")

    print("Move throttle back to midpoint")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() != 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: Bidirectional Throttle with regen brake is working")

    # Checking reverse & regen brake
    watchdog.dut.write("Features", (1 << 4) + (1 << 1))
    watchdog.dut.write("Regen brake speed", 5)
    sleep(1)

    # Check forward
    print("Checking forward")
    print("Move throttle to forward range")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() <= 50:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: RPM in range")

    print("Move throttle back to midpoint")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() != 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: forward is working")

    # Check reverse
    print("Checking reverse")
    print("Move throttle to reverse range")

    # Wait for motor steady state
    start_time = datetime.now()
    while watchdog.dut.get_rpm() >= 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: RPM in range")

    print("Move throttle back to midpoint")
    start_time = datetime.now()
    while watchdog.dut.get_rpm() != 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(1)
        else:
            print("FAILED: TIMEOUT before RPM in range!")
            end_of_test()
            exit()
    print("PASSED: Bidirectional Throttle with both reverse & regen brake is working")

    end_of_test()
    print("PASSED: Bi-directional Throttle Test Finished")
