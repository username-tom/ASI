# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep


# COM & Motor parameters for TC 10.1.2
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1
THROTTLE_FULL_VOLTAGE_ORIGINAL = 4
THROTTLE_OFF_VOLTAGE_ORIGINAL = 1
THROTTLE_FULL_VOLTAGE_ADJUSTED = 5
THROTTLE_OFF_VOLTAGE_ADJUSTED = 0

if __name__ == "__main__":
    tests = [False, False, False]
    parameters = {"Throttle sensor source": 5,
                  "Control command source": 4,
                  "Throttle full voltage": THROTTLE_FULL_VOLTAGE_ADJUSTED,
                  "Throttle off voltage": THROTTLE_OFF_VOLTAGE_ADJUSTED,
                  "Throttle deadband threshold": 0}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Initialization successful!")

    # tests 1
    print("Verify motor is stopped")
    input("Press Enter to start test 1...")
    watchdog.dut.write("Remote Throttle Voltage", .25 * THROTTLE_FULL_VOLTAGE_ADJUSTED)
    sleep(5)
    setpoint = watchdog.dut.read("throttle setpoint")
    print(f"25% Throttle Setpoint: {setpoint}")
    passed = input("Setpoint within reasonable range? [Y/N] ")
    if passed.lower() == "y":
        tests[0] = True

    # tests 2
    input("Press Enter to start test 2...")
    watchdog.dut.write("Remote Throttle Voltage", .5 * THROTTLE_FULL_VOLTAGE_ADJUSTED)
    sleep(5)
    setpoint = watchdog.dut.read("throttle setpoint")
    print(f"50% Throttle Setpoint: {setpoint}")
    passed = input("Setpoint within reasonable range? [Y/N] ")
    if passed.lower() == "y":
        tests[1] = True

    # tests 3
    input("Press Enter to start test 3...")
    watchdog.dut.write("Remote Throttle Voltage", THROTTLE_FULL_VOLTAGE_ADJUSTED)
    sleep(5)
    setpoint = watchdog.dut.read("throttle setpoint")
    print(f"100% Throttle Setpoint: {setpoint}")
    passed = input("Setpoint within reasonable range? [Y/N] ")
    if passed.lower() == "y":
        tests[2] = True

    for i, test in enumerate(tests, 1):
        print(f"TC 10.2.2 Test {i} Passed: {test}")

    parameters = {"Fault clear": 1,
                  "Remote Throttle Voltage": 0,
                  "Throttle sensor source": 0,
                  "Control command source": 4,
                  "Throttle full voltage": THROTTLE_FULL_VOLTAGE_ORIGINAL,
                  "Throttle off voltage": THROTTLE_OFF_VOLTAGE_ORIGINAL,
                  "Throttle deadband threshold": 0.2}
    watchdog.update_params(**parameters)
