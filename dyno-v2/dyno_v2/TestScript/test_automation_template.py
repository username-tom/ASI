"""Template with sample functions for test automation.
Only supports one device running over terminal. """
# IMPORTS
from dyno_v2.Module.Watchdog import *
from time import sleep
from datetime import datetime
from threading import Thread

# COM & Motor parameters for TC 10.9.14 Bi-directional Throttle
PORT = "COM5"
BAUD_RATE = 115200
MB_ADDRESS = 1


if __name__ == "__main__":

    """
    Initiate Watchdog
    """
    # Initiate watchdog and updates parameters
    parameters = {"Control command source": 1,  # Throttle
                  "Speed regulator mode": 0,  # Speed
                  "Throttle sensor source": 0,  # Throttle Voltage
                  "Throttle off voltage": 1,  # V
                  "Throttle full voltage": 4,  # V
                  "Bidirectional Throttle Deadband": 0.2,  # V
                  "Bidirectional Throttle Midpoint": 2.5,  # V
                  "Reverse_Enable_Source": 4,  # bidirectional throttle
                  "Features4": 2048}  # 0000 1000 0000 0000
    # Init Watchdog, loading all parameters from ASIObjectDictionary
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)


    # Read and store original parameter value
    feature = int(watchdog.dut.read("Features"))  # for int, bit, num, hex parameters (bit operation requires int)
    throttle = watchdog.dut.read("throttle setpoint")  # for float, double parameters (don't need bit operations)


    """
    End of Test function
    """
    # Reset changed parameters
    def end_of_test():
        watchdog.restore_parameters()
        # if parameters need save to flash to restore
        watchdog.dut.save_to_flash()
        print("Power cycle to complete restoring parameters")


    # Test failed function
    def test_failed(msg=""):
        print(msg)
        end_of_test()
        exit()


    # Update bit values based on original value
    bit = 1
    if (feature & (1 << bit)) >> bit == 0:  # check if the feature bit is already enabled
        watchdog.dut.write("Features", feature + (1 << bit))  # write adjusted value to feature
    sleep(1)


    """
    Other Functions
    """
    # Save to flash
    watchdog.dut.save_to_flash()


    # Wait for user input (pauses test script)
    input("INSERT MESSAGE HERE")
    # Example 1: any input to continue
    input("Power cycle and press Enter to continue...")
    # Example 2: expecting specific inputs
    ans = input("Proceed with test? (Y/N)")
    if ans.lower() in ['y', '', 'yes']:  # accepting Y, y, Yes, YES, yes, yEs, ... , or empty input
        print("Proceed!")
    else:
        print("Abort!")
        end_of_test()
        exit("Test Aborted by User!")


    # Information for user
    print("INSERT MESSAGE HERE")


    # Write parameter
    watchdog.dut.write("Remote Throttle Voltage", 2.5)


    # Read and display parameter
    throttle = watchdog.dut.read("throttle setpoint")
    print(f'Throttle Setpoint: {throttle}')


    # Check parameter value for pass/fail condition
    if throttle == 0:
        print("PASSED: Throttle setpoint is 0")
    else:
        print("FAILED: Throttle setpoint is not 0")
        end_of_test()
        exit("FAILED: Incomplete Test")  # Ends test on failure


    # Wait for motor RPM to reach desired target with timeout
    target = 500  # RPM
    start_time = datetime.now()
    while watchdog.dut.get_rpm() <= 0.8 * target:
        if (datetime.now() - start_time).total_seconds() < 30:  # 30 seconds time out
            sleep(1)
        else:
            test_failed("FAILED: TIMEOUT before RPM in range!")
    print("PASSED: RPM in range")


    # Check faults
    print(watchdog.dut.check_faults())


    # Clear faults
    watchdog.dut.clear_faults()


    # Check if controller is in foldback
    print(watchdog.dut.in_foldback())


    # Change access level
    watchdog.dut.set_access_level(1)


    # Bridge check
    (passed,
     post_static_open_circuit_voltages,
     post_dynamic_high_voltages,
     post_dynamic_low_voltages) = watchdog.dut.bridge_check()
    print(f"Bridge Test Result: {passed}\n"
          f"POST Static Voltages: {post_static_open_circuit_voltages}\n"
          f"POST Dynamic High Voltages: {post_dynamic_high_voltages}\n"
          f"POST Dynamic Low Voltages: {post_dynamic_low_voltages}")


    # Run motor with watchdog
    watchdog.update_timeout(500, 450)  # update Command timeout threshold & Average Command timeout threshold
    watchdog.run_for(0.2, 25)  # runs for ~5 (0.2 * 25) seconds


    # Run motor with watchdog until faults
    watchdog.update_timeout(500, 450)
    watchdog.run_till_fault(0.2, 25)  # runs for ~5 (0.2 * 25) seconds unless controller faults


    # Turns off communication timeouts
    watchdog.dut.turn_off_communication_timeout()


    # Wait for ## seconds
    print("Waiting for 3 seconds")
    wait_thread = Thread(target=wait_for, args=[3])
    wait_thread.start()
    wait_thread.join()


    """
    End of Test
    """
    # Default end of test
    end_of_test()
    print("PASSED: XXXXXXX Test Finished")
