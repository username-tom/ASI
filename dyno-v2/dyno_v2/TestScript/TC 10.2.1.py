# IMPORTS
from dyno_v2.Module.Watchdog import Watchdog


# COM & Motor parameters for TC 10.1.2
PORT = "COM25"
BAUD_RATE = 115200
MB_ADDRESS = 1
THROTTLE_FULL_VOLTAGE_ORIGINAL = 4
THROTTLE_OFF_VOLTAGE_ORIGINAL = 1
THROTTLE_FULL_VOLTAGE_ADJUSTED = 3
THROTTLE_OFF_VOLTAGE_ADJUSTED = 2

if __name__ == "__main__":
    parameters = {"Speed regulator mode": 2,
                  "Control command source": 4,
                  "Throttle full voltage": THROTTLE_FULL_VOLTAGE_ORIGINAL,
                  "Throttle off voltage": THROTTLE_OFF_VOLTAGE_ORIGINAL}
    # Init Watchdog
    watchdog = Watchdog(PORT, BAUD_RATE, MB_ADDRESS, **parameters)
    watchdog.dut.turn_off_communication_timeout()
    watchdog.dut.clear_faults()
    print("Initialization successful!")

    # tests 1
    print("Motor should run with throttle input")

    input("Press Enter to start next test...")

    # tests 2
    print("Adjusting Throttle full voltage to lower value...")
    watchdog.dut.write("Throttle full voltage", THROTTLE_FULL_VOLTAGE_ADJUSTED)
    print("Press the throttle and Faults bit 11 should turn on...")
    while "faults-bit 11: Throttle voltage outside range (flash code 2,4)" not in watchdog.dut.check_faults():
        continue
    print("Throttle out of range warning detected!")
    print("tests 2 PASS!")
    watchdog.dut.write("Fault clear", 1)
    watchdog.dut.write("Throttle full voltage", THROTTLE_FULL_VOLTAGE_ORIGINAL)
    input("Let go of throttle and press Enter...")

    # tests 3
    print("Adjusting Throttle off voltage to higher value...")
    watchdog.dut.write("Throttle off voltage", THROTTLE_OFF_VOLTAGE_ADJUSTED)
    print("Throttle at off position should trigger out of range warning right away...")
    while "faults-bit 11: Throttle voltage outside range (flash code 2,4)" not in watchdog.dut.check_faults():
        continue
    print("Throttle out of range warning detected!")
    print("tests 3 PASS!")
    watchdog.dut.write("Throttle off voltage", THROTTLE_OFF_VOLTAGE_ORIGINAL)

