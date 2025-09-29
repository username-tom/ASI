# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.26 Momemtary Assist Mode & High Speed Vehicle
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":
    parameters = {"Control command source": 1,  # Throttle
                  "Speed regulator mode": 0,  # Speed
                  "Throttle sensor source": 0,  # Throttle Voltage
                  "Assist mode source": 11,  # Momentary switch
                  "Momentary Assist Modes": 4,  # 0, 1, 2, 3
                  "Momentary Assist Source": 1 << 11,  # remote regen 1
                  "Features5": 1 << 1}  # high speed vehicle
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    sleep(5)


    def end_of_test():
        # End of test
        watchdog.restore_parameters()


    print("Initialization successful!")
    sleep(1)

    # Test 1
    print("Test 1")
    if watchdog.dut.read("assist level") == 0:
        print("Assist level is 0")
    else:
        print("FAILED: Assist level is not 0")
        end_of_test()
        exit()

    input("Press down throttle and press Enter")
    if watchdog.dut.get_rpm() == 0:
        print("PASSED: motor is stopped")
    else:
        print("FAILED: motor is not stopped")
        end_of_test()
        exit()

    input("\nRelease throttle and press Enter")

    # Test 2
    print("Test 2")
    print("Toggle remote regen 1 on")
    watchdog.dut.write("Remote Digital Commands", 1 << 7)

    print("Checking assist level...")
    if watchdog.dut.read("assist level") == 0:
        print("PASSED: Assist level remains at 0")
    else:
        print("FAILED: Assist level changed")
        end_of_test()
        exit()

    print("Toggle remote regen 1 off")
    watchdog.dut.write("Remote Digital Commands", 0)
    sleep(1)

    print("Checking assist level...")
    if watchdog.dut.read("assist level") == 0.5:
        print("PASSED: Assist level in range")
    else:
        print("FAILED: Assist level not in range")
        end_of_test()
        exit()

    input("Press down throttle and press Enter")
    if watchdog.dut.get_rpm() > 0:
        print("PASSED: motor is spinning")
    else:
        print("FAILED: motor is not spinning")
        end_of_test()
        exit()

    vehicle_speed = watchdog.dut.read("vehicle speed")
    high_speed = watchdog.dut.read("vehicle speed (high speed vehicle)")
    if 0.49 * high_speed <= vehicle_speed <= 0.51 * high_speed:
        print("PASSED: vehicle speed (hi & low) are in range")
    else:
        print("FAILED: vehicle speed not in range")
        end_of_test()
        exit()

    input("\nRelease throttle and press Enter")

    # Test 3
    print("Test 3")
    print("Toggle remote regen 1 on")
    watchdog.dut.write("Remote Digital Commands", 1 << 7)

    print("Checking assist level...")
    if watchdog.dut.read("assist level") == 0.5:
        print("PASSED: Assist level remains at 0.5")
    else:
        print("FAILED: Assist level changed")
        end_of_test()
        exit()

    print("Toggle remote regen 1 off")
    watchdog.dut.write("Remote Digital Commands", 0)
    sleep(1)

    print("Checking assist level...")
    if watchdog.dut.read("assist level") == 0.75:
        print("PASSED: Assist level in range")
    else:
        print("FAILED: Assist level not in range")
        end_of_test()
        exit()

    input("Press down throttle and press Enter")
    if watchdog.dut.get_rpm() > 0:
        print("PASSED: motor is spinning")
    else:
        print("FAILED: motor is not spinning")
        end_of_test()
        exit()

    vehicle_speed = watchdog.dut.read("vehicle speed")
    high_speed = watchdog.dut.read("vehicle speed (high speed vehicle)")
    if 0.49 * high_speed <= vehicle_speed <= 0.51 * high_speed:
        print("PASSED: vehicle speed (hi & low) are in range")
    else:
        print("FAILED: vehicle speed not in range")
        end_of_test()
        exit()

    input("\nRelease throttle and press Enter")

    # Test 4
    print("Test 4")
    print("Toggle remote regen 1 on")
    watchdog.dut.write("Remote Digital Commands", 1 << 7)

    print("Checking assist level...")
    if watchdog.dut.read("assist level") == 0.75:
        print("PASSED: Assist level remains at 0.75")
    else:
        print("FAILED: Assist level changed")
        end_of_test()
        exit()

    print("Toggle remote regen 1 off")
    watchdog.dut.write("Remote Digital Commands", 0)
    sleep(1)

    print("Checking assist level...")
    if watchdog.dut.read("assist level") == 1:
        print("PASSED: Assist level in range")
    else:
        print("FAILED: Assist level not in range")
        end_of_test()
        exit()

    input("Press down throttle and press Enter")
    if watchdog.dut.get_rpm() > 0:
        print("PASSED: motor is spinning")
    else:
        print("FAILED: motor is not spinning")
        end_of_test()
        exit()

    vehicle_speed = watchdog.dut.read("vehicle speed")
    high_speed = watchdog.dut.read("vehicle speed (high speed vehicle)")
    if 0.49 * high_speed <= vehicle_speed <= 0.51 * high_speed:
        print("PASSED: vehicle speed (hi & low) are in range")
    else:
        print("FAILED: vehicle speed not in range")
        end_of_test()
        exit()

    input("\nRelease throttle and press Enter")

    end_of_test()
    print("PASSED: Momentary Assist Mode & High-speed Vehicle Test Finished")