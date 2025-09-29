# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep


# COM & Motor parameters for TC 10.9.15
PORT = "COM5"
BAUD_RATE = 115200
MB_ADDRESS = 1
THROTTLE_FULL_VOLTAGE_ORIGINAL = 4
THROTTLE_OFF_VOLTAGE_ORIGINAL = 1
THROTTLE_FULL_VOLTAGE_ADJUSTED = 5
THROTTLE_OFF_VOLTAGE_ADJUSTED = 0

if __name__ == "__main__":
    tests = [False, False, False]
    parameters = {"Fault clear": 1,
                  "Throttle sensor source": 5,
                  "Control command source": 4,
                  "Throttle full voltage": THROTTLE_FULL_VOLTAGE_ADJUSTED,
                  "Throttle off voltage": THROTTLE_OFF_VOLTAGE_ADJUSTED,
                  "Throttle deadband threshold": 0}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    print("Initialization successful!")

    # placeholder