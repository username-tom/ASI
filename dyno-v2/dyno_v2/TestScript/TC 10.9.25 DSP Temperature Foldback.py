# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.14 Bi-directional Throttle
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
    parameters = {"Features5": 1}  # 0000 0000 0000 0001
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)


    def end_of_test():
        # End of test
        watchdog.restore_parameters()
        watchdog.dut.set_access_level(2)
        watchdog.dut.write("Controller foldback starting temperature", 80)
        watchdog.dut.write("Controller foldback ending temperature", 100)
        sleep(1)
        watchdog.dut.set_access_level(0)


    print("Initialization successful!")

    # Test 1
    print("Test 1: Checking starting conditions")
    if watchdog.dut.read("Controller foldback starting temperature") == 80 and \
            watchdog.dut.read("Controller foldback ending temperature") == 100:
        watchdog.dut.set_access_level(2)
        watchdog.dut.write("Controller foldback starting temperature", 80)
        watchdog.dut.write("Controller foldback ending temperature", 100)
        sleep(1)

    original_controller_temperature = watchdog.dut.read("controller temperature")
    original_dsp_temperature = watchdog.dut.read("dsp core temperature")
    print("Checking starting temperatures...")
    if original_dsp_temperature < original_controller_temperature:
        end_of_test()
        exit("Test Aborted: DSP temperature lower than controller temperature")
    print("DSP & controller temperature in normal range")

    print("Checking warnings and foldback...")
    if watchdog.dut.read("warnings") > 0:
        end_of_test()
        exit("Test Aborted: Warning detected, please check!")
    if watchdog.dut.read("controller temperature foldback gain") != 1:
        end_of_test()
        exit("Test Aborted: Controller already in foldback, please check!")

    print("Test 1 PASSED!")

    # Test 2
    print("Test 2: Checking DSP temperature foldback")
    watchdog.dut.set_access_level(2)
    new_starting_temperature = int((original_controller_temperature + original_dsp_temperature) / 2)
    print(f"Changing 'Controller foldback starting temperature' to {new_starting_temperature}")
    watchdog.dut.write("Controller foldback starting temperature",
                       new_starting_temperature)

    sleep(1)
    print("Checking 'controller temperature foldback gain'...")
    new_foldback = watchdog.dut.read("controller temperature foldback gain")
    print(f"controller temperature foldback gain = {new_foldback}")
    new_foldback_ref = 1 - ((watchdog.dut.read("dsp core temperature") - new_starting_temperature) /
                            (100 - new_starting_temperature))
    if 0.99 < new_foldback / new_foldback_ref < 1.01:
        print("Test 2 PASSED!")
    else:
        end_of_test()
        exit("Test 2 FAILED: controller temperature foldback gain out of range")

    end_of_test()
    print("PASSED: DSP Temperature Foldback Test Finished")