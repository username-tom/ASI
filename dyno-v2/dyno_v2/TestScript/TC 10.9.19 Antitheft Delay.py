# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.19 Antitheft Delay
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

# def wait_for(time):
#     wait_start = datetime.now()
#     waiting = True
#     while waiting:
#         if (datetime.now() - wait_start).total_seconds() < time:
#             sleep(1)
#         else:
#             waiting = False


if __name__ == "__main__":
    parameters = {"Wheel Lock/Antitheft disable source": 3,  # remote
                  "Antitheft enable time": 5000,  # ms
                  "Control command source": 1,  # Throttle
                  "Throttle sensor source": 5,  # remote
                  "Features": 1 << 2}  # Antitheft
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()

    # Disables antitheft
    print("Disabling antitheft")
    remote_digital_commands = int(watchdog.dut.read("Remote Digital Commands"))
    if (remote_digital_commands & (1 << 14)) >> 14 == 0:
        watchdog.dut.write("Remote Digital Commands", remote_digital_commands + 1 << 14)

    watchdog.dut.save_to_flash()


    def end_of_test():
        # End of test
        watchdog.restore_parameters()
        watchdog.dut.save_to_flash()
        print("Power cycle to reset parameters")

    input("Power cycle and press Enter to continue...")
    print("Initialization successful!")

    # Enables antitheft
    print("Enabling antitheft")
    watchdog.check_bit_vector("Remote Digital Commands", 14, 0)
    # remote_digital_commands = int(watchdog.dut.read("Remote Digital Commands"))
    # if (remote_digital_commands & (1 << 14)) >> 14 == 1:
    #     watchdog.dut.write("Remote Digital Commands", remote_digital_commands - 1 << 14)

    # Check Antitheft status
    start_time = datetime.now()
    while (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(0.5)
        else:
            print("FAILED: TIMEOUT on enabling antitheft")
            end_of_test()
            exit()

    if (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 1:
        print(f"PASSED: Antitheft enabled after {(datetime.now() - start_time).total_seconds():.2f} seconds\n")
    else:
        print("FAILED: Antitheft not engaged")
        end_of_test()
        exit()

    # Test 1
    input("Power cycle and press Enter to continue...")

    # Enables antitheft
    print("Enabling antitheft")
    remote_digital_commands = int(watchdog.dut.read("Remote Digital Commands"))
    if (remote_digital_commands & (1 << 14)) >> 14 == 1:
        watchdog.dut.write("Remote Digital Commands", remote_digital_commands - 1 << 14)

    # Run motor to delay antitheft
    while (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 0:
        start_time = datetime.now()
        print("Run motor with throttle")
        while watchdog.dut.get_rpm() == 0:
            if (datetime.now() - start_time).total_seconds() < 5:
                sleep(0.5)
            else:
                print("FAILED: TIMEOUT on running motor")
                input("Power cycle and restart...")

        while watchdog.dut.get_rpm() > 50:
            if (datetime.now() - start_time).total_seconds() < 5:
                sleep(0.5)
            else:
                print("PASSED: Motor operating for over 5 seconds\nRelease the throttle")
                break

    # check antitheft
    sleep(1)
    if (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 1:
        print(f"PASSED: Antitheft enabled after {(datetime.now() - start_time).total_seconds():.2f} seconds\n")
    else:
        print("FAILED: Antitheft not engaged")
        end_of_test()
        exit()

    print("Test 1 PASSED!\n")

    # Test 2
    print("Test 2\nRun and stop motor within 5 seconds of powering on")
    input("Power cycle and press Enter to continue...")

    # Run motor without delaying antitheft
    start_time = datetime.now()
    print("Run motor with throttle")
    while watchdog.dut.get_rpm() == 0:
        if (datetime.now() - start_time).total_seconds() < 5:
            sleep(0.5)
        else:
            print("FAILED: TIMEOUT on running motor")
            input("Power cycle and restart...")

    print("Motor operating\nRelease the throttle")

    # Check Antitheft status
    start_time = datetime.now()
    while (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 0:
        if (datetime.now() - start_time).total_seconds() < 30:
            sleep(0.5)
        else:
            print("FAILED: TIMEOUT on enabling antitheft")
            end_of_test()
            exit()

    if (int(watchdog.dut.read("controller flags")) & (1 << 14)) >> 14 == 1:
        print(f"PASSED: Antitheft enabled after {(datetime.now() - start_time).total_seconds():.2f} seconds\n")
    else:
        print("FAILED: Antitheft not engaged")
        end_of_test()
        exit()


    end_of_test()
    print("PASSED: Bi-directional Throttle Test Finished")