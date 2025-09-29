# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog
from time import sleep


# COM & Motor parameters for TC 10.5.4.1 (6.024+)
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1

if __name__ == "__main__":
    parameters = {"Throttle sensor source": 0,
                  "Control command source": 1,
                  "Cutoff brake sensor source": 0,
                  "Regen brake source": 1,
                  "Assist mode source": 0}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Initialization successful!")

    input("Hold throttle to maximum and observe motor behavior\nPress Enter when finished")

    parameters = {"Comm Loss Limp Mode Speed": 0.2,
                  "Comm Loss Limp Mode Power": 0.2,
                  "Comm loss Limp Mode Interval": 5,
                  "Features3": 1 << 14,}
    watchdog.update_params(**parameters)
    print("Comm Loss Limp Mode parameters updated\n"
          "Feature3 bit 14 enabled")

    watchdog.update_timeout(5000, 5000)
    print("Updated command timeout threshold")

    input("Hold throttle to maximum and observe motor behavior\nPress Enter when finished")

    print("Test over\n"
          "Power cycle to reset DUT")

